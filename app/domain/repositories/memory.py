#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : memory.py
@Desc    : 记忆仓库协议（与课程 domain/repositories 对应）。
           定义记忆的读写接口，便于后续接入 Postgres/Redis 等真实存储。
"""
from typing import Protocol

from app.domain.models.memory import Memory


class IMemoryRepository(Protocol):
    """记忆仓库协议。"""

    async def get_memory(self, session_id: str, agent_name: str) -> Memory:
        """根据会话 id 与 Agent 名字获取记忆。"""
        ...

    async def save_memory(self, session_id: str, agent_name: str, memory: Memory) -> None:
        """持久化记忆。"""
        ...
