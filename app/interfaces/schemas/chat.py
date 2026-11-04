#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : chat.py
@Desc    : 对话接口的请求/响应 Schema。
"""
from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """对话请求。"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """对话创建响应（返回会话ID，用于后续流式拉取）。"""
    session_id: str
    status: str = "submitted"
