#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : inbox_routes.py
@Desc    : 待确认收件箱（只读聚合）。
           把分散在「工单」「通知」两处的待人工确认草稿汇总成一个列表，
           使刷新页面 / 切换会话后仍能从侧栏找回草稿。
           本接口只读、不注册为 @tool，LLM 无法调用；确认动作仍由用户点击后走各自的 confirm 接口。
"""
from typing import List, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.application.services.notification_service import get_notification_service
from app.domain.services.tools.workorder import list_workorder_pending

router = APIRouter(prefix="/inbox", tags=["待确认收件箱（只读）"])


class PendingItem(BaseModel):
    """一条待人工确认草稿。"""

    confirm_token: str = Field(..., description="确认令牌；确认接口仍需用户主动点击")
    kind: Literal["workorder", "notification"]
    title: str
    summary: str
    draft: dict
    created_at: str
    expires_in_seconds: int
    remaining_seconds: int


class PendingInboxResponse(BaseModel):
    """收件箱列表。"""

    items: List[PendingItem] = Field(default_factory=list)
    total: int = 0


@router.get("/pending", response_model=PendingInboxResponse)
async def list_pending_items():
    """汇总两类待确认草稿，按生成时间倒序；过期项由各自模块在读取时清理。"""
    items = list_workorder_pending() + get_notification_service().list_pending()
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return PendingInboxResponse(
        items=[PendingItem(**item) for item in items],
        total=len(items),
    )
