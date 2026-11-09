#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : spc.py
@Desc    : SPC 控制图判异工具（只读分析，不产生任何副作用、不触发自动通知）。
           P0: check_spc_rules；P1: 控制图、C1 参数化与解释、LIMITS_VERSION 校验、多设备同期对比。
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set

from app.domain.models.spc_result import SpcResult, SpcViolation
from app.domain.models.tool_result import ToolResult
from app.domain.services.analysis.spc import (
    RULE_DESCRIPTIONS,
    RULE_SEVERITY,
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


def _fmt_ts(ts: str) -> str:
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M").strftime("%m-%d %H:%M")
    except Exception:
        return ts


class SpcTool(BaseTool):
    """SPC 控制图判异工具集（P0 + P1）。"""
    name = "spc"

    # ------------------------------------------------------------------
    # 共享计算：check_spc_rules / plot_control_chart 复用同一套口径
    # ------------------------------------------------------------------
    def _check_limits_version(
            self,
            eid: int,
            param: str,
            window_start: str,
            baseline_start: str,
            cfg: SpcConfig,
            expected_version: str,
    ) -> Dict:
        """校验口径版本：显式期望值不匹配为硬失败；历史变更落在基线/窗口内为软告警。"""
        meta = sample.PARAM_META.get(eid, {}).get(param, {})
        current = meta.get("limits_version", "未知")
        expected = expected_version or cfg.expected_limits_version or ""
        history = sample.LIMITS_HISTORY.get(eid, {}).get(param, [])
        status: Dict = {
            "current": current,
            "expected": expected,
            "history": history,
            "baseline_changed": False,
            "window_changed": False,
            "ok": True,
            "note": "口径版本一致，基线期与当前窗口内无变更",
            "hard_error": "",
        }
        if expected and expected != current:
            status["ok"] = False
            status["hard_error"] = f"口径版本不匹配：期望 {expected}，当前 {current}，请人工确认后再判异"
            status["note"] = status["hard_error"]
            return status

        for item in history:
            effective = item.get("effective_from", "")
            if not effective:
                continue
            if baseline_start and effective > baseline_start:
                status["baseline_changed"] = True
            if window_start and effective > window_start:
                status["window_changed"] = True
        if status["baseline_changed"] or status["window_changed"]:
            status["ok"] = False
            status["note"] = (
                "基线期或当前窗口内发生规格 / 复测口径版本变更，"
                "sigma 与判异结论需人工复核（结论已降级为【推测】）"
            )
        return status

    def _peer_comparison(
            self,
            eid: int,
            equip: Dict,
            param: str,
            hours: int,
            cfg: SpcConfig,
            selected: Sequence[str],
            own_rules: Set[str],
    ) -> Dict:
        """同产线 + 同参数的其他机台同期对比（呼应「不得隐瞒不利证据」）。"""
        peers = []
        for peer_eid, peer_equip in sample.EQUIPMENT.items():
            if peer_eid == eid:
                continue
            if peer_equip.get("line") != equip.get("line") or peer_equip.get("param") != param:
                continue
            peer_series = sample.PARAM_TS.get(peer_eid, {}).get(param, [])
            peer_baseline = sample.BASELINE_TS.get(peer_eid, {}).get(param, [])
            if not peer_series or not peer_baseline:
                continue
            points = peer_series[-hours:]
            values = [p["value"] for p in points]
            ts = [p["ts"] for p in points]
            usable = [p["value"] for p in peer_baseline[-cfg.baseline_window_hours:]
                      if not p.get("excluded") and p.get("value") is not None]
            if len(usable) < 20:
                continue
            center, sigma, meta = estimate_sigma(usable, cfg.sigma_method)
            if meta.get("degenerate") or sigma <= 0:
                continue
            hits = evaluate_rules(
                values, ts, center, sigma, selected,
                c1_min_points=cfg.c1_min_points,
                c1_min_slope=cfg.c1_min_slope,
                c1_sigma=cfg.c1_sigma,
            )
            peer_rules = sorted({h["rule"] for h in hits})
            peers.append({
                "eid": peer_eid,
                "name": peer_equip.get("name", ""),
                "n": len(values),
                "verdict": "失控" if any(h["severity"] == "critical" for h in hits) or len(hits) >= 2
                           else ("需关注" if hits else "受控"),
                "hits": len(hits),
                "rules": peer_rules,
                "max_z": round(max((abs(v - center) / sigma for v in values), default=0.0), 2),
                "same_pattern": bool(own_rules.intersection(peer_rules)),
                "limits_version": sample.PARAM_META.get(peer_eid, {}).get(param, {}).get("limits_version", "未知"),
            })

        if not peers:
            note = "未找到同产线同参数的对照机台，无法进行同期对比"
        else:
            common = sorted({r for p in peers for r in p["rules"]} & own_rules)
            if common:
                note = (f"其他机台同期也命中 {'、'.join(common)}，"
                        "需考虑产线级系统性因素，不得只归因于本机台")
            else:
                note = ("同产线同参数的对照机台未命中本机台同样的判异规则，"
                        "异常更可能是本机台特有（相关，因果待验证）")
        return {"group_by": "line+param", "peers": peers, "note": note}

    def _compute(
            self,
            eid: int,
            param: str,
            window: str,
            rules: Optional[List[str]],
            compare_peers: Optional[bool],
            expected_version: str,
            cfg: SpcConfig,
            with_cross: bool = True,
    ) -> Dict:
        """一次完整判异计算，返回上下文；出错时返回 {"error": ...}。"""
        equip = sample.EQUIPMENT.get(int(eid))
        if not equip:
            return {"error": f"未找到设备 eid={eid}"}
        param = param or equip.get("param", "")
        series = sample.PARAM_TS.get(int(eid), {}).get(param)
        if not series:
            return {"error": f"未找到 eid={eid} 的参数 {param} 时序"}

        hours = _WINDOW_HOURS.get(window, 168)
        window_points = series[-hours:]
        values = [p["value"] for p in window_points]
        ts = [p["ts"] for p in window_points]
        n = len(values)

        baseline = sample.BASELINE_TS.get(int(eid), {}).get(param, [])[-cfg.baseline_window_hours:]
        usable = [p["value"] for p in baseline if not p.get("excluded") and p.get("value") is not None]
        excluded = len(baseline) - len(usable)
        if len(usable) < 20:
            return {"error": "受控基线期样本不足（<20），无法估计 sigma"}

        version_status = self._check_limits_version(
            int(eid), param, ts[0], baseline[0]["ts"] if baseline else "", cfg, expected_version
        )
        if version_status.get("hard_error"):
            return {"error": version_status["hard_error"]}

        center, sigma, sigma_meta = estimate_sigma(usable, cfg.sigma_method)
        limits = build_limits(center, sigma, equip.get("control_min"), equip.get("control_max"))
        selected = [r for r in (rules or cfg.rules) if r in RULE_TITLES] or list(cfg.rules)
        violations = evaluate_rules(
            values, ts, center, sigma, selected,
            c1_min_points=cfg.c1_min_points,
            c1_min_slope=cfg.c1_min_slope,
            c1_sigma=cfg.c1_sigma,
        )

        cross = None
        if with_cross and any(v["rule"] in ("N3", "C1") for v in violations):
            trend = analyze_trend(values)
            cross = {key: trend[key] for key in
                     ("slope", "ci_low", "ci_high", "significant", "conclusion")}
            check_text = (
                f"趋势斜率 {trend['slope']}/h，95% CI "
                f"[{trend['ci_low']}, {trend['ci_high']}]，"
                f"{'显著' if trend['significant'] else '不显著'}"
            )
            for v in violations:
                if v["rule"] in ("N3", "C1"):
                    v["cross_check"] = check_text

        total_by_rule: Dict[str, int] = {}
        for v in violations:
            total_by_rule[v["rule"]] = total_by_rule.get(v["rule"], 0) + 1
        total_hits = len(violations)

        peer_result = None
        want_peers = cfg.compare_peers_by_default if compare_peers is None else compare_peers
        if want_peers:
            peer_result = self._peer_comparison(
                int(eid), equip, param, hours, cfg, selected, set(total_by_rule)
            )

        caveats = [
            f"工艺规格限（{equip.get('control_min')} ~ {equip.get('control_max')}）用于判合格，"
            "与统计控制限 ±3σ 不是一回事",
            f"sigma 来自受控基线期 {len(usable)} 点（{sigma_meta['method']}），"
            f"已排除 {excluded} 个停机 / 试产 / 复测口径标记点",
            f"口径版本 LIMITS_VERSION={version_status['current']}；{version_status['note']}",
        ]
        if n < cfg.downgrade_n:
            caveats.append(f"当前窗口 n={n} < {cfg.downgrade_n}，结论降级为【推测】")
        if sigma_meta.get("degenerate"):
            caveats.append(f"基线离散度为 0：{sigma_meta.get('reason')}")
        caveats.append("强自相关时序可能使游程类规则虚报，必要时先做差分或改用 Block Bootstrap")
        caveats.append("规则命中仅说明过程异常，根因「相关，因果待验证」")
        if peer_result:
            caveats.append(f"同期对比：{peer_result['note']}")

        version_downgrade = not version_status["ok"]
        if n < cfg.n_min or sigma_meta.get("degenerate"):
            verdict, grade = "无法判断", "无法判断"
        else:
            grade = "推测" if (n < cfg.downgrade_n or version_downgrade) else "数据支持"
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
            if version_downgrade:
                conclusion += " 口径版本变更，结论需人工复核。"
            if peer_result:
                conclusion += f" 同期对比：{peer_result['note']}"

        return {
            "eid": int(eid), "param": param, "window": window, "n": n,
            "equip": equip, "values": values, "ts": ts,
            "center": center, "sigma": sigma, "sigma_meta": sigma_meta,
            "usable_n": len(usable), "excluded": excluded,
            "limits": limits, "selected": selected, "violations": violations,
            "total_by_rule": total_by_rule, "total_hits": total_hits,
            "cross": cross, "caveats": caveats, "verdict": verdict, "grade": grade,
            "conclusion": conclusion, "version_status": version_status,
            "peer_result": peer_result,
            "time_range": {"start": ts[0], "end": ts[-1]},
        }

    # ------------------------------------------------------------------
    # @tool: 判异主入口
    # ------------------------------------------------------------------
    @tool(
        name="check_spc_rules",
        description="按 SPC 控制图规则（Nelson / Western Electric）判断设备参数过程是否受控。"
                    "用受控基线期稳健估计 ±1/2/3σ，校验 LIMITS_VERSION，可对比同产线同参数的其他机台。"
                    "用于回答「是否失控 / 判异 / SPC / 同期对比」等问题。只读，不产生任何写操作。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "param": {"type": "string", "description": "参数名，留空取设备主参数"},
            "window": {"type": "string", "description": "时间窗 1d/3d/7d/30d，默认 7d"},
            "rules": {"type": "array", "items": {"type": "string"},
                      "description": "可选规则子集 N1/N2/N3/N5/N6/C1，留空用配置默认"},
            "compare_peers": {"type": "boolean",
                              "description": "是否对比同产线同参数的其他机台，默认按配置"},
            "expected_version": {"type": "string",
                                 "description": "期望的 LIMITS_VERSION，非空且与当前版本不符时拒绝判定"},
        },
        required=["eid"],
    )
    async def check_spc_rules(
            self,
            eid: int,
            param: str = "",
            window: str = "7d",
            rules: Optional[List[str]] = None,
            compare_peers: Optional[bool] = None,
            expected_version: str = "",
    ) -> ToolResult:
        cfg: SpcConfig = get_app_config().spc
        if not cfg.enabled:
            return ToolResult.fail("SPC 判异功能已关闭（spc.enabled=false）")
        ctx = self._compute(eid, param, window, rules, compare_peers, expected_version, cfg)
        if "error" in ctx:
            return ToolResult.fail(ctx["error"])

        # 同规则多段明细限流展示，命中总数在结论与 caveats 中如实给出
        seen: Dict[str, int] = {}
        shown = []
        for v in ctx["violations"]:
            rule = v["rule"]
            seen[rule] = seen.get(rule, 0) + 1
            if seen[rule] <= cfg.max_segments_per_rule:
                shown.append(v)
        truncated = {r: c for r, c in ctx["total_by_rule"].items()
                     if c > cfg.max_segments_per_rule}
        caveats = list(ctx["caveats"])
        if truncated:
            caveats.append(
                f"违规明细按规则限流展示（每规则前 {cfg.max_segments_per_rule} 段）："
                + "、".join(f"{r} 共 {c} 段" for r, c in truncated.items())
            )

        result = SpcResult(
            eid=ctx["eid"], param=ctx["param"], window=ctx["window"], n=ctx["n"],
            baseline={
                "n": ctx["usable_n"], "excluded": ctx["excluded"],
                "center": round(ctx["center"], 4), "sigma": round(ctx["sigma"], 4),
                "method": ctx["sigma_meta"]["method"],
                "limits_version": ctx["version_status"]["current"],
                "degenerate": ctx["sigma_meta"].get("degenerate", False),
            },
            limits=ctx["limits"], rule_set=ctx["selected"],
            violations=[SpcViolation(**v) for v in shown],
            verdict=ctx["verdict"], grade=ctx["grade"], conclusion=ctx["conclusion"],
            caveats=caveats, cross_check=ctx["cross"],
            limits_version_status=ctx["version_status"],
            peer_comparison=ctx["peer_result"],
            time_range=ctx["time_range"],
        )
        return ToolResult.ok(
            data=result.model_dump(),
            message=f"SPC 判异完成：{ctx['verdict']}（命中 {ctx['total_hits']} 段违规）",
        )

    # ------------------------------------------------------------------
    # @tool: 控制图（P1）
    # ------------------------------------------------------------------
    @tool(
        name="plot_control_chart",
        description="绘制 SPC 控制图：实测值 + 中心线 + ±1/2/3σ 控制限 + 规格限 + 判异点标红，"
                    "图表直接渲染给用户看。当用户要求「控制图 / SPC 图 / 画判异图」时调用。只读。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "param": {"type": "string", "description": "参数名，留空取设备主参数"},
            "window": {"type": "string", "description": "时间窗 1d/3d/7d/30d，默认 7d"},
        },
        required=["eid"],
    )
    async def plot_control_chart(
            self, eid: int, param: str = "", window: str = "7d"
    ) -> ToolResult:
        cfg: SpcConfig = get_app_config().spc
        if not cfg.enabled:
            return ToolResult.fail("SPC 判异功能已关闭（spc.enabled=false）")
        ctx = self._compute(eid, param, window, None, None, "", cfg, with_cross=False)
        if "error" in ctx:
            return ToolResult.fail(ctx["error"])

        values, ts, limits = ctx["values"], ctx["ts"], ctx["limits"]
        n = len(values)
        # 红点只标「超出 ±3σ」的点（N1 等价条件）：游程类规则会覆盖整段，
        # 若把所有规则的索引并集都标红，曲线会整条变红而失去可读性。
        violation_idx: Set[int] = {
            i for i, v in enumerate(values)
            if abs((v - ctx["center"]) / ctx["sigma"]) > 3
        }

        max_points = cfg.control_chart_max_points
        if n <= max_points:
            indices = list(range(n))
        else:
            step = n / float(max_points)
            chosen: Set[int] = {int(i * step) for i in range(max_points)} | {0, n - 1}
            extra = sorted(violation_idx - chosen)
            if extra:
                k = min(len(extra), max(1, max_points // 2))
                chosen |= {extra[int(j * len(extra) / k)] for j in range(k)}
            indices = sorted(chosen)

        data = []
        for i in indices:
            row: Dict = {
                "t": _fmt_ts(ts[i]),
                "value": values[i],
                "cl": limits["cl"],
                "violation_value": values[i] if i in violation_idx else None,
            }
            for k in (1, 2, 3):
                row[f"ucl_{k}"] = limits[f"ucl_{k}"]
                row[f"lcl_{k}"] = limits[f"lcl_{k}"]
            data.append(row)

        series = [{"key": "value", "name": "实测值", "style": "solid"},
                  {"key": "cl", "name": "CL", "style": "limit"}]
        for k in (1, 2, 3):
            series.append({"key": f"ucl_{k}", "name": f"+{k}σ", "style": "limit"})
            series.append({"key": f"lcl_{k}", "name": f"-{k}σ", "style": "limit"})
        series.append({"key": "violation_value", "name": "判异点", "style": "marker"})

        ref_lines = []
        if limits.get("spec_max") is not None:
            ref_lines.append({"y": limits["spec_max"], "label": f"规格上限 {limits['spec_max']}{ctx['equip'].get('unit', '')}"})
        if limits.get("spec_min") is not None:
            ref_lines.append({"y": limits["spec_min"], "label": f"规格下限 {limits['spec_min']}{ctx['equip'].get('unit', '')}"})

        chart = {
            "kind": "line",
            "title": f"{ctx['equip']['name']} · {ctx['equip'].get('param_desc', ctx['param'])}控制图（{window}）",
            "x_label": "时间",
            "y_label": f"{ctx['equip'].get('param_desc', ctx['param'])}({ctx['equip'].get('unit', '')})",
            "unit": ctx["equip"].get("unit", ""),
            "data": data,
            "series": series,
            "ref_lines": ref_lines,
            "meta": {
                "control_chart": True,
                "center": limits["cl"], "sigma": limits["sigma"],
                "verdict": ctx["verdict"], "grade": ctx["grade"],
                "violations": ctx["total_hits"],
                "violation_points": len(violation_idx),
                "limits_version": ctx["version_status"]["current"],
                "baseline_n": ctx["usable_n"],
                "peers": len(ctx["peer_result"]["peers"]) if ctx["peer_result"] else 0,
            },
        }
        return ToolResult.ok(
            data={"eid": ctx["eid"], "param": ctx["param"], "window": window, "chart": chart},
            message=f"已生成控制图：{ctx['verdict']}，标红 {len(violation_idx)} 个判异点",
        )

    # ------------------------------------------------------------------
    # @tool: 规则解释（P1）
    # ------------------------------------------------------------------
    @tool(
        name="explain_spc_rule",
        description="解释某条 SPC 判异规则的触发条件、含义与局限，以及当前生效参数。只读。",
        parameters={
            "rule_id": {"type": "string", "description": "规则ID：N1/N2/N3/N5/N6/C1"},
        },
        required=["rule_id"],
    )
    async def explain_spc_rule(self, rule_id: str) -> ToolResult:
        cfg: SpcConfig = get_app_config().spc
        if rule_id not in RULE_DESCRIPTIONS:
            return ToolResult.fail(f"未知规则 {rule_id}，可选：{', '.join(RULE_DESCRIPTIONS)}")
        info = RULE_DESCRIPTIONS[rule_id]
        parameters = {}
        if rule_id == "C1":
            parameters = {
                "c1_min_points": cfg.c1_min_points,
                "c1_sigma": cfg.c1_sigma,
                "c1_min_slope": cfg.c1_min_slope,
            }
        return ToolResult.ok(
            data={
                "rule": rule_id,
                "title": RULE_TITLES[rule_id],
                "severity": RULE_SEVERITY[rule_id],
                "condition": info["condition"],
                "meaning": info["meaning"],
                "limitation": info["limitation"],
                "parameters": parameters,
                "enabled": rule_id in cfg.rules,
            },
            message=f"{rule_id}：{info['condition']}",
        )
