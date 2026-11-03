#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : chat_routes.py
@Desc    : 对话接口（与课程 interfaces/endpoints/session_routes.py 对应）。
           提供：提交消息、SSE 流式拉取、以及便捷的「提交即流式」端点。
"""
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.application.services.agent_service import get_agent_service
from app.interfaces.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["对话模块"])


@router.post("", response_model=ChatResponse)
async def create_chat(req: ChatRequest, request: Request):
    """创建/复用会话并提交消息（后台运行），返回 session_id。"""
    service = get_agent_service()
    session_id = req.session_id or service.create_session()
    # 若客户端传入了未知 session_id，则新建
    try:
        service.get_session(session_id)
    except Exception:
        session_id = service.create_session()
    await service.submit(session_id, req.message)
    return ChatResponse(session_id=session_id)


@router.get("/stream/{session_id}")
async def stream_chat(session_id: str):
    """SSE 流式拉取某个会话的事件流（直到 DoneEvent）。"""
    service = get_agent_service()

    async def event_gen():
        async for event in service.stream(session_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/stream")
async def stream_chat_direct(req: ChatRequest):
    """便捷端点：提交消息并直接以 SSE 流式返回结果。"""
    service = get_agent_service()
    session_id = req.session_id or service.create_session()
    try:
        service.get_session(session_id)
    except Exception:
        session_id = service.create_session()
    await service.submit(session_id, req.message)

    async def event_gen():
        async for event in service.stream(session_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
