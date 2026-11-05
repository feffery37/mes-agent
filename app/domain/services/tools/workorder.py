#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : workorder.py
@Desc    : 维修工单工具（对应数据域 PR_WORKORDER）。
           基础框架在内存中维护工单；真实环境对接 MES / 工单系统。
"""
import itertools
import logging
import uuid
from datetime import datetime, timedelta

from app.domain.models.tool_result import ToolResult
from app.domain.services.tools.base import BaseTool, tool

logger = logging.getLogger(__name__)

_counter = itertools.count(1001)
_WORKORDERS: dict = {}
# 待人工确认的工单申请：confirm_token -> {"draft": {...}, "created_at": datetime}
_PENDING: dict = {}
_TOKEN_TTL = timedelta(minutes=10)


def _purge_expired() -> None:
    """清理过期令牌，避免待确认单长期滞留。"""
    now = datetime.now()
    for token in [t for t, p in _PENDING.items() if now - p["created_at"] > _TOKEN_TTL]:
        _PENDING.pop(token, None)


class WorkOrderTool(BaseTool):
    """维修工单工具集（写操作需人工确认，人在回路）。

    LLM 只能生成「待确认单」；真正的创建入口是 confirm_workorder()，
    它不是 @tool，不出现在 get_tools() 里，LLM 无任何路径触发写操作。
    """
    name = "workorder"

    @tool(
        name="create_workorder",
        description="生成一张「待用户确认」的维修工单申请，不会直接创建工单。"
                    "返回 confirm_token 与拟建单内容；只有用户在界面点击确认后系统才会真正创建。",
        parameters={
            "eid": {"type": "integer", "description": "设备ID"},
            "title": {"type": "string", "description": "工单标题"},
            "priority": {"type": "string", "description": "优先级 low/normal/high，默认 normal"},
        },
        required=["eid", "title"],
    )
    async def create_workorder(self, eid: int, title: str, priority: str = "normal") -> ToolResult:
        _purge_expired()
        token = f"cfm-{uuid.uuid4().hex[:12]}"
        draft = {"eid": int(eid), "title": title, "priority": priority or "normal"}
        _PENDING[token] = {"draft": draft, "created_at": datetime.now()}
        logger.info("[HITL] 生成待确认工单 token=%s draft=%s", token, draft)
        return ToolResult.ok(
            data={
                "status": "pending_confirmation",
                "confirm_token": token,
                "draft": draft,
                "expires_in_seconds": int(_TOKEN_TTL.total_seconds()),
                "hint": "尚未创建工单，需用户在确认卡片上点击「确认建单」",
            },
            message="已生成待确认工单，等待用户确认（当前未创建）",
        )

    def confirm_workorder(self, confirm_token: str, action: str = "confirm") -> ToolResult:
        """人工确认入口：仅由 /api/workorder/confirm 调用，不暴露给 LLM。"""
        _purge_expired()
        pending = _PENDING.get(confirm_token)
        if not pending:
            return ToolResult.fail("确认令牌无效或已过期，请重新发起建单")
        _PENDING.pop(confirm_token, None)

        if action == "cancel":
            logger.info("[HITL] 用户取消建单 token=%s", confirm_token)
            return ToolResult.ok(
                data={"status": "cancelled", "confirm_token": confirm_token},
                message="已取消建单，未创建任何工单",
            )

        # 用待确认单的原始内容创建，忽略任何外部传入的字段，防止确认内容被篡改
        wo_id = f"WO-{next(_counter)}"
        workorder = {
            **pending["draft"],
            "wo_id": wo_id,
            "status": "created",
            "confirmed_by": "user",
            "confirmed_at": datetime.now().isoformat(timespec="seconds"),
        }
        _WORKORDERS[wo_id] = workorder
        logger.info("[HITL] 用户确认建单 token=%s wo=%s", confirm_token, wo_id)
        return ToolResult.ok(
            data={"status": "created", "workorder": workorder},
            message=f"工单 {wo_id} 创建成功",
        )

    @tool(
        name="query_workorder",
        description="查询已创建的维修工单（仅用户确认后创建的单才会出现）。",
        parameters={
            "wo_id": {"type": "string", "description": "工单号，留空返回全部"},
        },
        required=[],
    )
    async def query_workorder(self, wo_id: str = "") -> ToolResult:
        if wo_id:
            return ToolResult.ok(data=_WORKORDERS.get(wo_id), message="查询完成")
        return ToolResult.ok(data=list(_WORKORDERS.values()), message="查询完成")
