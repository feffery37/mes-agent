#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : llm.py
@Desc    : LLM 交互协议（与课程 domain/external/llm.py 对应）。
           定义 Agent 应用与 LLM 之间的统一接口，便于在不改动上层逻辑的情况下
           替换不同的模型实现（DeepSeek / OpenAI / 本地 Mock 等）。
"""
from typing import Protocol, List, Dict, Any, Optional


class LLM(Protocol):
    """Agent 应用与 LLM 交互的接口协议。"""

    async def invoke(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            response_format: Optional[Dict[str, Any]] = None,
            tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """传递消息列表、工具列表、响应格式、工具选择策略调用 LLM 接口。"""
        ...

    @property
    def model_name(self) -> str:
        """只读属性，返回 LLM 的模型名。"""
        ...

    @property
    def temperature(self) -> float:
        """只读属性，返回 LLM 的温度。"""
        ...

    @property
    def max_tokens(self) -> int:
        """只读属性，返回 LLM 的最大生成 token 数。"""
        ...
