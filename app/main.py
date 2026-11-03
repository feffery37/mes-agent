#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : main.py
@Desc    : 应用入口（与课程 app/main.py 对应）。
           完成：加载配置 -> 初始化日志 -> CORS -> 注册异常处理器 -> 挂载路由 -> 生命周期启停。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.logging import setup_logging
from app.interfaces.endpoints.routes import router
from app.interfaces.errors.exception_handlers import register_exception_handlers
from app.interfaces.service_dependencies import get_agent_service
from core.config import get_settings

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("ims_agent")

openapi_tags = [
    {"name": "状态模块", "description": "服务运行健康监测。"},
    {"name": "对话模块", "description": "设备洞察 Agent 对话与 SSE 流式输出。"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("iMES 设备洞察 Agent 正在初始化")
    try:
        yield
    finally:
        logger.info("iMES 设备洞察 Agent 正在关闭")
        await get_agent_service().shutdown()
        logger.info("Agent 服务成功关闭")


app = FastAPI(
    title="iMES 设备洞察 Agent",
    description="面向制造业设备运维的对话式分析助手：查现状 / 看趋势 / 找原因 / 问对策。"
                "基于 DDD 分层 + ReAct + 可动态配置 LLM 的基础框架（参考 imooc-mas 课程架构）。",
    lifespan=lifespan,
    openapi_tags=openapi_tags,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """服务信息入口；前端 UI 由 Next.js（ui/，默认 http://localhost:3000）提供。"""
    return {
        "service": "ims_equipment_agent",
        "docs": "/docs",
        "chat_stream": "/api/chat/stream",
        "ui": "http://localhost:3000",
    }
