#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : exception_handlers.py
@Desc    : 统一异常处理器。
           把领域/应用异常转换为标准化 JSON 响应，解决跨域统一响应问题。
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.errors.exceptions import AgentNotFoundError, ServerRequestsError

logger = logging.getLogger(__name__)


async def _server_requests_handler(request: Request, exc: ServerRequestsError):
    return JSONResponse(status_code=502, content={"error": exc.message})


async def _agent_not_found_handler(request: Request, exc: AgentNotFoundError):
    return JSONResponse(status_code=404, content={"error": exc.detail})


async def _unhandled_handler(request: Request, exc: Exception):
    logger.exception(f"未处理异常: {str(exc)}")
    return JSONResponse(status_code=500, content={"error": "内部服务错误"})


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""
    app.add_exception_handler(ServerRequestsError, _server_requests_handler)
    app.add_exception_handler(AgentNotFoundError, _agent_not_found_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
