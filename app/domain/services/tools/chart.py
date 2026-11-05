#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : chart.py
@Desc    : 可视化图表工具集。
           工具本身不产出图片，而是产出「图表规格(chart spec)」随工具结果返回，
           由前端用 Recharts 渲染成可交互图表，直接在对话里看图做分析。
           spec 结构：{kind, title, x_label, y_label, unit, data[], series[], ref_lines[]}
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from app.domain.models.tool_result import ToolResult
from app.domain.services.analysis.theil_sen import theil_sen_slope
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.data import sample

logger = logging.getLogger(__name__)

_WINDOW_HOURS = {"1d": 24, "3d": 72, "7d": 168, "30d": 720}
_MAX_POINTS = 72


def _downsample(points: List[Dict[str, Any]], max_points: int = _MAX_POINTS) -> List[Dict[str, Any]]:
    """按固定步长抽稀，保留首尾点，避免前端渲染上千个点。"""
    n = len(points)
    if n <= max_points:
        return points
    step = n / float(max_points)
    idx = sorted({int(i * step) for i in range(max_points)} | {n - 1})
    return [points[i] for i in idx]


def _fmt_ts(ts: str) -> str:
    """把 2026-11-05 09:00 压缩成 11-05 09:00，便于 X 轴展示。"""
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M").strftime("%m-%d %H:%M")
    except Exception:
        return ts


