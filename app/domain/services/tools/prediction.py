#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : prediction.py
@Desc    : 故障预测与可解释性工具（对应方案第4章 predict_failure / explain）。
           基础框架用「趋势斜率 + 越限占比」构造退化特征，给出故障概率与 SHAP 风格解释，
           后续可替换为 LightGBM + 真实 SHAP（见方案第5章决策记录）。
"""
import logging
import math

from app.domain.models.tool_result import ToolResult
from app.domain.services.analysis.theil_sen import analyze_trend
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.data import sample

logger = logging.getLogger(__name__)

# 故障概率阈值（方案建议用成本矩阵扫描，这里给演示默认值）
FAILURE_THRESHOLD = 0.22


class PredictionTool(BaseTool):
    """故障预测工具集。"""
    name = "prediction"

    @staticmethod
    def _features(eid: int, param: str):
        equip = sample.EQUIPMENT.get(int(eid), {})
        control_max = equip.get("control_max")
        control_min = equip.get("control_min")
        series = sample.PARAM_TS.get(int(eid), {}).get(param, [])
        if not series:
            return None
        values = [p["value"] for p in series]
        trend = analyze_trend(values[-168:])
        over = sum(1 for v in values if control_max and v > control_max) / max(len(values), 1)
        return {
            "eid": int(eid),
            "param": param,
            "sen_slope": trend["slope"],
            "over_rate": round(over, 4),
            "latest": trend["latest"],
            "control_max": control_max,
            "control_min": control_min,
        }

    @tool(
        name="predict_failure",
        description="预测设备在指定时间窗内发生故障的概率（基于趋势退化特征）。"
                    "用于回答“未来几天会不会出问题”等问题。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "horizon": {"type": "string", "description": "预测时域，如 24h/72h/168h，默认 72h"},
        },
        required=["eid"],
    )
    async def predict_failure(self, eid: int, horizon: str = "72h") -> ToolResult:
        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return ToolResult.fail(f"未找到设备 eid={eid}")
        feat = self._features(int(eid), equip.get("param"))
        if not feat:
            return ToolResult.fail("缺少工艺参数时序")

        # 演示用：sigmoid 组合退化特征 -> 概率（真实场景用 LightGBM）
        score = 3.0 * feat["sen_slope"] + 2.5 * feat["over_rate"]
        prob = 1.0 / (1.0 + math.exp(-score))
        will_fail = prob >= FAILURE_THRESHOLD
        data = {
            **feat,
            "horizon": horizon,
            "failure_probability": round(prob, 3),
            "threshold": FAILURE_THRESHOLD,
            "predicted": will_fail,
            "eta_hours": round(48 * (1 - prob), 1) if will_fail else None,
        }
        return ToolResult.ok(data=data, message="预测完成")

    @tool(
        name="explain",
        description="对预测结果做可解释性说明（SHAP 风格特征贡献），帮助工程师判断依据。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "horizon": {"type": "string", "description": "预测时域，默认 72h"},
        },
        required=["eid"],
    )
    async def explain(self, eid: int, horizon: str = "72h") -> ToolResult:
        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return ToolResult.fail(f"未找到设备 eid={eid}")
        feat = self._features(int(eid), equip.get("param"))
        if not feat:
            return ToolResult.fail("缺少工艺参数时序")
        # 演示用 SHAP 风格贡献（与方案示例一致：sen_slope 贡献最大）
        contributions = [
            {"feature": "sen_slope", "value": feat["sen_slope"], "contribution": round(0.31 + feat["sen_slope"], 3)},
            {"feature": "over_rate", "value": feat["over_rate"], "contribution": round(0.19 * (1 + feat["over_rate"] * 5), 3)},
        ]
        return ToolResult.ok(
            data={"eid": int(eid), "horizon": horizon, "contributions": contributions},
            message="解释完成",
        )
