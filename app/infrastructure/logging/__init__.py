#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : __init__.py
@Desc    : 日志模块。
           提供统一的 setup_logging，供 main 生命周期与运行期使用。
"""
import logging
import sys

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志：统一格式、输出到 stdout，避免重复添加 handler。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 第三方 HTTP 客户端会以 INFO 打印完整请求 URL；通知 webhook 的 URL 含 key，
    # 统一降噪到 WARNING，避免密钥写进日志（LLM 网关日志用的 httpx2 不受影响）。
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)

    _CONFIGURED = True
