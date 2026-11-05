#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : notify_routes.py
@Desc    : 通知人工确认接口（人在回路）。
           只有用户在前端确认卡片上点击发送，才真正对外推送；本接口不注册为 @tool，LLM 无法调用。
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.application.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notify", tags=["通知确认（人在回路）"])


class NotifyConfirmRequest(BaseModel):
    """用户点击发送 / 忽略时提交。"""

    confirm_token: str = Field(..., description="由 draft_notification 返回的待确认令牌")
    action: Literal["send", "cancel"] = "send"


class NotifyConfirmResponse(BaseModel):
    """确认结果。"""

    success: bool
    message: str = ""
    data: Optional[dict] = None


@router.post("/confirm", response_model=NotifyConfirmResponse)
async def confirm_notification(req: NotifyConfirmRequest):
    """人工确认 / 忽略通知草稿，确认后才执行对外发送。"""
    result = await get_notification_service().confirm(req.confirm_token, req.action)
    return NotifyConfirmResponse(
        success=result.success,
        message=result.message or "",
        data=result.data,
    )
