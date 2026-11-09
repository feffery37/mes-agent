#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : test_spc.py
@Desc    : SPC 判异单测：6 类异常模式 + 稳健性 + 工具链路 + P1 能力。
           运行：uv run pytest tests/test_spc.py -q
"""
import asyncio

from app.domain.services.analysis.spc import (
    build_limits,
    estimate_sigma,
    evaluate_rules,
)
from app.domain.services.tools.spc import SpcTool

CENTER = 100.0
SIGMA = 1.0
TS = [f"t{i:03d}" for i in range(200)]
ALL_RULES = ["N1", "N2", "N3", "N5", "N6", "C1"]


def check(values, rules):
    return evaluate_rules(values, TS[:len(values)], CENTER, SIGMA, rules)


def hit_rules(values, rules):
    return {v["rule"] for v in check(values, rules)}


# ---------------------------------------------------------------------------
# P0：算法层与工具链路
# ---------------------------------------------------------------------------
def test_sigma_robust_to_outliers():
    baseline = [100 + (i % 11 - 5) * 0.7 for i in range(720)]
    center, sigma, meta = estimate_sigma(baseline, "mad")
    assert abs(center - 100) < 0.5
    assert 1.5 < sigma < 4.0
    assert meta["method"] == "mad"

    polluted = baseline + [118.0] * 20  # 约 2.7% 污染
    center2, sigma2, _ = estimate_sigma(polluted, "mad")
    assert abs(center2 - center) < 0.5
    assert abs(sigma2 - sigma) < 0.5, "离群点不应显著改变 sigma"


def test_sigma_degenerate_is_flagged():
    _, sigma, meta = estimate_sigma([100.0] * 100 + [1e6], "mad")
    assert meta["degenerate"] is True
    assert sigma < 1e-6, "常量基线 + 离群点不应回退到 std 撑大 sigma"


def test_build_limits():
    limits = build_limits(100.0, 2.0, 90.0, 110.0)
    assert limits["cl"] == 100.0
    assert limits["ucl_3"] == 106.0
    assert limits["lcl_1"] == 98.0
    assert limits["spec_max"] == 110.0


def test_stable_process_has_no_violation():
    values = [100 + (1 if i % 2 else -1) * 0.5 for i in range(60)]
    assert check(values, ALL_RULES) == []


def test_n1_single_point_beyond_3sigma():
    values = [100.0] * 20 + [110.0] + [100.0] * 20
    assert "N1" in hit_rules(values, ["N1"])
    assert check(values, ["N1"])[0]["max_z"] >= 10


def test_n2_nine_points_same_side():
    values = [101.5] * 12 + [100.0] * 10
    assert "N2" in hit_rules(values, ["N2"])


def test_n3_six_monotonic_points():
    values = [100 + i * 0.5 for i in range(10)]
    hits = check(values, ["N3"])
    assert hits and hits[0]["rule"] == "N3" and hits[0]["length"] >= 6


def test_n5_two_of_three_beyond_2sigma():
    values = [100.0] * 5 + [102.5, 102.5, 100.0] + [100.0] * 10
    assert "N5" in hit_rules(values, ["N5"])


def test_n6_four_of_five_beyond_1sigma():
    values = [100.0] * 5 + [101.5] * 4 + [100.0] * 10
    assert "N6" in hit_rules(values, ["N6"])


def test_c1_linear_points_beyond_1sigma():
    values = [100.0] * 5 + [101.5, 102.0, 102.5, 103.0] + [100.0] * 10
    assert "C1" in hit_rules(values, ["C1"])


def test_sliding_window_hits_are_merged():
    values = [103.5] * 20  # z=3.5，严格超出 ±3σ
    hits = check(values, ["N1"])
    assert len(hits) == 1, "连续越界点应合并成一段，不能逐点重复报"
    assert hits[0]["length"] == 20
    assert hits[0]["max_z"] >= 3.5


def test_tool_full_chain():
    result = asyncio.run(SpcTool().check_spc_rules(1, window="7d"))
    assert result.success is True
    data = result.data
    assert data["n"] == 168
    assert data["baseline"]["n"] >= 700
    assert data["baseline"]["limits_version"] != "未知"
    assert data["baseline"]["excluded"] >= 1
    assert data["verdict"] in ("失控", "需关注")
    assert data["violations"], "1 号机持续漂移应命中判异规则"
    assert data["cross_check"] is not None
    assert any("规格限" in c for c in data["caveats"])


def test_tool_unknown_device():
    result = asyncio.run(SpcTool().check_spc_rules(999))
    assert result.success is False


# ---------------------------------------------------------------------------
# P1：控制图 / C1 参数化 / 版本校验 / 同期对比
# ---------------------------------------------------------------------------
def test_c1_sigma_is_configurable():
    values = [100.0] * 5 + [101.5, 102.0, 102.5, 103.0] + [100.0] * 10
    ts = TS[:len(values)]
    assert evaluate_rules(values, ts, CENTER, SIGMA, ["C1"], c1_sigma=1.0)
    assert evaluate_rules(values, ts, CENTER, SIGMA, ["C1"], c1_sigma=2.0) == []


def test_explain_spc_rule():
    ok = asyncio.run(SpcTool().explain_spc_rule("C1"))
    assert ok.success is True
    assert ok.data["parameters"]["c1_sigma"] == 1.0
    assert "limitation" in ok.data
    assert asyncio.run(SpcTool().explain_spc_rule("XX")).success is False


def test_limits_version_hard_check():
    result = asyncio.run(SpcTool().check_spc_rules(1, expected_version="v2"))
    assert result.success is False
    assert "版本不匹配" in result.message


def test_limits_version_soft_warning():
    result = asyncio.run(SpcTool().check_spc_rules(3))
    assert result.success is True
    status = result.data["limits_version_status"]
    assert status["window_changed"] is True
    assert status["baseline_changed"] is True
    assert result.data["grade"] == "推测"


def test_peer_comparison():
    result = asyncio.run(SpcTool().check_spc_rules(1, compare_peers=True))
    assert result.success is True
    comparison = result.data["peer_comparison"]
    assert comparison is not None
    peers = {p["eid"]: p for p in comparison["peers"]}
    assert 3 in peers, "同产线同参数的 3 号机应作为对照"
    assert peers[3]["verdict"] == "受控"
    assert peers[3]["same_pattern"] is False
    assert comparison["note"]


def test_control_chart():
    result = asyncio.run(SpcTool().plot_control_chart(1))
    assert result.success is True
    chart = result.data["chart"]
    assert chart["kind"] == "line"
    styles = {s["style"] for s in chart["series"]}
    assert {"limit", "marker", "solid"} <= styles
    assert chart["meta"]["control_chart"] is True
    assert chart["meta"]["violation_points"] > 0
    assert any("ucl_3" in row for row in chart["data"])
    assert any(row["violation_value"] is not None for row in chart["data"])
    assert chart["ref_lines"]
