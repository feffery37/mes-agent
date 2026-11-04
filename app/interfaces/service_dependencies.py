#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : service_dependencies.py
@Desc    : 依赖注入入口。
           集中构造 LLM / AgentService 等依赖，供接口层使用。
"""
from app.application.services.agent_service import AgentService, get_agent_service

__all__ = ["AgentService", "get_agent_service"]
