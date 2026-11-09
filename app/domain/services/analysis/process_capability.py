#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : process_capability.py
@Desc    : 过程能力指数 Cp / Cpk 纯函数。

           前提条件（否则数值没有解释力，不得用于放行）：
           1) 过程受控（SPC 判异未失控）；
           2) LIMITS_VERSION 未变更（规格 / 复测口径一致）；
           3) sigma 来自受控基线期、规格限来自设备主数据。
           硬纪律第 8 条：Cpk 变差时先查 LIMITS_VERSION 是否变更。
"""
from typing import Dict, Optional, Sequence

import numpy as np


def compute_capability(
        values: Sequence[float],
        baseline_center: float,
        sigma: float,
        spec_min: Optional[float],
        spec_max: Optional[float],
        controlled: bool = True,
        version_ok: bool = True,
        min_cpk: float = 1.33,
        warn_cpk: float = 1.0,
) -> Dict:
    """计算 Cp / Cpk 并给出可用性与结论分级。

    mu 用当前窗口（已排除白名单点）的过程均值，sigma 用受控基线期的稳健估计，
    这样均值漂移会如实反映为 Cpk 下降，而不会被漂移数据把 sigma 撑大掩盖。
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    base: Dict = {
        "available": False,
        "n": int(arr.size),
        "baseline_center": round(float(baseline_center), 4),
        "sigma": round(float(sigma), 4),
        "spec_min": spec_min,
        "spec_max": spec_max,
        "controlled": controlled,
        "version_ok": version_ok,
        "caveats": [],
    }
    if arr.size < 2:
        base["reason"] = "有效样本不足"
        return base
    if spec_min is None or spec_max is None or spec_max <= spec_min:
        base["reason"] = "工艺规格限缺失或不合法，无法计算 Cpk"
        return base
    if sigma <= 0:
        base["reason"] = "sigma 不可用（基线离散度为 0）"
        return base

    mu = float(np.mean(arr))
    cp = (spec_max - spec_min) / (6.0 * sigma)
    cpu = (spec_max - mu) / (3.0 * sigma)
    cpl = (mu - spec_min) / (3.0 * sigma)
    cpk = min(cpu, cpl)
    level = "充足" if cpk >= min_cpk else ("勉强" if cpk >= warn_cpk else "不足")
    valid = bool(controlled and version_ok)
    caveats = [
        "Cp / Cpk 假设过程近似正态且受控；本框架用稳健 MAD 估计 sigma，与经典口径略有差异",
        "工艺规格限用于判合格，统计控制限 ±3σ 用于判受控，两者不可混用",
    ]
    if not controlled:
        caveats.append("SPC 判异为失控 / 需关注，Cpk 数值仅供参考，不得用于质量放行")
    if not version_ok:
        caveats.append("LIMITS_VERSION 发生变更或校验未通过，Cpk 需人工复核后再判读")

    return {
        **base,
        "available": True,
        "mean": round(mu, 4),
        "cp": round(cp, 4),
        "cpu": round(cpu, 4),
        "cpl": round(cpl, 4),
        "cpk": round(cpk, 4),
        "level": level,
        "valid": valid,
        "grade": "数据支持" if valid else "推测",
        "caveats": caveats,
    }
