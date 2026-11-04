#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : uow.py
@Desc    : 工作单元(Unit of Work)协议 + 内存实现。
          DDD 分层：通过 uow_factory 注入，BaseAgent 在事务上下文中读写记忆。
"""
from typing import Callable, Protocol

from app.domain.repositories.memory import IMemoryRepository


class IUnitOfWork(Protocol):
    """工作单元协议。"""
    session: IMemoryRepository

    async def __aenter__(self):
        ...

    async def __aexit__(self, exc_type, exc, tb):
        ...


class InMemoryUnitOfWork:
    """内存工作单元：持有内存记忆仓库，并提供异步上下文管理器语义。"""

    def __init__(self, repository: IMemoryRepository) -> None:
        self.session = repository

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None
