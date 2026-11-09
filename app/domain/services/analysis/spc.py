#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : spc.py
@Desc    : SPC 控制图判异纯函数（对应 Nelson / Western Electric 规则）。
           1) 用「受控基线期」稳健估计 center / sigma，不能用含漂移的当前窗口自估；
           2) 生成 ±1/2/3σ 控制限；
           3) 按可配置规则集检出非随机模式。

           注意：工艺规格限（control_min/control_max）与统计控制限（±3σ）是两回事，
           本模块只用基线数据估计 sigma，绝不拿规格限换算。
"""
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.domain.services.analysis.theil_sen import theil_sen_slope

RULE_TITLES = {
    "N1": "单点超出 ±3σ",
    "N2": "连续 9 点位于中心线同侧",
    "N3": "连续 6 点单调上升 / 下降",
    "N5": "连续 3 点中 2 点超出 ±2σ（同侧）",
    "N6": "连续 5 点中 4 点超出 ±1σ（同侧）",
    "C1": "连续多点超出 ±1σ 且呈线性分布",
}

RULE_SEVERITY = {
    "N1": "critical",
    "N2": "warning",
    "N3": "warning",
    "N5": "warning",
    "N6": "warning",
    "C1": "warning",
}


def estimate_sigma(
        values: Sequence[float],
        method: str = "mad",
) -> Tuple[float, float, Dict]:
    """从受控基线期估计 (center, sigma, 元信息)。

    mad: sigma = 1.4826 * median(|y - median(y)|)，抗离群点，与 Theil-Sen 思路一致；
    mr:  sigma = mean(|diff(y)|) / 1.128，I-MR 单值移动极差法。
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n_raw = int(arr.size)
    if n_raw < 2:
        return 0.0, 0.0, {"method": method, "n_raw": n_raw, "n_used": n_raw,
                          "degenerate": True, "reason": "基线样本不足"}

    center = float(np.median(arr))
    if method == "mr":
        sigma = float(np.mean(np.abs(np.diff(arr))) / 1.128)
    else:
        sigma = 1.4826 * float(np.median(np.abs(arr - center)))

    degenerate = not np.isfinite(sigma) or sigma <= 1e-9
    if degenerate:
        # 基线几乎无变异（常量序列 + 少量离群点）：不回退到 std，
        # 否则单个离群点就会把 sigma 撑大导致漏报；直接标记为不可用。
        sigma = 1e-9
    return (
        center,
        sigma,
        {
            "method": "mr" if method == "mr" else "mad",
            "n_raw": n_raw,
            "n_used": n_raw,
            "degenerate": degenerate,
            "reason": "基线离散度为 0，判异结果不可用" if degenerate else "",
        },
    )


def build_limits(
        center: float,
        sigma: float,
        spec_min: Optional[float] = None,
        spec_max: Optional[float] = None,
) -> Dict:
    """生成中心线、±1/2/3σ 控制限，并附带工艺规格限（仅用于对比展示）。"""
    limits = {"cl": round(center, 4), "sigma": round(sigma, 4)}
    for k in (1, 2, 3):
        limits[f"lcl_{k}"] = round(center - k * sigma, 4)
        limits[f"ucl_{k}"] = round(center + k * sigma, 4)
    limits["spec_min"] = spec_min
    limits["spec_max"] = spec_max
    return limits


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def _merge(hits: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """把重叠 / 相邻的命中区间合并，避免滑窗规则重复报同一段。"""
    if not hits:
        return []
    ordered = sorted(hits)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(int(s), int(e)) for s, e in merged]


def _violation(
        rule: str,
        start: int,
        end: int,
        ts: Sequence[str],
        z: Sequence[float],
        detail: str,
) -> Dict:
    indices = list(range(start, end + 1))
    return {
        "rule": rule,
        "title": RULE_TITLES[rule],
        "severity": RULE_SEVERITY[rule],
        "start": ts[start] if start < len(ts) else "",
        "end": ts[end] if end < len(ts) else "",
        "length": end - start + 1,
        "max_z": round(max((abs(z[i]) for i in indices), default=0.0), 2),
        "detail": detail,
        "indices": indices[:60],
        "indices_truncated": len(indices) > 60,
        "cross_check": None,
    }


