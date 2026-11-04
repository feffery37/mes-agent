#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : default.py
@Desc    : 默认 JSON 解析器（实现 JSONParser 协议）。
           使用 json-repair 容忍 LLM 输出的噪声 JSON。
"""
import json
import logging
from typing import Any

import json_repair

from app.domain.external.json_parser import JSONParser

logger = logging.getLogger(__name__)


class DefaultJSONParser(JSONParser):
    """默认 JSON 解析器。"""

    async def invoke(self, content: str) -> Any:
        if content is None:
            return {}
        try:
            return json_repair.loads(content)
        except Exception as e:
            logger.warning(f"[DefaultJSONParser] 解析失败，回退到原始字符串: {str(e)}")
            return content
