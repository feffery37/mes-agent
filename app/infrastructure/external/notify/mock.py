#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : mock.py
@Desc    : 本地日志渠道：只记录日志，不对外发送。
           未配置 webhook 环境变量时自动降级到这里，保证开箱即用且不会误发。
"""
import logging

from app.domain.models.notification import Notification, NotifyResult

logger = logging.getLogger(__name__)


class MockNotifier:
    """演示 / 降级用通知渠道。"""

    def __init__(self, channel: str = "mock") -> None:
        self._channel = channel

    @property
    def channel(self) -> str:
        return self._channel

    async def send(self, notification: Notification) -> NotifyResult:
        logger.info(
            "[Notify:%s][日志模式，未对外发送] %s\n%s",
            self.channel,
            notification.title,
            notification.body,
        )
        return NotifyResult(
            success=True,
            channel=self.channel,
            message="日志模式，未对外发送",
        )
