#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : routes.py
@Desc    : 路由聚合（与课程 interfaces/endpoints/routes.py 对应）。
"""
from fastapi import APIRouter

from app.interfaces.endpoints import chat_routes, status_routes

router = APIRouter()
router.include_router(status_routes.router)
router.include_router(chat_routes.router)
