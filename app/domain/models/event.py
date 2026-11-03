#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : event.py
@Desc    : 事件模型（与课程 domain/models/event.py 对应）。
           Agent 执行过程以「事件流」形式向接口层/前端推送，实现流式响应。
           这里保留基础框架所需的核心事件类型。
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Literal, List, Optional, Any, Dict, Union, Annotated

from pydantic import BaseModel, Field

from .tool_result import ToolResult


class ToolEventStatus(str, Enum):
    """工具事件状态。"""
    CALLING = "calling"   # 调用中
    CALLED = "called"     # 调用完毕


class BaseEvent(BaseModel):
    """基础事件类型。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal[""] = ""
    created_at: datetime = Field(default_factory=datetime.now)


class MessageEvent(BaseEvent):
    """消息事件（用户/AI 文本）。"""
    type: Literal["message"] = "message"
    role: Literal["user", "assistant"] = "assistant"
    message: str = ""
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class ToolEvent(BaseEvent):
    """工具事件：在工具调用前/后各推送一次，驱动前端可视化。"""
    type: Literal["tool"] = "tool"
    tool_call_id: str
    tool_name: str                                   # 工具集名字
    function_name: str                               # 具体工具函数名
    function_args: Dict[str, Any]
    function_result: Optional[ToolResult] = None
    status: ToolEventStatus = ToolEventStatus.CALLING


class WaitEvent(BaseEvent):
    """等待事件：需要用户确认/输入时推送。"""
    type: Literal["wait"] = "wait"


class ErrorEvent(BaseEvent):
    """错误事件。"""
    type: Literal["error"] = "error"
    error: str = ""


class DoneEvent(BaseEvent):
    """任务结束事件。"""
    type: Literal["done"] = "done"


# 事件联合类型（用于序列化/反序列化时的类型判别）
Event = Annotated[
    Union[
        MessageEvent,
        ToolEvent,
        WaitEvent,
        ErrorEvent,
        DoneEvent,
    ],
    Field(discriminator="type"),
]
