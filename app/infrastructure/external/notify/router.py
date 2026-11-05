#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : router.py
@Desc    : 多渠道分发。单渠道异常不影响其它渠道，也不向上抛出。
"""
from typing import Dict, List

from app.domain.external.notifier import INotifier
from app.domain.models.notification import Notification, NotifyResult


class ChannelRouter:
    """按 Notification.channels 分发到已注册的渠道。"""

    def __init__(self, notifiers: Dict[str, INotifier]) -> None:
        self._notifiers = notifiers

    @property
    def channels(self) -> List[str]:
        return list(self._notifiers)

    async def send(self, notification: Notification) -> List[NotifyResult]:
        targets = notification.channels or list(self._notifiers)
        if not targets:
            return [NotifyResult(success=False, channel="-", message="无可用通知渠道")]

        results: List[NotifyResult] = []
        for name in targets:
            notifier = self._notifiers.get(name)
            if notifier is None:
                results.append(
                    NotifyResult(success=False, channel=name, message="渠道未启用")
                )
                continue
            try:
                results.append(await notifier.send(notification))
            except Exception as e:
                results.append(
                    NotifyResult(success=False, channel=name, message=type(e).__name__)
                )
        return results
