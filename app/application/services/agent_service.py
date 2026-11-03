#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : agent_service.py
@Desc    : Agent 后台任务运行器 + 会话管理器（对应课程 application + domain/services/agent_task_runner）。
           1) AgentTaskRunner：在后台 asyncio 任务中运行 Agent 的 ReAct 流，并以事件流输出；
           2) AgentService：管理多会话、输入输出队列、生命周期启停（后台运行架构）。
"""
import asyncio
import logging
import uuid
from typing import AsyncGenerator, Callable, Dict, Optional

from app.application.errors.exceptions import AgentNotFoundError
from app.domain.external.json_parser import JSONParser
from app.domain.external.llm import LLM
from app.domain.models.event import (
    BaseEvent,
    DoneEvent,
    ErrorEvent,
    MessageEvent,
    ToolEvent,
    ToolEventStatus,
)
from app.domain.models.message import Message
from app.domain.repositories.uow import IUnitOfWork, InMemoryUnitOfWork
from app.domain.services.agents.react import EquipmentInsightAgent
from app.domain.services.tools.base import BaseTool
from app.domain.services.tools.equipment import EquipmentTool
from app.domain.services.tools.knowledge import KnowledgeTool
from app.domain.services.tools.prediction import PredictionTool
from app.domain.services.tools.trend import TrendTool
from app.domain.services.tools.workorder import WorkOrderTool
from app.infrastructure.external.json_parser.default import DefaultJSONParser
from app.infrastructure.external.llm.mock import MockLLM
from app.infrastructure.external.llm.openai_llm import OpenAILLM
from app.infrastructure.repositories.memory import InMemoryMemoryRepository
from core.config import AgentConfig, AppConfig, LLMConfig, get_app_config

logger = logging.getLogger(__name__)


class AgentTaskRunner:
    """Agent 任务运行器：在后台任务中运行 Agent 流并产出事件。"""

    def __init__(
            self,
            uow_factory: Callable[[], IUnitOfWork],
            llm: LLM,
            agent_config: AgentConfig,
            json_parser: JSONParser,
            tools: list[BaseTool],
            session_id: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._llm = llm
        self._agent_config = agent_config
        self._json_parser = json_parser
        self._tools = tools
        self._session_id = session_id

    async def run(self, message: Message) -> AsyncGenerator[BaseEvent, None]:
        """运行 Agent 的 ReAct 流，逐条产出事件。"""
        if not message.message:
            yield ErrorEvent(error="空消息错误")
            return

        agent = EquipmentInsightAgent(
            uow_factory=self._uow_factory,
            session_id=self._session_id,
            agent_config=self._agent_config,
            llm=self._llm,
            json_parser=self._json_parser,
            tools=self._tools,
        )

        async for event in agent.invoke(message.message):
            # 工具事件：可在此补充前端友好的扩展内容（如曲线 URL），基础框架留空
            if isinstance(event, ToolEvent) and event.status == ToolEventStatus.CALLED:
                logger.info(
                    f"[TaskRunner] 工具 {event.function_name} 返回: "
                    f"{event.function_result.model_dump() if event.function_result else None}"
                )
            yield event


class _SessionState:
    """单个会话的运行状态。"""

    def __init__(self) -> None:
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.task: Optional[asyncio.Task] = None


class AgentService:
    """Agent 会话管理服务（后台运行架构）。"""

    def __init__(self) -> None:
        self._app_config: AppConfig = get_app_config()
        self._repo = InMemoryMemoryRepository()
        self._json_parser = DefaultJSONParser()
        self._tools: list[BaseTool] = [
            EquipmentTool(),
            TrendTool(),
            PredictionTool(),
            KnowledgeTool(),
            WorkOrderTool(),
        ]
        self._llm: Optional[LLM] = None
        self._sessions: Dict[str, _SessionState] = {}

    # ----- LLM 工厂（可动态配置：真实模型 / 本地 Mock）-----
    def _build_llm(self) -> LLM:
        llm_config: LLMConfig = self._app_config.llm
        if llm_config.provider == "mock" or not llm_config.api_key:
            logger.warning("[AgentService] 使用 MockLLM（无 API Key 或 provider=mock）")
            return MockLLM(llm_config)
        return OpenAILLM(llm_config)

    def _get_llm(self) -> LLM:
        if self._llm is None:
            self._llm = self._build_llm()
        return self._llm

    def _uow_factory(self) -> IUnitOfWork:
        return InMemoryUnitOfWork(self._repo)

    # ----- 会话管理 -----
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = _SessionState()
        return session_id

    def get_session(self, session_id: str) -> _SessionState:
        state = self._sessions.get(session_id)
        if not state:
            raise AgentNotFoundError(f"会话不存在: {session_id}")
        return state

    async def submit(self, session_id: str, message: str) -> None:
        """提交一条用户消息，触发（或复用）后台任务运行 Agent。"""
        state = self.get_session(session_id)
        await state.input_queue.put(MessageEvent(message=message, role="user"))

        if state.task is None or state.task.done():
            runner = AgentTaskRunner(
                uow_factory=self._uow_factory,
                llm=self._get_llm(),
                agent_config=self._app_config.agent,
                json_parser=self._json_parser,
                tools=self._tools,
                session_id=session_id,
            )
            state.task = asyncio.create_task(self._drain(state, runner))

    async def _drain(self, state: _SessionState, runner: AgentTaskRunner) -> None:
        """后台任务：消费输入队列，运行 Agent，把事件写入输出队列。"""
        try:
            while not state.input_queue.empty():
                event: MessageEvent = await state.input_queue.get()
                message = Message(message=event.message, role="user")
                async for out in runner.run(message):
                    await state.output_queue.put(out)
            await state.output_queue.put(DoneEvent())
        except asyncio.CancelledError:
            logger.info("[AgentService] 后台任务被取消")
            await state.output_queue.put(DoneEvent())
            raise
        except Exception as e:
            logger.exception(f"[AgentService] 运行出错: {str(e)}")
            await state.output_queue.put(ErrorEvent(error=f"运行出错: {str(e)}"))
            await state.output_queue.put(DoneEvent())

    async def stream(self, session_id: str) -> AsyncGenerator[BaseEvent, None]:
        """从输出队列消费事件，直到 DoneEvent（供 SSE 推送）。"""
        state = self.get_session(session_id)
        while True:
            event = await state.output_queue.get()
            yield event
            if isinstance(event, DoneEvent):
                break

    async def shutdown(self) -> None:
        """关闭所有后台任务。"""
        for session_id, state in self._sessions.items():
            if state.task and not state.task.done():
                state.task.cancel()
                try:
                    await state.task
                except (asyncio.CancelledError, Exception):
                    pass
        logger.info("[AgentService] 所有后台任务已关闭")


_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取全局 AgentService 单例（对应课程 interfaces/service_dependencies.get_agent_service）。"""
    global _service
    if _service is None:
        _service = AgentService()
    return _service
