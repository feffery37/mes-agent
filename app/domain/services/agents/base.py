#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : base.py
@Desc    : 基础 Agent（与课程 domain/services/agents/base.py 对应）。
           实现 ReAct 循环：调用 LLM -> 解析工具调用 -> 执行工具 -> 回填结果 -> 再次调用 LLM，
           以事件流(AsyncGenerator[BaseEvent])形式输出，支持记忆持久化与重试。
"""
import asyncio
import logging
import uuid
from abc import ABC
from typing import Optional, List, AsyncGenerator, Dict, Any, Callable

from app.domain.external.json_parser import JSONParser
from app.domain.external.llm import LLM
from core.config import AgentConfig
from app.domain.models.event import (
    ToolEvent,
    ToolEventStatus,
    ErrorEvent,
    MessageEvent,
    BaseEvent,
)
from app.domain.models.memory import Memory
from app.domain.models.tool_result import ToolResult
from app.domain.repositories.uow import IUnitOfWork
from app.domain.services.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """基础 Agent 智能体。"""

    name: str = ""
    _system_prompt: str = ""
    _format: Optional[str] = None
    _retry_interval: float = 1.0
    _tool_choice: Optional[str] = None

    def __init__(
            self,
            uow_factory: Callable[[], IUnitOfWork],
            session_id: str,
            agent_config: AgentConfig,
            llm: LLM,
            json_parser: JSONParser,
            tools: List[BaseTool],
    ) -> None:
        self._uow_factory = uow_factory
        self._uow = uow_factory()
        self._session_id = session_id
        self._agent_config = agent_config
        self._llm = llm
        self._memory: Optional[Memory] = None
        self._json_parser = json_parser
        self._tools = tools

    async def _ensure_memory(self) -> None:
        if self._memory is None:
            async with self._uow:
                self._memory = await self._uow.session.get_memory(self._session_id, self.name)

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        available_tools = []
        for tool in self._tools:
            available_tools.extend(tool.get_tools())
        return available_tools

    def _get_tool(self, tool_name: str) -> BaseTool:
        for tool in self._tools:
            if tool.has_tool(tool_name):
                return tool
        raise ValueError(f"未知工具: {tool_name}")

    async def _invoke_llm(
            self, messages: List[Dict[str, Any]], format: Optional[str] = None
    ) -> Dict[str, Any]:
        """调用 LLM 并处理记忆（带重试）。"""
        await self._add_to_memory(messages)
        response_format = {"type": format} if format else None

        error = "调用语言模型发生错误"
        for _ in range(self._agent_config.max_retries):
            try:
                message = await self._llm.invoke(
                    messages=self._memory.get_messages(),
                    tools=self._get_available_tools(),
                    response_format=response_format,
                    tool_choice=self._tool_choice,
                )

                if message.get("role") == "assistant":
                    if not message.get("content") and not message.get("tool_calls"):
                        logger.warning("LLM 回复了空内容，执行重试")
                        await self._add_to_memory([
                            {"role": "assistant", "content": ""},
                            {"role": "user", "content": "AI无响应内容，请继续。"},
                        ])
                        await asyncio.sleep(self._retry_interval)
                        continue
                    filtered = {"role": "assistant", "content": message.get("content")}
                    if message.get("reasoning_content"):
                        filtered["reasoning_content"] = message["reasoning_content"]
                    if message.get("tool_calls"):
                        filtered["tool_calls"] = message["tool_calls"][:1]
                else:
                    logger.warning(f"LLM 响应角色无法确认: {message.get('role')}")
                    filtered = message

                await self._add_to_memory([filtered])
                return filtered
            except Exception as e:
                logger.error(f"调用语言模型发生错误: {str(e)}")
                error = str(e)
                await asyncio.sleep(self._retry_interval)
                continue

        raise RuntimeError(
            f"调用语言模型失败, 已达到最大重试次数({self._agent_config.max_retries}): {error}"
        )

    async def _invoke_tool(
            self, tool: BaseTool, tool_name: str, arguments: Dict[str, Any]
    ) -> ToolResult:
        err = ""
        for _ in range(self._agent_config.max_retries):
            try:
                return await tool.invoke(tool_name, **arguments)
            except Exception as e:
                err = str(e)
                logger.exception(f"调用工具[{tool_name}]出错: {str(e)}")
                await asyncio.sleep(self._retry_interval)
                continue
        return ToolResult(success=False, message=err)

    async def _add_to_memory(self, messages: List[Dict[str, Any]]) -> None:
        await self._ensure_memory()
        if self._memory.empty:
            self._memory.add_message({"role": "system", "content": self._system_prompt})
        self._memory.add_messages(messages)
        async with self._uow:
            await self._uow.session.save_memory(self._session_id, self.name, self._memory)

    async def invoke(
            self, query: str, format: Optional[str] = None
    ) -> AsyncGenerator[BaseEvent, None]:
        """ReAct 主循环：以事件流形式驱动工具调用与最终回答。"""
        format = format if format else self._format
        message = await self._invoke_llm([{"role": "user", "content": query}], format)

        for _ in range(self._agent_config.max_iterations):
            if not message or not message.get("tool_calls"):
                break

            tool_messages = []
            for tool_call in message["tool_calls"]:
                if not tool_call.get("function"):
                    continue

                tool_call_id = tool_call["id"] or str(uuid.uuid4())
                function_name = tool_call["function"]["name"]
                function_args = await self._json_parser.invoke(tool_call["function"]["arguments"])

                tool = self._get_tool(function_name)

                yield ToolEvent(
                    tool_call_id=tool_call_id,
                    tool_name=tool.name,
                    function_name=function_name,
                    function_args=function_args,
                    status=ToolEventStatus.CALLING,
                )

                result = await self._invoke_tool(tool, function_name, function_args)

                yield ToolEvent(
                    tool_call_id=tool_call_id,
                    tool_name=tool.name,
                    function_name=function_name,
                    function_args=function_args,
                    function_result=result,
                    status=ToolEventStatus.CALLED,
                )

                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "function_name": function_name,
                    "content": result.model_dump_json(),
                })

            message = await self._invoke_llm(tool_messages)
        else:
            yield ErrorEvent(error=f"Agent迭代超过最大迭代次数: {self._agent_config.max_iterations}")

        if message and message.get("content") is not None:
            yield MessageEvent(message=message["content"])
        else:
            yield ErrorEvent(error="Agent未能生成有效回复内容")
