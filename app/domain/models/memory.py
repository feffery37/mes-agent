#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : memory.py
@Desc    : Agent 记忆模型（与课程 domain/models/memory.py 对应）。
           以消息字典列表的形式保存会话上下文，支持持久化与压缩。
"""
from typing import Dict, List, Optional


class Memory:
    """Agent 记忆：消息列表 + 基础操作。"""

    def __init__(self, messages: Optional[List[Dict[str, object]]] = None) -> None:
        self._messages: List[Dict[str, object]] = messages or []

    @property
    def empty(self) -> bool:
        return len(self._messages) == 0

    def add_message(self, message: Dict[str, object]) -> None:
        self._messages.append(message)

    def add_messages(self, messages: List[Dict[str, object]]) -> None:
        self._messages.extend(messages)

    def get_messages(self) -> List[Dict[str, object]]:
        return list(self._messages)

    def get_last_message(self) -> Optional[Dict[str, object]]:
        return self._messages[-1] if self._messages else None

    def roll_back(self) -> None:
        """回滚最后一条消息（用于工具调用被用户打断等场景）。"""
        if self._messages:
            self._messages.pop()

    def compact(self) -> None:
        """压缩记忆（基础实现：保留 system 与最近 20 条消息）。"""
        if not self._messages:
            return
        system_msgs = [m for m in self._messages if m.get("role") == "system"]
        others = [m for m in self._messages if m.get("role") != "system"]
        keep = others[-20:]
        self._messages = system_msgs + keep
