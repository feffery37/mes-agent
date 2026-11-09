#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : spc_sop.py
@Desc    : SPC 判异结果与知识库 SOP 的联动匹配（纯函数）。
           按命中规则 / 白名单排除原因关联 SOP，供工具层自动带出处理建议。
           注意：SOP 内容原样返回，模型不得据此建议具体工艺参数数值（硬纪律第 9 条）。
"""
from typing import Dict, List, Optional, Sequence


def match_sops(
        documents: Sequence[Dict],
        rule_ids: Sequence[str],
        model: str = "",
        reasons: Optional[Sequence[str]] = None,
        max_results: int = 3,
) -> List[Dict]:
    """返回与本次判异最相关的 SOP，按匹配度排序。"""
    rules = set(rule_ids)
    reason_set = set(reasons or [])
    scored = []
    for doc in documents:
        if doc.get("model") and model and doc["model"] != model:
            continue
        matched_rules = sorted(set(doc.get("spc_rules", [])) & rules)
        matched_reasons = sorted(set(doc.get("exclude_reasons", [])) & reason_set)
        score = len(matched_rules) * 2 + len(matched_reasons)
        if score == 0:
            continue
        scored.append((score, int(doc.get("cases", 0) or 0), {
            "id": doc.get("id", ""),
            "title": doc.get("title", ""),
            "model": doc.get("model", ""),
            "symptom": doc.get("symptom", ""),
            "content": doc.get("content", ""),
            "root_cause": doc.get("root_cause", ""),
            "cases": doc.get("cases", 0),
            "matched_rules": matched_rules,
            "matched_reasons": matched_reasons,
            "relevance": score,
        }))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]["id"]))
    return [item[2] for item in scored[:max_results]]
