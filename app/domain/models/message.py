#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : message.py
@Desc    : 消息领域模型（与课程 domain/models/message.py 对应）。
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """用户输入 / Agent 输出的消息模型。"""

    message: str = ""                                  # 消息正文
    attachments: List[str] = Field(default_factory=list)  # 附件路径列表
    role: Optional[str] = "user"                       # 角色
