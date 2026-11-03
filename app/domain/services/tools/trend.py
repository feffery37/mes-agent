#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : trend.py
@Desc    : 稳健趋势分析工具（对应数据域 EQ_PARAM_TS）。
           调用 Theil-Sen + Bootstrap，输出斜率、95% 置信区间与是否显著。
           对应方案第5章：脏数据环境下稳健判断趋势。
"""
import logging

from app.domain.models.tool_result import ToolResult
from app.domain.services.analysis.theil_sen import analyze_trend
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.data import sample

logger = logging.getLogger(__name__)

_WINDOW_HOURS = {"1d": 24, "3d": 72, "7d": 168, "30d": 720}


class TrendTool(BaseTool):
    """趋势分析工具集。"""
    name = "trend"

    @tool(
        name="analyze_trend",
        description="对设备某一工艺参数做稳健趋势分析（Theil-Sen 斜率 + Bootstrap 95% 置信区间），"
                    "判断趋势是否显著上升/下降。用于回答“最近温度是不是在上升”等问题。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "param": {"type": "string", "description": "参数名，如 TEMP_NOZZLE"},
            "window": {"type": "string", "description": "时间窗，可选 1d/3d/7d/30d，默认 7d"},
        },
        required=["eid", "param"],
    )
    async def analyze_trend(self, eid: int, param: str, window: str = "7d") -> ToolResult:
        series = sample.PARAM_TS.get(int(eid), {}).get(param)
        if not series:
            return ToolResult.fail(f"未找到设备 eid={eid} 的参数 {param} 时序")

        hours = _WINDOW_HOURS.get(window, 168)
        values = [p["value"] for p in series[-hours:]]
        result = analyze_trend(values)
        result.update({"eid": int(eid), "param": param, "window": window, "points": len(values)})
        return ToolResult.ok(data=result, message="趋势分析完成")
