#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : memory.py
@Desc    : 内存记忆仓库实现（实现 IMemoryRepository）。
           基础框架使用进程内字典存储；后续可替换为 Postgres/Redis 实现相同接口。
"""
import threading
from typing import Dict, Tuple

from app.domain.models.memory import Memory
from app.domain.repositories.memory import IMemoryRepository


class InMemoryMemoryRepository(IMemoryRepository):
    """基于内存的记忆仓库（单进程、线程安全）。"""

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], Memory] = {}
        self._lock = threading.Lock()

    async def get_memory(self, session_id: str, agent_name: str) -> Memory:
        key = (session_id, agent_name)
        with self._lock:
            memory = self._store.get(key)
            if memory is None:
                memory = Memory()
                self._store[key] = memory
            return memory

    async def save_memory(self, session_id: str, agent_name: str, memory: Memory) -> None:
        key = (session_id, agent_name)
        with self._lock:
            self._store[key] = memory
