#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : exceptions.py
@Desc    : 应用层统一异常。
           用于接口层统一捕获并返回标准化错误响应。
"""
from fastapi import HTTPException, status


class ServerRequestsError(Exception):
    """外部服务（如 LLM）请求异常。"""

    def __init__(self, message: str = "服务请求失败") -> None:
        self.message = message
        super().__init__(message)


class AgentNotFoundError(HTTPException):
    """会话/Agent 未找到。"""

    def __init__(self, detail: str = "会话不存在") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
