#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : workorder_routes.py
@Desc    : 工单人工确认接口（人在回路）。
           只有用户在前端确认卡片上主动点击，才会执行写操作；LLM 无法调用本接口。
"""
import logging

from fastapi import APIRouter

from app.domain.services.tools.workorder import WorkOrderTool
from app.interfaces.schemas.workorder import WorkOrderConfirmRequest, WorkOrderConfirmResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workorder", tags=["工单确认（人在回路）"])


@router.post("/confirm", response_model=WorkOrderConfirmResponse)
async def confirm_workorder(req: WorkOrderConfirmRequest):
    """人工确认 / 取消待建工单，返回创建结果。"""
    result = WorkOrderTool().confirm_workorder(req.confirm_token, req.action)
    return WorkOrderConfirmResponse(
        success=result.success,
        message=result.message or "",
        data=result.data,
    )
