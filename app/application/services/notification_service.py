#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : notification_service.py
@Desc    : 通知编排服务（人在回路）。
           模型只能生成「待确认草稿」，真正的对外发送由用户点击后调用 confirm() 执行。
           没有事件旁路、阈值规则或静默窗口：发不发完全由人决定。
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from app.domain.models.notification import Notification, NotifyResult
from app.domain.models.tool_result import ToolResult
from app.infrastructure.external.notify.mock import MockNotifier
from app.infrastructure.external.notify.router import ChannelRouter
from app.infrastructure.external.notify.wecom import WecomNotifier
from core.config import NotifyConfig, get_app_config

logger = logging.getLogger(__name__)


class NotificationService:
    """草稿管理 + 人工确认后的投递。"""

    def __init__(self, config: NotifyConfig, router: Optional[ChannelRouter] = None) -> None:
        self._config = config
        self._router = router or self._build_router(config)
        self._pending: Dict[str, Dict] = {}
        self._ttl = timedelta(minutes=10)

    @staticmethod
    def _build_router(config: NotifyConfig) -> ChannelRouter:
        """按配置注册渠道；缺少 webhook 时降级为只打日志的 Mock 渠道。"""
        notifiers = {}
        for name, channel_config in config.channels.items():
            if not channel_config.enabled:
                continue
            env_name = channel_config.webhook_env
            webhook_url = os.getenv(env_name, "") if env_name else ""
            if name == "wecom" and webhook_url:
                notifiers[name] = WecomNotifier(webhook_url, timeout=config.timeout_seconds)
                mode = "真实 webhook"
            else:
                notifiers[name] = MockNotifier(name)
                mode = "日志模式（未配置 webhook，或尚未实现的渠道）"
            logger.info("[Notify] 渠道 %s 已注册：%s", name, mode)
        return ChannelRouter(notifiers)

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def default_channels(self) -> list[str]:
        return self._config.default_channels or list(self._router.channels)

    def _purge_expired(self) -> None:
        now = datetime.now()
        for token in [t for t, p in self._pending.items() if now - p["created_at"] > self._ttl]:
            self._pending.pop(token, None)

    def list_pending(self) -> list[dict]:
        """只读：列出待人工确认的通知草稿，供收件箱聚合（不是 @tool，LLM 不可见）。"""
        self._purge_expired()
        now = datetime.now()
        ttl_seconds = int(self._ttl.total_seconds())
        items = []
        for token, pending in self._pending.items():
            notification: Notification = pending["notification"]
            channels = "、".join(notification.channels) or "默认渠道"
            items.append({
                "confirm_token": token,
                "kind": "notification",
                "title": notification.title,
                "summary": f"{notification.level.value} · {channels}",
                "draft": notification.model_dump(mode="json"),
                "created_at": pending["created_at"].isoformat(timespec="seconds"),
                "expires_in_seconds": ttl_seconds,
                "remaining_seconds": max(
                    0, int((self._ttl - (now - pending["created_at"])).total_seconds())
                ),
            })
        return items

    def create_draft(self, notification: Notification) -> Tuple[str, int]:
        """登记一张待人工确认的草稿，返回 (confirm_token, 有效秒数)。"""
        self._purge_expired()
        token = f"ntf-{uuid.uuid4().hex[:12]}"
        self._pending[token] = {"notification": notification, "created_at": datetime.now()}
        logger.info("[Notify] 生成待确认草稿 token=%s title=%s", token, notification.title)
        return token, int(self._ttl.total_seconds())

    async def confirm(self, confirm_token: str, action: str = "send") -> ToolResult:
        """人工确认入口：仅由 /api/notify/confirm 调用，不暴露给 LLM。"""
        self._purge_expired()
        pending = self._pending.get(confirm_token)
        if not pending:
            return ToolResult.fail("确认令牌无效或已过期，请重新生成通知草稿")
        self._pending.pop(confirm_token, None)

        if action == "cancel":
            logger.info("[Notify] 用户忽略通知草稿 token=%s", confirm_token)
            return ToolResult.ok(
                data={"status": "cancelled", "confirm_token": confirm_token},
                message="已忽略，未发送任何通知",
            )

        notification: Notification = pending["notification"]
        results = await self._send(notification)
        payload = {
            "status": "sent",
            "channels": [r.channel for r in results],
            "results": [r.model_dump() for r in results],
        }
        if results and all(r.success for r in results):
            logger.info(
                "[Notify] 用户确认发送成功 token=%s channels=%s",
                confirm_token,
                payload["channels"],
            )
            return ToolResult.ok(data=payload, message="通知已发送")
        logger.warning("[Notify] 发送未完全成功 token=%s detail=%s", confirm_token, payload["results"])
        return ToolResult.fail("通知发送失败，请查看服务日志")

    async def _send(self, notification: Notification) -> list[NotifyResult]:
        """带重试的投递；失败只记录，不向上抛。"""
        last: list[NotifyResult] = []
        for attempt in range(self._config.retry + 1):
            try:
                last = await self._router.send(notification)
                if last and all(r.success for r in last):
                    return last
            except Exception:
                logger.exception("[Notify] 投递异常（不影响对话）")
            if attempt < self._config.retry:
                await asyncio.sleep(0.5 * (2 ** attempt))
        return last


_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """通知服务单例：待确认草稿需要跨 HTTP 请求共享。"""
    global _service
    if _service is None:
        _service = NotificationService(get_app_config().notify)
    return _service
