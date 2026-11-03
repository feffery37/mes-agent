#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : knowledge.py
@Desc    : 知识库 / SOP 检索工具（对应数据域 KB_DOCUMENT）。
           支持关键词 + 机型元数据过滤（方案第5章：向量 + 元数据过滤的思路，基础框架用关键词匹配）。
"""
import logging

from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.data import sample

logger = logging.getLogger(__name__)


class KnowledgeTool(BaseTool):
    """知识库检索工具集。"""
    name = "knowledge"

    @tool(
        name="search_knowledge",
        description="根据症状关键词检索 SOP / 历史案例知识库，返回处理建议与根因统计。"
                    "用于回答“该怎么处理 / 有没有类似案例”等问题。",
        parameters={
            "keyword": {"type": "string", "description": "症状关键词，如 温度上升"},
            "model": {"type": "string", "description": "可选机型过滤，如 ASM-AD830"},
        },
        required=["keyword"],
    )
    async def search_knowledge(self, keyword: str, model: str = "") -> ToolResult:
        kw = keyword.lower()
        results = []
        for doc in sample.KB_DOCUMENT:
            haystack = (doc["title"] + doc["symptom"] + doc["content"]).lower()
            if kw in haystack and (not model or model.lower() in doc.get("model", "").lower()):
                results.append(doc)
        if not results:
            return ToolResult.ok(data={"count": 0, "docs": []}, message="未检索到相关知识")
        return ToolResult.ok(data={"count": len(results), "docs": results}, message="检索完成")
