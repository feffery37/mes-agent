#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : notification.py
@Desc    : 对外通知的领域模型，与具体渠道（企业微信 / 飞书）解耦。
"""
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field


class NotifyLevel(str, Enum):
    """通知级别。"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Notification(BaseModel):
    """一条待推送消息。

    内容只能由工具返回的定量数据渲染，不允许模型自由编造数值。
    """

    title: str
    body: str
    level: NotifyLevel = NotifyLevel.WARNING
    channels: List[str] = Field(default_factory=list)
    dedup_key: str = ""
    source: str = ""
    links: List[Dict[str, str]] = Field(default_factory=list)


class NotifyResult(BaseModel):
    """单个渠道的投递结果。"""

    success: bool
    channel: str
    message: str = ""
