#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : status_routes.py
@Desc    : 状态监测接口（与课程 interfaces/endpoints/status_routes.py 对应）。
"""
import time

from fastapi import APIRouter

from core.config import get_app_config, get_settings

router = APIRouter(prefix="/status", tags=["状态模块"])

_START_TIME = time.time()


@router.get("")
async def status():
    """返回服务运行状态与关键配置。"""
    settings = get_settings()
    app_config = get_app_config()
    return {
        "service": "ims_equipment_agent",
        "env": settings.env,
        "llm_provider": app_config.llm.provider,
        "llm_model": app_config.llm.model_name,
        "agent_max_iterations": app_config.agent.max_iterations,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "status": "ok",
    }
