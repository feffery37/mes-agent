#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : theil_sen.py
@Desc    : Theil-Sen 稳健趋势估计 + Bootstrap 百分位置信区间。
           对应《iMES 设备洞察 Agent 技术方案》第5章：在脏数据环境下稳健判断趋势。
           崩溃点 29.3%（OLS 为 0%），无需分布假设。
"""
import numpy as np
from numpy.random import default_rng


def theil_sen_slope(y: np.ndarray, x: np.ndarray | None = None) -> float:
    """计算 Theil-Sen 中位数斜率。

    Args:
        y: 观测序列（如温度）。
        x: 自变量（默认 0..n-1）。
    Returns:
        斜率（单位/观测步）。
    """
    y = np.asarray(y, dtype=float)
    n = y.shape[0]
    if x is None:
        x = np.arange(n, dtype=float)
    x = np.asarray(x, dtype=float)

    # 所有两两斜率的中位数
    slopes = []
    for i in range(n - 1):
        dx = x[i + 1:] - x[i]
        dy = y[i + 1:] - y[i]
        with np.errstate(divide="ignore", invalid="ignore"):
            s = dy / dx
        s = s[np.isfinite(s)]
        slopes.extend(s.tolist())
    if not slopes:
        return 0.0
    return float(np.median(slopes))


def bootstrap_ci(
        y: np.ndarray,
        n_bootstrap: int = 1000,
        confidence: float = 0.95,
        seed: int = 42,
        x: np.ndarray | None = None,
) -> tuple[float, float]:
    """Bootstrap 百分位置信区间（成对重采样 (x, y)）。

    方案 2.3 关键约束：必须成对抽取 (x, y)，保持自变量与观测值的配对关系。
    若只抽 y 而把 x 重置为 0..n-1，等于打乱时间顺序，斜率分布会被压向 0，
    区间系统性失真（表现为点估计显著、CI 却跨 0）。
    """
    y = np.asarray(y, dtype=float)
    n = y.shape[0]
    if x is None:
        x = np.arange(n, dtype=float)
    x = np.asarray(x, dtype=float)
    rng = default_rng(seed)

    estimates = np.empty(n_bootstrap, dtype=float)
    valid = 0
    idx = np.arange(n)
    for _ in range(n_bootstrap):
        bi = rng.choice(idx, size=n, replace=True)
        xs, ys = x[bi], y[bi]
        if np.unique(xs).size < 2:  # 退化重采样：x 全相同，斜率无定义
            continue
        order = np.argsort(xs, kind="stable")
        estimates[valid] = theil_sen_slope(ys[order], xs[order])
        valid += 1
    if valid == 0:
        return 0.0, 0.0
    estimates = estimates[:valid]
    alpha = (1.0 - confidence) / 2.0
    low = float(np.quantile(estimates, alpha))
    high = float(np.quantile(estimates, 1.0 - alpha))
    return low, high


def analyze_trend(
        values: list[float],
        confidence: float = 0.95,
        n_bootstrap: int = 1000,
        x: list[float] | None = None,
) -> dict:
    """对序列做稳健趋势分析，返回斜率、截距、置信区间与趋势结论。

    Args:
        x: 可选自变量（时间戳 / 批次序号），默认等距 0..n-1。
    Returns:
        {
          "slope": float, "intercept": float,
          "ci_low": float, "ci_high": float,
          "significant": bool,   # 置信区间是否不跨 0
          "direction": str,      # up | down | flat（不显著一律 flat）
          "conclusion": str,     # 显著上升 | 显著下降 | 趋势不显著 | 样本不足
          "latest": float, "points": int,
        }
    """
    arr = np.asarray(values, dtype=float)
    if x is None:
        xs = np.arange(arr.shape[0], dtype=float)
    else:
        xs = np.asarray(x, dtype=float)

    # 前置清洗：剔除空值 / 非有限值（方案 3.1 S2）
    mask = np.isfinite(arr) & np.isfinite(xs)
    arr, xs = arr[mask], xs[mask]

    if arr.size < 2:
        return {
            "slope": 0.0, "intercept": 0.0,
            "ci_low": 0.0, "ci_high": 0.0,
            "significant": False, "direction": "flat", "conclusion": "样本不足",
            "latest": 0.0, "points": int(arr.size),
        }

    slope = theil_sen_slope(arr, xs)
    intercept = float(np.median(arr - slope * xs))
    low, high = bootstrap_ci(arr, x=xs, n_bootstrap=n_bootstrap, confidence=confidence)
    significant = not (low <= 0 <= high)
    if not significant:
        direction, conclusion = "flat", "趋势不显著"
    elif slope > 0:
        direction, conclusion = "up", "显著上升"
    else:
        direction, conclusion = "down", "显著下降"
    return {
        "slope": round(float(slope), 4),
        "intercept": round(intercept, 2),
        "ci_low": round(low, 4),
        "ci_high": round(high, 4),
        "significant": significant,
        "direction": direction,
        "conclusion": conclusion,
        "latest": round(float(arr[-1]), 2),
        "points": int(arr.size),
    }
