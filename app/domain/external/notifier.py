#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : notifier.py
@Desc    : 对外通知渠道协议（与 LLM 协议同层，便于替换实现）。
"""
from typing import Protocol

from app.domain.models.notification import Notification, NotifyResult


class INotifier(Protocol):
    """通知渠道接口协议。"""

    @property
    def channel(self) -> str:
        """渠道名，如 wecom / feishu / mock。"""
        ...

    async def send(self, notification: Notification) -> NotifyResult:
        """投递一条通知，实现方需自行保证不向上抛异常。"""
        ...
