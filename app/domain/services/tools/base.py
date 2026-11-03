#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : base.py
@Desc    : 工具基类与工具装饰器（与课程 domain/services/tools/base.py 对应）。
           设计思路：
           1) 所有工具继承 BaseTool，拥有统一的 invoke 方法；
           2) @tool 装饰器把函数声明为工具，并附上 name/description/schema；
           3) get_tools() 缓存并返回供 LLM 绑定的 schema；
           4) 调用前用 inspect 过滤 LLM 幻觉产生的多余参数。
"""
import inspect
from typing import Dict, Any, List, Callable

from app.domain.models.tool_result import ToolResult


def tool(
        name: str,
        description: str,
        parameters: Dict[str, Dict[str, Any]],
        required: List[str],
) -> Callable:
    """OpenAI 工具装饰器：把方法声明为可被 LLM 调用的工具。"""

    def decorator(func):
        tool_schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        }
        func._tool_name = name
        func._tool_description = description
        func._tool_schema = tool_schema
        return func

    return decorator


class BaseTool:
    """基础工具类：管理一个工具集。"""

    name: str = ""

    def __init__(self) -> None:
        self._tools_cache: List[Dict[str, Any]] | None = None

    @classmethod
    def _filter_parameters(cls, method: Callable, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """过滤 kwargs，仅保留 method 真实声明的参数（防止 LLM 幻觉）。"""
        filtered: Dict[str, Any] = {}
        sign = inspect.signature(method)
        for key, value in kwargs.items():
            if key in sign.parameters:
                filtered[key] = value
        return filtered

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取所有已注册工具的 schema（带缓存）。"""
        if self._tools_cache is not None:
            return self._tools_cache
        tools = []
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_schema"):
                tools.append(getattr(method, "_tool_schema"))
        self._tools_cache = tools
        return tools

    def has_tool(self, tool_name: str) -> bool:
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_name") and getattr(method, "_tool_name") == tool_name:
                return True
        return False

    async def invoke(self, tool_name: str, **kwargs) -> ToolResult:
        """根据工具名调用对应方法并返回 ToolResult。"""
        for _, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, "_tool_name") and getattr(method, "_tool_name") == tool_name:
                filtered_kwargs = self._filter_parameters(method, kwargs)
                return await method(**filtered_kwargs)
        return ToolResult.fail(f"工具[{tool_name}]未找到")