def evaluate_rules(
        values: Sequence[float],
        timestamps: Sequence[str],
        center: float,
        sigma: float,
        rules: Sequence[str],
        c1_min_points: int = 3,
        c1_min_slope: float = 0.0,
) -> List[Dict]:
    """按规则集检出违规，返回已合并的命中清单。"""
    vals = [float(v) for v in values]
    n = len(vals)
    ts = list(timestamps)
    if n == 0 or sigma <= 0:
        return []
    z = [(v - center) / sigma for v in vals]
    selected = set(rules)
    hits: Dict[str, List[Tuple[int, int]]] = {r: [] for r in RULE_TITLES}

    # N1：单点超出 ±3σ
    if "N1" in selected:
        hits["N1"] = [(i, i) for i in range(n) if abs(z[i]) > 3]

    # N2：连续 9 点位于中心线同侧（z=0 中断游程）
    if "N2" in selected:
        run = 0
        for i in range(1, n + 1):
            broken = i == n or _sign(z[i]) == 0 or _sign(z[i]) != _sign(z[run])
            if broken:
                if i - run >= 9:
                    hits["N2"].append((run, i - 1))
                run = i

    # N3：连续 6 点严格单调（对应 5 个同号差分）
    if "N3" in selected and n >= 6:
        diffs = [vals[i + 1] - vals[i] for i in range(n - 1)]
        run = 0
        for i in range(1, len(diffs) + 1):
            broken = i == len(diffs) or _sign(diffs[i]) == 0 or _sign(diffs[i]) != _sign(diffs[run])
            if broken:
                if i - run >= 5:
                    hits["N3"].append((run, i))
                run = i

    # N5 / N6：滑窗计数（同侧超阈值）
    for rule, k, m, threshold in (("N5", 3, 2, 2.0), ("N6", 5, 4, 1.0)):
        if rule not in selected or n < k:
            continue
        for s in range(n - k + 1):
            window = z[s:s + k]
            pos = sum(1 for x in window if x > threshold)
            neg = sum(1 for x in window if x < -threshold)
            if pos >= m or neg >= m:
                hits[rule].append((s, s + k - 1))

    # C1 自定义：连续 ≥c1_min_points 点全在 ±1σ 外同侧，且呈线性（Theil-Sen 斜率同向）
    if "C1" in selected:
        side = [1 if zi > 1 else (-1 if zi < -1 else 0) for zi in z]
        run = 0
        for i in range(1, n + 1):
            broken = i == n or side[i] == 0 or side[i] != side[run]
            if broken:
                if side[run] != 0 and i - run >= max(c1_min_points, 2):
                    seg = np.asarray(vals[run:i], dtype=float)
                    slope = theil_sen_slope(seg)
                    if slope * side[run] > 0 and abs(slope) >= c1_min_slope:
                        hits["C1"].append((run, i - 1))
                run = i

    # 游程类规则（N2/N3/C1）的 hits 已是极大连续段，不能再按「相邻」合并，
    # 否则中间一个反向点会被吞掉，误报成「全程单调 / 全程同侧」。
    merged: Dict[str, List[Tuple[int, int]]] = {
        rule: (hits[rule] if rule in ("N2", "N3", "C1") else _merge(hits[rule]))
        for rule in RULE_TITLES
    }

    results: List[Dict] = []
    for rule in RULE_TITLES:
        for start, end in merged[rule]:
            if rule == "N1":
                detail = f"共 {end - start + 1} 个点超出 ±3σ（最大 |z|={max(abs(z[i]) for i in range(start, end + 1)):.2f}）"
            elif rule == "N2":
                side = "上侧" if z[start] > 0 else "下侧"
                detail = f"连续 {end - start + 1} 个点位于中心线{side}"
            elif rule == "N3":
                direction = "上升" if vals[end] > vals[start] else "下降"
                detail = f"连续 {end - start + 1} 个点单调{direction}"
            elif rule in ("N5", "N6"):
                detail = f"窗口内多点超出 ±{'2' if rule == 'N5' else '1'}σ（同侧）"
            else:
                detail = f"连续 {end - start + 1} 个点超出 ±1σ 且呈线性分布"
            results.append(_violation(rule, start, end, ts, z, detail))
    return results
