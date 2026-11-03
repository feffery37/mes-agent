#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : equipment.py
@Desc    : 设备主数据与报警查询工具（对应数据域 EQ_EQUIPMENT / EQ_ALARM_LOG）。
           能力：查现状（设备型号、控制限、最新值）。
"""
import logging

from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.data import sample

logger = logging.getLogger(__name__)


class EquipmentTool(BaseTool):
    """设备查询工具集。"""
    name = "equipment"

    @tool(
        name="query_equipment",
        description="查询设备主数据：型号、所属产线、参数控制限(上下限)、单位等。用于回答“设备型号/控制限是多少”等问题。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID，如 1 表示 1 号邦定机"},
        },
        required=["eid"],
    )
    async def query_equipment(self, eid: int) -> ToolResult:
        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return ToolResult.fail(f"未找到设备 eid={eid}")
        # 取最新工艺参数值
        latest = None
        param = equip.get("param")
        series = sample.PARAM_TS.get(int(eid), {}).get(param)
        if series:
            latest = series[-1]["value"]
        data = {**equip, "latest_value": latest}
        return ToolResult.ok(data=data, message="查询设备主数据成功")

    @tool(
        name="query_alarm_log",
        description="查询指定设备最近 N 天的报警日志，用于回答“昨天/今天有哪些报警”等问题。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "days": {"type": "integer", "description": "查询最近几天，默认 1"},
        },
        required=["eid"],
    )
    async def query_alarm_log(self, eid: int, days: int = 1) -> ToolResult:
        logs = sample.ALARM_LOG.get(int(eid), [])
        return ToolResult.ok(
            data={"eid": int(eid), "days": days, "count": len(logs), "alarms": logs},
            message=f"查询到 {len(logs)} 条报警",
        )
