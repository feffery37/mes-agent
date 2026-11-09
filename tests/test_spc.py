#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : test_spc.py
@Desc    : SPC 判异单测：规则模式 + 稳健性 + P1/P2 工具链路。
           运行：uv run pytest tests/test_spc.py -q
"""
import asyncio

from app.domain.services.analysis.process_capability import compute_capability
from app.domain.services.analysis.spc import (
    build_limits,
    estimate_sigma,
    evaluate_rules,
)
from app.domain.services.analysis.spc_sop import match_sops
from app.domain.services.tools.spc import SpcTool
from core.config import get_app_config

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

    polluted = baseline + [118.0] * 20
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


# ---------------------------------------------------------------------------
# P2：过程能力 / 白名单 / SOP 联动
# ---------------------------------------------------------------------------
def test_capability_symmetric_process():
    cap = compute_capability([100.0] * 60, 100.0, 1.0, 94.0, 106.0)
    assert cap["available"] is True
    assert cap["cp"] == 2.0 and cap["cpk"] == 2.0
    assert cap["level"] == "充足" and cap["valid"] is True
    assert cap["grade"] == "数据支持"


def test_capability_shifted_mean():
    cap = compute_capability([103.0] * 60, 100.0, 1.0, 94.0, 106.0)
    assert cap["cp"] == 2.0
    assert cap["cpu"] == 1.0 and cap["cpk"] == 1.0
    assert cap["level"] == "勉强"


def test_capability_invalid_inputs():
    assert compute_capability([100.0] * 10, 100.0, 1.0, None, 106.0)["available"] is False
    assert compute_capability([100.0] * 10, 100.0, 0.0, 94.0, 106.0)["available"] is False


def test_capability_uncontrolled_is_not_valid():
    cap = compute_capability([100.0] * 60, 100.0, 1.0, 94.0, 106.0, controlled=False)
    assert cap["valid"] is False and cap["grade"] == "推测"
    assert any("放行" in c for c in cap["caveats"])
    cap2 = compute_capability([100.0] * 60, 100.0, 1.0, 94.0, 106.0, version_ok=False)
    assert cap2["valid"] is False
    assert any("LIMITS_VERSION" in c for c in cap2["caveats"])


def test_whitelist_exclusions():
    data = asyncio.run(SpcTool().check_spc_rules(1)).data
    assert len(data["exclusions"]) == 2
    assert {"传感器跳变", "停机"} == {e["reason"] for e in data["exclusions"]}
    assert data["effective_n"] == data["n"] - 2
    assert any("白名单" in c for c in data["caveats"])


def test_whitelist_toggle_changes_n1():
    tool = SpcTool()
    cfg = get_app_config().spc
    original = cfg.exclude_flagged_points
    try:
        cfg.exclude_flagged_points = True
        on = asyncio.run(tool.check_spc_rules(1)).data
        on_idx = {i for v in on["violations"] if v["rule"] == "N1" for i in v["indices"]}
        assert 50 not in on_idx, "豁免点不应参与判异"

        cfg.exclude_flagged_points = False
        off = asyncio.run(tool.check_spc_rules(1)).data
        off_idx = {i for v in off["violations"] if v["rule"] == "N1" for i in v["indices"]}
        assert 50 in off_idx, "关闭白名单后跳变点应被判为异常"
        assert off["exclusions"] == []
    finally:
        cfg.exclude_flagged_points = original


def test_sop_linking():
    data = asyncio.run(SpcTool().check_spc_rules(1)).data
    sops = data["related_sops"]
    assert sops, "命中规则应自动关联知识库 SOP"
    assert "SOP-EQ-0310" in {s["id"] for s in sops}
    assert any(s["matched_rules"] for s in sops)
    assert any("SOP" in c for c in data["caveats"])
    assert "SOP" in data["conclusion"]


def test_match_sops_pure():
    docs = [
        {"id": "A", "model": "M1", "spc_rules": ["N1", "N3"], "cases": 5},
        {"id": "B", "model": "M2", "spc_rules": ["N1"], "cases": 9},
        {"id": "C", "model": "", "exclude_reasons": ["停机"], "cases": 1},
    ]
    result = match_sops(docs, ["N1", "N3"], model="M1", reasons=["停机"], max_results=2)
    assert [d["id"] for d in result] == ["A", "C"]
    assert result[0]["matched_rules"] == ["N1", "N3"]
    assert result[1]["matched_reasons"] == ["停机"]
    assert match_sops(docs, [], model="M1") == []


def test_capability_tool():
    result = asyncio.run(SpcTool().compute_process_capability(1))
    assert result.success is True
    data = result.data
    assert data["capability"]["available"] is True
    assert "cpk" in data["capability"]
    assert data["capability"]["valid"] is False, "1 号机失控，Cpk 不应具备放行解释力"
    assert "不得用于质量放行" in data["conclusion"]
    assert data["effective_n"] == data["n"] - len(data["exclusions"])
