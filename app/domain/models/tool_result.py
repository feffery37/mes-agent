#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : tool_result.py
@Desc    : 工具结果领域模型（与课程 domain/models/tool_result.py 对应）。
           所有工具调用统一返回 ToolResult，便于 Agent 把结果回填给 LLM。
"""
from typing import Optional, TypeVar, Generic

from pydantic import BaseModel

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    """工具结果 Domain 模型。"""

    success: bool = True
    message: Optional[str] = ""
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "") -> "ToolResult[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str = "工具调用失败") -> "ToolResult[T]":
        return cls(success=False, message=message, data=None)
