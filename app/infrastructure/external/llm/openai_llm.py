#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : openai_llm.py
@Desc    : 基于 OpenAI SDK / 兼容协议的 LLM 实现。。
"""
import logging
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI

from app.application.errors.exceptions import ServerRequestsError
from app.domain.external.llm import LLM
from core.config import LLMConfig

logger = logging.getLogger(__name__)


class OpenAILLM(LLM):
    """基于 OpenAI 兼容协议的异步 LLM 调用类。"""

    def __init__(self, llm_config: LLMConfig, **kwargs) -> None:
        self._client = AsyncOpenAI(
            base_url=str(llm_config.base_url),
            api_key=llm_config.api_key,
            **kwargs,
        )
        self._model_name = llm_config.model_name
        self._temperature = llm_config.temperature
        self._max_tokens = llm_config.max_tokens
        self._timeout = 3600

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    async def invoke(
            self,
            messages: List[Dict[str, Any]],
            tools: Optional[List[Dict[str, Any]]] = None,
            response_format: Optional[Dict[str, Any]] = None,
            tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """异步调用 LLM，返回 OpenAI 格式的 message 字典。"""
        try:
            if tools:
                logger.info(f"[OpenAILLM] 携带工具调用模型 {self._model_name}")
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    messages=messages,
                    response_format=response_format,
                    tools=tools,
                    tool_choice=tool_choice,
                    parallel_tool_calls=False,
                    timeout=self._timeout,
                )
            else:
                logger.info(f"[OpenAILLM] 普通调用模型 {self._model_name}")
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    messages=messages,
                    response_format=response_format,
                    timeout=self._timeout,
                )

            message = response.choices[0].message
            # 兼容 reasoning_content（DeepSeek 思考模型）
            result = {"role": "assistant", "content": message.content}
            if getattr(message, "reasoning_content", None):
                result["reasoning_content"] = message.reasoning_content
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
            return result
        except Exception as e:
            logger.error(f"[OpenAILLM] 调用出错: {str(e)}")
            raise ServerRequestsError("调用 LLM 接口出错") from e
