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
) -> tuple[float, float]:
    """Bootstrap 百分位置信区间（基于 Theil-Sen 斜率重采样）。"""
    y = np.asarray(y, dtype=float)
    rng = default_rng(seed)
    n = y.shape[0]
    estimates = np.empty(n_bootstrap, dtype=float)
    idx = np.arange(n)
    for b in range(n_bootstrap):
        sample = y[rng.choice(idx, size=n, replace=True)]
        estimates[b] = theil_sen_slope(sample)
    alpha = (1.0 - confidence) / 2.0
    low = float(np.quantile(estimates, alpha))
    high = float(np.quantile(estimates, 1.0 - alpha))
    return low, high


def analyze_trend(
        values: list[float],
        confidence: float = 0.95,
        n_bootstrap: int = 1000,
) -> dict:
    """对序列做稳健趋势分析，返回斜率、置信区间、是否显著。

    Returns:
        {
          "slope": float,
          "ci_low": float,
          "ci_high": float,
          "significant": bool,   # 置信区间是否不跨 0
          "direction": str,      # "up" | "down" | "flat"
          "latest": float,
        }
    """
    arr = np.asarray(values, dtype=float)
    slope = theil_sen_slope(arr)
    low, high = bootstrap_ci(arr, n_bootstrap=n_bootstrap, confidence=confidence)
    significant = not (low <= 0 <= high)
    if abs(slope) < 1e-9:
        direction = "flat"
    elif slope > 0:
        direction = "up"
    else:
        direction = "down"
    return {
        "slope": round(slope, 4),
        "ci_low": round(low, 4),
        "ci_high": round(high, 4),
        "significant": significant,
        "direction": direction,
        "latest": round(float(arr[-1]), 2),
    }
