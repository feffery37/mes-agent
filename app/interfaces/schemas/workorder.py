#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : workorder.py
@Desc    : 工单确认接口的请求 / 响应模型（人在回路）。
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class WorkOrderConfirmRequest(BaseModel):
    """用户点击确认 / 取消时提交。"""

    confirm_token: str = Field(..., description="由 create_workorder 返回的待确认令牌")
    action: Literal["confirm", "cancel"] = "confirm"


class WorkOrderConfirmResponse(BaseModel):
    """确认结果。"""

    success: bool
    message: str = ""
    data: Optional[dict] = None