class ChartTool(BaseTool):
    """图表工具集：把分析结果转成前端可渲染的图表规格。"""
    name = "chart"

    @tool(
        name="plot_param_trend",
        description="把设备工艺参数的趋势画成折线图（实测曲线 + 稳健趋势线 + 控制上下限参考线），"
                    "图表会直接渲染给用户看。当用户要求「画图/可视化/图表/曲线」或需要直观展示趋势时调用。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "param": {"type": "string", "description": "参数名，如 TEMP_NOZZLE"},
            "window": {"type": "string", "description": "时间窗，可选 1d/3d/7d/30d，默认 7d"},
        },
        required=["eid", "param"],
    )
    async def plot_param_trend(self, eid: int, param: str, window: str = "7d") -> ToolResult:
        equip = sample.EQUIPMENT.get(int(eid))
        series = sample.PARAM_TS.get(int(eid), {}).get(param)
        if not equip or not series:
            return ToolResult.fail(f"未找到设备 eid={eid} 的参数 {param} 时序")

        hours = _WINDOW_HOURS.get(window, 168)
        window_points = series[-hours:]
        values = np.asarray([p["value"] for p in window_points], dtype=float)

        # Theil-Sen 稳健斜率 + 中位数截距，得到趋势拟合线
        slope = theil_sen_slope(values)
        idx = np.arange(len(values), dtype=float)
        intercept = float(np.median(values - slope * idx))

        indexed = [{"i": i, **p} for i, p in enumerate(window_points)]
        data = [
            {
                "t": _fmt_ts(p["ts"]),
                "value": p["value"],
                "trend": round(intercept + slope * p["i"], 2),
            }
            for p in _downsample(indexed)
        ]

        unit = equip.get("unit", "")
        cmin, cmax = equip.get("control_min"), equip.get("control_max")
        ref_lines = []
        if cmax is not None:
            ref_lines.append({"y": cmax, "label": f"控制上限 {cmax}{unit}"})
        if cmin is not None:
            ref_lines.append({"y": cmin, "label": f"控制下限 {cmin}{unit}"})

        latest = float(values[-1])
        chart = {
            "kind": "line",
            "title": f"{equip['name']} · {equip['param_desc']}趋势（{window}）",
            "x_label": "时间",
            "y_label": f"{equip['param_desc']}({unit})",
            "unit": unit,
            "data": data,
            "series": [
                {"key": "value", "name": "实测值", "style": "solid"},
                {"key": "trend", "name": "Theil-Sen 趋势线", "style": "dashed"},
            ],
            "ref_lines": ref_lines,
            "meta": {
                "slope_per_hour": round(slope, 4),
                "latest": latest,
                "window": window,
                "points": len(values),
            },
        }
        direction = "上升" if slope > 0 else ("下降" if slope < 0 else "平稳")
        return ToolResult.ok(
            data={"eid": int(eid), "param": param, "window": window, "chart": chart},
            message=f"已生成趋势图：{equip['param_desc']}整体{direction}（斜率 {round(slope, 4)}/h），最新 {latest}{unit}",
        )

    @tool(
        name="plot_alarm_distribution",
        description="把设备的报警记录画成按日期统计的柱状图，便于看报警频次分布。"
                    "当用户要求「画报警分布/哪个时间段报警多/可视化报警情况」时调用。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "days": {"type": "integer", "description": "统计最近几天，默认 7"},
        },
        required=["eid"],
    )
    async def plot_alarm_distribution(self, eid: int, days: int = 7) -> ToolResult:
        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return ToolResult.fail(f"未找到设备 eid={eid}")
        logs = sample.ALARM_LOG.get(int(eid), [])
        if not logs:
            return ToolResult.fail(f"{equip['name']} 最近 {days} 天没有报警记录，暂无可视化数据")

        by_date: Dict[str, int] = {}
        by_code: Dict[str, int] = {}
        for item in logs:
            day = str(item.get("time", ""))[:10]
            by_date[day] = by_date.get(day, 0) + 1
            code = str(item.get("code", ""))
            by_code[code] = by_code.get(code, 0) + 1

        data = [{"t": d[5:], "count": c} for d, c in sorted(by_date.items())]
        chart = {
            "kind": "bar",
            "title": f"{equip['name']} · 报警次数分布（最近 {days} 天）",
            "x_label": "日期",
            "y_label": "报警次数",
            "unit": "次",
            "data": data,
            "series": [{"key": "count", "name": "报警次数", "style": "solid"}],
            "ref_lines": [],
            "meta": {"total": len(logs), "by_code": by_code},
        }
        return ToolResult.ok(
            data={"eid": int(eid), "days": days, "chart": chart},
            message=f"已生成报警分布图：共 {len(logs)} 条，占比最高的是 {max(by_code, key=by_code.get)}",
        )

    @tool(
        name="plot_failure_risk",
        description="把设备在不同时间窗（24h/72h/168h）内的故障概率画成柱状图，直观展示风险随时间的增长。"
                    "当用户要求「画风险图/可视化故障概率」时调用。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
        },
        required=["eid"],
    )
    async def plot_failure_risk(self, eid: int) -> ToolResult:
        from app.domain.services.tools.prediction import PredictionTool

        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return ToolResult.fail(f"未找到设备 eid={eid}")

        base = await PredictionTool().predict_failure(int(eid), "72h")
        if not base.success or not base.data:
            return ToolResult.fail(base.message or "故障预测失败")

        p72 = float(base.data["failure_probability"])
        threshold = float(base.data.get("threshold", 0.22))
        data = []
        for label, hours in (("24h", 24), ("72h", 72), ("168h", 168)):
            # 按指数风险累积把 72h 概率外推到其它时域（演示口径）
            prob = 1.0 - (1.0 - p72) ** (hours / 72.0)
            data.append({"t": label, "prob": round(prob * 100, 1)})

        chart = {
            "kind": "bar",
            "title": f"{equip['name']} · 故障概率随时间窗变化",
            "x_label": "预测时域",
            "y_label": "故障概率(%)",
            "unit": "%",
            "data": data,
            "series": [{"key": "prob", "name": "故障概率", "style": "solid"}],
            "ref_lines": [{"y": round(threshold * 100, 1), "label": f"告警阈值 {round(threshold * 100, 1)}%"}],
            "meta": {"horizon_72h_prob": p72, "predicted": base.data.get("predicted")},
        }
        return ToolResult.ok(
            data={"eid": int(eid), "chart": chart},
            message=f"已生成风险图：72h 故障概率 {round(p72 * 100, 1)}%",
        )
