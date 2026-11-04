#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : react.py
@Desc    : 设备洞察 Agent（基于 ReAct 架构）。
           系统提示词引导大模型完成「查现状 -> 看趋势 -> 找原因 -> 问对策」的闭环。
"""
import logging

from app.domain.services.agents.base import BaseAgent

logger = logging.getLogger(__name__)


EQUIPMENT_INSIGHT_SYSTEM_PROMPT = """你是一名制造业设备运维专家助手「iMES 设备洞察 Agent」。
你的目标是以自然语言帮助班组长、设备工程师完成设备运维的闭环：
1) 查现状：设备型号、控制限、实时/近期参数与报警；
2) 看趋势：用稳健趋势分析判断参数是否在显著上升/下降；
3) 找原因：结合趋势、报警、维修履历与知识库定位根因；
4) 问对策：给出 SOP 处理建议、历史案例与可执行的维修工单。

你拥有以下工具：query_equipment(查设备)、query_alarm_log(查报警)、analyze_trend(趋势分析)、
predict_failure(故障预测)、explain(可解释性)、search_knowledge(知识库检索)、create_workorder(创建工单)。
请按需调用工具获取定量结论，再组织中文回答。回答要简洁、专业、可执行，并明确数据依据。"""


class EquipmentInsightAgent(BaseAgent):
    """设备洞察 Agent。"""
    name: str = "equipment_insight"
    _system_prompt: str = EQUIPMENT_INSIGHT_SYSTEM_PROMPT
    _format: str = "text"  # 最终以文本回答为主
    _retry_interval: float = 1.0
