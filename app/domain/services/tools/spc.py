#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : spc.py
@Desc    : SPC 判异工具（只读分析，不产生任何副作用、不触发自动通知）。
           用受控基线期稳健估计 ±1/2/3σ，按配置规则集检出非随机模式，并与 Theil-Sen 交叉验证。
"""
import logging
from typing import List, Optional

from app.domain.models.spc_result import SpcResult, SpcViolation
from app.domain.models.tool_result import ToolResult
from app.domain.services.analysis.spc import (
    RULE_TITLES,
    build_limits,
    estimate_sigma,
    evaluate_rules,
)
from app.domain.services.analysis.theil_sen import analyze_trend
from app.domain.services.tools.base import BaseTool, tool
from app.infrastructure.data import sample
from core.config import SpcConfig, get_app_config

logger = logging.getLogger(__name__)

_WINDOW_HOURS = {"1d": 24, "3d": 72, "7d": 168, "30d": 720}


class SpcTool(BaseTool):
    """SPC 控制图判异工具集。"""
    name = "spc"

    @tool(
        name="check_spc_rules",
        description="按 SPC 控制图规则（Nelson / Western Electric）判断设备参数过程是否受控。"
                    "用受控基线期稳健估计 ±1/2/3σ 控制限，返回规则命中清单、z 值、样本量与结论分级。"
                    "用于回答「是否失控 / 判异 / SPC / 有没有异常模式」等问题。只读，不产生任何写操作。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "param": {"type": "string", "description": "参数名，留空取设备主参数"},
            "window": {"type": "string", "description": "时间窗 1d/3d/7d/30d，默认 7d"},
            "rules": {
                "type": "array",
                "items": {"type": "string"},
                "description": "可选规则子集，如 N1/N2/N3/N5/N6/C1，留空用配置默认",
            },
        },
        required=["eid"],
    )
    async def check_spc_rules(
            self,
            eid: int,
            param: str = "",
            window: str = "7d",
            rules: Optional[List[str]] = None,
    ) -> ToolResult:
        cfg: SpcConfig = get_app_config().spc
        if not cfg.enabled:
            return ToolResult.fail("SPC 判异功能已关闭（spc.enabled=false）")

        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return ToolResult.fail(f"未找到设备 eid={eid}")
        param = param or equip.get("param", "")
        series = sample.PARAM_TS.get(int(eid), {}).get(param)
        if not series:
            return ToolResult.fail(f"未找到 eid={eid} 的参数 {param} 时序")

        hours = _WINDOW_HOURS.get(window, 168)
        window_points = series[-hours:]
        values = [p["value"] for p in window_points]
        ts = [p["ts"] for p in window_points]
        n = len(values)

        baseline = sample.BASELINE_TS.get(int(eid), {}).get(param, [])[-cfg.baseline_window_hours:]
        usable = [p["value"] for p in baseline if not p.get("excluded") and p.get("value") is not None]
        excluded = len(baseline) - len(usable)
        if len(usable) < 20:
            return ToolResult.fail("受控基线期样本不足（<20），无法估计 sigma")

        center, sigma, sigma_meta = estimate_sigma(usable, cfg.sigma_method)
        limits = build_limits(center, sigma, equip.get("control_min"), equip.get("control_max"))
        meta = sample.PARAM_META.get(int(eid), {}).get(param, {})

        selected = [r for r in (rules or cfg.rules) if r in RULE_TITLES] or list(cfg.rules)
        violations = evaluate_rules(
            values, ts, center, sigma, selected,
            c1_min_points=cfg.c1_min_points,
            c1_min_slope=cfg.c1_min_slope,
        )

        # N3 / C1（趋势类规则）与 Theil-Sen + Bootstrap 交叉验证
        cross = None
        if any(v["rule"] in ("N3", "C1") for v in violations):
            trend = analyze_trend(values)
            cross = {
                key: trend[key]
                for key in ("slope", "ci_low", "ci_high", "significant", "conclusion")
            }
            check_text = (
                f"趋势斜率 {trend['slope']}/h，95% CI "
                f"[{trend['ci_low']}, {trend['ci_high']}]，"
                f"{'显著' if trend['significant'] else '不显著'}"
            )
            for v in violations:
                if v["rule"] in ("N3", "C1"):
                    v["cross_check"] = check_text

        caveats = [
            f"工艺规格限（{equip.get('control_min')} ~ {equip.get('control_max')}）用于判合格，"
            "与统计控制限 ±3σ 不是一回事",
            f"sigma 来自受控基线期 {len(usable)} 点（{sigma_meta['method']}），"
            f"已排除 {excluded} 个停机 / 试产 / 复测口径标记点",
        ]
        if meta.get("limits_version"):
            caveats.append(
                f"口径版本 LIMITS_VERSION={meta['limits_version']}；若规格或复测口径变更，结论需重新判定"
            )
        else:
            caveats.append("LIMITS_VERSION 缺失，涉及 Cpk / 规格的结论标注【无法判断】")
        if n < cfg.downgrade_n:
            caveats.append(f"当前窗口 n={n} < {cfg.downgrade_n}，结论降级为【推测】")
        if sigma_meta.get("degenerate"):
            caveats.append(f"基线离散度为 0：{sigma_meta.get('reason')}")
        caveats.append("强自相关时序可能使游程类规则虚报，必要时先做差分或改用 Block Bootstrap")
        caveats.append("规则命中仅说明过程异常，根因「相关，因果待验证」；其他机台同期异常需并列给出")

        # 同一规则可能命中很多段（如周期性噪声导致 N3 反复命中），明细按规则限流，
        # 但命中总数在结论与 caveats 中如实给出，不隐瞒不利证据。
        total_by_rule: dict[str, int] = {}
        for v in violations:
            total_by_rule[v["rule"]] = total_by_rule.get(v["rule"], 0) + 1
        total_hits = len(violations)
        seen: dict[str, int] = {}
        shown = []
        for v in violations:
            rule = v["rule"]
            seen[rule] = seen.get(rule, 0) + 1
            if seen[rule] <= cfg.max_segments_per_rule:
                shown.append(v)
        truncated = {r: c for r, c in total_by_rule.items() if c > cfg.max_segments_per_rule}
        if truncated:
            caveats.append(
                f"违规明细按规则限流展示（每规则前 {cfg.max_segments_per_rule} 段）："
                + "、".join(f"{r} 共 {c} 段" for r, c in truncated.items())
            )

        if n < cfg.n_min or sigma_meta.get("degenerate"):
            verdict, grade = "无法判断", "无法判断"
        else:
            grade = "推测" if n < cfg.downgrade_n else "数据支持"
            critical = any(v["severity"] == "critical" for v in violations)
            enough = total_hits >= (2 if cfg.require_two_rules else 1)
            verdict = "失控" if (critical or enough) else ("需关注" if total_hits else "受控")

        if verdict == "无法判断":
            conclusion = "【无法判断】样本量或基线离散度不足，需补充受控基线数据后再判异。"
        elif verdict == "受控":
            conclusion = (
                f"【{grade}】当前窗口 {n} 个点未命中 {', '.join(selected)} 中任何判异规则，过程受控。"
            )
        else:
            hit_rules = "、".join(sorted(total_by_rule))
            conclusion = (
                f"【{grade}】{verdict}：命中 {total_hits} 段违规（{hit_rules}）；"
                f"基线 center={round(center, 4)}、sigma={round(sigma, 4)}、n={len(usable)}。"
                "规则命中仅说明过程异常，根因「相关，因果待验证」。"
            )

        result = SpcResult(
            eid=int(eid),
            param=param,
            window=window,
            n=n,
            baseline={
                "n": len(usable),
                "excluded": excluded,
                "center": round(center, 4),
                "sigma": round(sigma, 4),
                "method": sigma_meta["method"],
                "limits_version": meta.get("limits_version", "未知"),
                "degenerate": sigma_meta.get("degenerate", False),
            },
            limits=limits,
            rule_set=selected,
            violations=[SpcViolation(**v) for v in shown],
            verdict=verdict,
            grade=grade,
            conclusion=conclusion,
            caveats=caveats,
            cross_check=cross,
            time_range={"start": ts[0], "end": ts[-1]},
        )
        return ToolResult.ok(
            data=result.model_dump(),
            message=f"SPC 判异完成：{verdict}（命中 {total_hits} 段违规）",
        )
