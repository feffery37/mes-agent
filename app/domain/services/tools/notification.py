#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : notification.py
@Desc    : 对外通知工具（人在回路）。
           模型只能生成待确认草稿；真正的发送入口是 /api/notify/confirm，不是 @tool。
"""
import logging
from typing import List, Optional

from app.application.services.notification_service import get_notification_service
from app.domain.models.notification import Notification, NotifyLevel
from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool

logger = logging.getLogger(__name__)


class NotificationTool(BaseTool):
    """通知草稿工具集。"""
    name = "notification"

    @tool(
        name="draft_notification",
        description="生成一张「待人工确认」的对外通知草稿，不会发送消息。"
                    "返回 confirm_token 与草稿内容；只有用户在确认卡片上点击「发送通知」后系统才会真正推送。"
                    "仅在用户明确要求通知 / 推送 / 发到群 / 告诉班组时调用，不得主动推送。",
        parameters={
            "title": {"type": "string", "description": "通知标题"},
            "body": {"type": "string", "description": "通知正文；其中数值必须来自本轮工具返回，不得编造"},
            "level": {"type": "string", "description": "级别 info/warning/critical，默认 warning"},
            "channels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "目标渠道，留空用默认渠道",
            },
        },
        required=["title", "body"],
    )
    async def draft_notification(
            self,
            title: str,
            body: str,
            level: str = "warning",
            channels: Optional[List[str]] = None,
    ) -> ToolResult:
        service = get_notification_service()
        if not service.enabled:
            return ToolResult.fail("通知功能已关闭（notify.enabled=false）")

        try:
            notify_level = NotifyLevel(level)
        except ValueError:
            notify_level = NotifyLevel.WARNING

        notification = Notification(
            title=title,
            body=body,
            level=notify_level,
            channels=channels or service.default_channels,
            source="agent_draft",
        )
        token, expires = service.create_draft(notification)
        return ToolResult.ok(
            data={
                "status": "pending_confirmation",
                "kind": "notification",
                "confirm_token": token,
                "draft": {
                    "title": notification.title,
                    "body": notification.body,
                    "level": notification.level.value,
                    "channels": notification.channels,
                },
                "expires_in_seconds": expires,
                "hint": "尚未发送，需用户在确认卡片上点击「发送通知」",
            },
            message="已生成待确认通知草稿，等待用户确认（当前未发送）",
        )
