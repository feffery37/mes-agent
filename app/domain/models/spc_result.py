#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : spc_result.py
@Desc    : SPC 判异结果领域模型。所有数值均由工具内部计算，可追溯。
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SpcViolation(BaseModel):
    """一条判异规则的命中记录。"""

    rule: str
    title: str
    severity: Literal["critical", "warning", "info"] = "warning"
    start: str = ""
    end: str = ""
    length: int = 0
    max_z: Optional[float] = None
    detail: str = ""
    indices: List[int] = Field(default_factory=list)
    indices_truncated: bool = False
    cross_check: Optional[str] = None


class SpcResult(BaseModel):
    """一次 SPC 判异的完整结果。"""

    eid: int
    param: str
    window: str
    n: int
    baseline: Dict = Field(default_factory=dict)
    limits: Dict = Field(default_factory=dict)
    rule_set: List[str] = Field(default_factory=list)
    violations: List[SpcViolation] = Field(default_factory=list)
    verdict: Literal["失控", "需关注", "受控", "无法判断"] = "受控"
    grade: Literal["数据支持", "推测", "无法判断"] = "推测"
    conclusion: str = ""
    caveats: List[str] = Field(default_factory=list)
    cross_check: Optional[Dict] = None
    limits_version_status: Optional[Dict] = None
    peer_comparison: Optional[Dict] = None
    effective_n: Optional[int] = None
    exclusions: List[Dict] = Field(default_factory=list)
    related_sops: List[Dict] = Field(default_factory=list)
    time_range: Dict = Field(default_factory=dict)
