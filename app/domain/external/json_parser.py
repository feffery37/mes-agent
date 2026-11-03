#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : json_parser.py
@Desc    : JSON 解析协议（与课程 domain/external/json_parser.py 对应）。
           LLM 在 tool_calls.arguments 中常返回带噪声的 JSON 字符串，
           统一通过该协议解析，避免大模型幻觉/格式问题导致解析失败。
"""
from typing import Protocol, Any


class JSONParser(Protocol):
    """JSON 解析器协议。"""

    async def invoke(self, content: str) -> Any:
        """传递待解析的内容，返回 Python 对象。"""
        ...
