#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : config.py
@Desc    : iMES 设备洞察 Agent 的中控配置。
           1) Settings —— 运行期配置，从 .env / 环境变量加载(pydantic-settings)；
           2) LLMConfig / AgentConfig / MCPConfig —— 业务配置，从 config.yaml 加载；
"""
from functools import lru_cache
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# 一、运行期配置（环境变量 / .env）
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """运行期基础配置，可被环境变量覆盖。"""

    env: str = "development"
    log_level: str = "INFO"
    app_config_filepath: str = "config.yaml"

    # LLM 相关（兼容 OpenAI 协议，默认 DeepSeek）
    llm_provider: str = "openai"          # openai | mock
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model_name: str = "deepseek-chat"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048

    # 数据源
    use_sample_data: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """获取并缓存运行期配置，避免重复读取。"""
    return Settings()


# ---------------------------------------------------------------------------
# 二、业务配置（config.yaml）—— 可动态下发 / 热更新
# ---------------------------------------------------------------------------
class LLMConfig(BaseModel):
    """LLM 动态配置模型。"""

    provider: str = "openai"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    model_name: str = "deepseek-chat"
    temperature: float = 0.0
    max_tokens: int = 2048


class AgentConfig(BaseModel):
    """Agent 动态配置模型"""

    name: str = "equipment_insight"
    max_iterations: int = Field(default=12, ge=1)
    max_retries: int = Field(default=3, ge=1)
    retry_interval: float = Field(default=1.0, ge=0.0)


class MCPConfig(BaseModel):
    """MCP 协议配置。"""

    servers: List[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    """聚合的业务配置。"""

    agent: AgentConfig = Field(default_factory=AgentConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    data_source: dict = Field(default_factory=dict)


@lru_cache()
def get_app_config() -> AppConfig:
    """读取 config.yaml 并构建 AppConfig；环境变量优先级更高。"""
    settings = get_settings()
    filepath = settings.app_config_filepath
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raw = {}

    app_config = AppConfig(**raw)

    # 环境变量覆盖（动态配置：运行期可改）
    app_config.llm.provider = settings.llm_provider or app_config.llm.provider
    app_config.llm.base_url = settings.llm_base_url or app_config.llm.base_url
    app_config.llm.api_key = settings.llm_api_key or app_config.llm.api_key
    app_config.llm.model_name = settings.llm_model_name or app_config.llm.model_name
    app_config.llm.temperature = settings.llm_temperature
    app_config.llm.max_tokens = settings.llm_max_tokens
    return app_config
