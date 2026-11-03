#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : workorder.py
@Desc    : 维修工单工具（对应数据域 PR_WORKORDER）。
           基础框架在内存中维护工单；真实环境对接 MES / 工单系统。
"""
import itertools
import logging

from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool

logger = logging.getLogger(__name__)

_counter = itertools.count(1001)
_WORKORDERS: dict = {}


class WorkOrderTool(BaseTool):
    """维修工单工具集。"""
    name = "workorder"

    @tool(
        name="create_workorder",
        description="创建设备维修工单，返回工单号。用于把 Agent 的建议落地为可执行动作。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "title": {"type": "string", "description": "工单标题"},
            "priority": {"type": "string", "description": "优先级 low/normal/high，默认 normal"},
        },
        required=["eid", "title"],
    )
    async def create_workorder(self, eid: int, title: str, priority: str = "normal") -> ToolResult:
        wo_id = f"WO-{next(_counter)}"
        _WORKORDERS[wo_id] = {
            "wo_id": wo_id,
            "eid": int(eid),
            "title": title,
            "priority": priority,
            "status": "created",
        }
        return ToolResult.ok(data=_WORKORDERS[wo_id], message=f"工单 {wo_id} 创建成功")

    @tool(
        name="query_workorder",
        description="查询已创建的维修工单。",
        parameters={
            "wo_id": {"type": "string", "description": "工单号，留空返回全部"},
        },
        required=[],
    )
    async def query_workorder(self, wo_id: str = "") -> ToolResult:
        if wo_id:
            return ToolResult.ok(data=_WORKORDERS.get(wo_id), message="查询完成")
        return ToolResult.ok(data=list(_WORKORDERS.values()), message="查询完成")
