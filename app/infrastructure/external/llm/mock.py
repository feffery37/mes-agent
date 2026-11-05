#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : mock.py
@Desc    : 本地 Mock LLM —— 无需 API Key 即可跑通 ReAct 循环，用于演示/单测。
           逻辑：根据最新用户问题做关键词意图识别 -> 选择并调用一个工具；
           当上下文中已出现工具结果时，输出一段汇总文本作为最终回答。
           接入真实模型时，把 service_dependencies 中的 provider 切回 openai 即可。
"""
import json
import logging
import uuid
from typing import List, Dict, Any, Optional

from app.domain.external.llm import LLM
from core.config import LLMConfig

logger = logging.getLogger(__name__)


# 意图关键词 -> (工具名, 默认参数构造器)
_INTENT_RULES = [
    # 可视化意图优先：命中即出图
    ("可视化", "plot_param_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("图表", "plot_param_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("画图", "plot_param_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("画个", "plot_param_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("曲线", "plot_param_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("报警", "query_alarm_log", lambda q: {"eid": 1, "days": 1}),
    ("趋势", "analyze_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("上升", "analyze_trend", lambda q: {"eid": 1, "param": "TEMP_NOZZLE", "window": "7d"}),
    ("预测", "predict_failure", lambda q: {"eid": 1, "horizon": "72h"}),
    ("会不会出问题", "predict_failure", lambda q: {"eid": 1, "horizon": "72h"}),
    ("怎么处理", "search_knowledge", lambda q: {"keyword": "温度上升"}),
    ("建议", "search_knowledge", lambda q: {"keyword": "温度上升"}),
    ("SOP", "search_knowledge", lambda q: {"keyword": "温度上升"}),
    ("工单", "create_workorder", lambda q: {"eid": 1, "title": "喷嘴温度异常处理"}),
    ("型号", "query_equipment", lambda q: {"eid": 1}),
    ("设备", "query_equipment", lambda q: {"eid": 1}),
    ("控制限", "query_equipment", lambda q: {"eid": 1}),
]


class MockLLM(LLM):
    """本地演示用 LLM 实现（实现 LLM 协议）。"""

    def __init__(self, llm_config: LLMConfig, **kwargs) -> None:
        self._model_name = llm_config.model_name or "mock-llm"
        self._temperature = llm_config.temperature
        self._max_tokens = llm_config.max_tokens

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @staticmethod
    def _last_user_text(messages: List[Dict[str, Any]]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                return str(m.get("content", ""))
        return ""

    @staticmethod
    def _has_tool_result(messages: List[Dict[str, Any]]) -> bool:
        return any(m.get("role") == "tool" for m in messages)

    def _decide_tool(self, query: str):
        for keyword, tool_name, arg_fn in _INTENT_RULES:
            if keyword in query:
                return tool_name, arg_fn(query)
        # 默认：查设备现状
        return "query_equipment", {"eid": 1}

    def _summarize(self, messages: List[Dict[str, Any]]) -> str:
        """根据工具结果生成最终中文回答（演示用，遵循「分析思路 -> 结论」格式约定）。"""
        parts = []
        for m in messages:
            if m.get("role") == "tool":
                fn = m.get("function_name", "")
                try:
                    data = json.loads(m.get("content", "{}"))
                except Exception:
                    data = m.get("content", "")
                parts.append(f"【{fn}】{data}")
        if not parts:
            return "（未获取到工具数据）"
        return (
            "## 分析思路\n"
            f"- 本轮共调用 {len(parts)} 项工具获取定量数据，按「查现状 → 看趋势 → 找原因 → 问对策」路径整理。\n"
            "- 将返回值中的关键指标与控制限对比，判断当前设备状态是否需要干预。\n\n"
            "## 结论\n"
            + "\n".join(parts)
            + "\n\n（以上由 iMES 设备洞察 Agent 演示模式生成，接入真实 LLM 后将给出自然语言推理。）"
        )

    async def invoke(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            response_format: Optional[Dict[str, Any]] = None,
            tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 已经执行过工具 -> 生成最终回答
        if self._has_tool_result(messages):
            return {
                "role": "assistant",
                "content": self._summarize(messages),
                "reasoning_content": "已获得工具返回的定量结论。现在把关键数据与控制限对比，"
                                     "按「分析思路 -> 结论」的格式组织最终回答，并落到可执行建议。",
            }

        # 否则根据意图选择一个工具并构造 tool_calls
        query = self._last_user_text(messages)
        tool_name, args = self._decide_tool(query)
        available = {t["function"]["name"]: t for t in (tools or [])}
        if tool_name not in available:
            # 工具集中没有匹配的，直接给文本兜底
            return {"role": "assistant", "content": f"（演示模式：未找到适配工具，原始问题：{query}）"}

        call_id = "call_" + uuid.uuid4().hex[:12]
        reasoning = (
            f"用户的问题是「{query}」。先做意图判断：该问题需要定量数据支撑，"
            f"因此第一步调用 {tool_name}（参数：{args}）获取设备现状；"
            "拿到结果后再决定是否需要进一步做趋势分析或知识库检索。"
        )
        return {
            "role": "assistant",
            "content": None,
            "reasoning_content": reasoning,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args, ensure_ascii=False),
                    },
                }
            ],
        }
