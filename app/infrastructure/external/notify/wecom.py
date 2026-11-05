#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : wecom.py
@Desc    : 企业微信群机器人 webhook 渠道。
           Webhook URL 只在实例内部使用：不写日志、不进异常文本，避免 key 泄露。
"""
from typing import Optional

import httpx

from app.domain.models.notification import Notification, NotifyLevel, NotifyResult

_LEVEL_PREFIX = {
    NotifyLevel.CRITICAL: '<font color="warning">【高风险】</font> ',
    NotifyLevel.WARNING: "【提醒】",
    NotifyLevel.INFO: "",
}


class WecomNotifier:
    """企业微信群机器人渠道（markdown 消息）。"""

    def __init__(
            self,
            webhook_url: str,
            timeout: float = 5.0,
            client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._timeout = timeout
        self._client = client  # 可注入，便于用 httpx.MockTransport 单测

    @property
    def channel(self) -> str:
        return "wecom"

    @staticmethod
    def build_payload(notification: Notification) -> dict:
        """把统一消息模型转成企业微信 markdown 格式。"""
        prefix = _LEVEL_PREFIX.get(notification.level, "")
        content = f"### {prefix}{notification.title}\n\n{notification.body}"
        if notification.links:
            content += "\n\n" + "  ".join(
                f"[{link.get('text', '查看详情')}]({link.get('url', '')})"
                for link in notification.links
            )
        return {"msgtype": "markdown", "markdown": {"content": content}}

    async def send(self, notification: Notification) -> NotifyResult:
        payload = self.build_payload(notification)
        try:
            if self._client is not None:
                resp = await self._client.post(
                    self._webhook_url, json=payload, timeout=self._timeout
                )
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(self._webhook_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errcode") != 0:
                return NotifyResult(
                    success=False,
                    channel=self.channel,
                    message=f"errcode={data.get('errcode')}, errmsg={data.get('errmsg')}",
                )
            return NotifyResult(success=True, channel=self.channel)
        except Exception as e:
            # 不输出异常明细：httpx 的异常文本可能包含带 key 的 webhook URL
            return NotifyResult(
                success=False,
                channel=self.channel,
                message=f"{type(e).__name__}（明细已脱敏）",
            )
