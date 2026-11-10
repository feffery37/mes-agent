#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : test_inbox.py
@Desc    : 待确认收件箱单测：两类草稿聚合、只读性、确认后出队、过期清理。
           运行：uv run pytest tests/test_inbox.py -q
"""
import asyncio
from datetime import timedelta

from app.application.services.notification_service import get_notification_service
from app.domain.models.notification import Notification
from app.domain.services.tools import workorder as wo
from app.domain.services.tools.workorder import WorkOrderTool
from app.interfaces.endpoints.inbox_routes import list_pending_items


def _reset() -> None:
    wo._PENDING.clear()
    get_notification_service()._pending.clear()


def _inbox():
    return asyncio.run(list_pending_items())


def _make_workorder() -> str:
    result = asyncio.run(WorkOrderTool().create_workorder(1, "温度漂移排查"))
    return result.data["confirm_token"]


def _make_notification():
    service = get_notification_service()
    token, _ = service.create_draft(Notification(
        title="设备故障风险预警",
        body="故障概率 0.963",
        channels=["wecom"],
    ))
    return token, service


def test_inbox_empty_after_reset():
    _reset()
    resp = _inbox()
    assert resp.total == 0
    assert resp.items == []


def test_inbox_aggregates_both_kinds_and_is_read_only():
    _reset()
    wo_token = _make_workorder()
    ntf_token, _ = _make_notification()

    resp = _inbox()
    assert resp.total == 2
    assert {item.kind for item in resp.items} == {"workorder", "notification"}
    by_token = {item.confirm_token: item for item in resp.items}
    assert by_token[wo_token].draft["eid"] == 1
    assert by_token[wo_token].title == "温度漂移排查"
    assert by_token[ntf_token].draft["title"] == "设备故障风险预警"
    assert by_token[ntf_token].remaining_seconds > 0
    # 重复读取是只读的，不会消耗令牌
    assert _inbox().total == 2


def test_inbox_confirm_removes_item():
    _reset()
    wo_token = _make_workorder()
    ntf_token, service = _make_notification()

    assert WorkOrderTool().confirm_workorder(wo_token, "confirm").success
    assert [item.confirm_token for item in _inbox().items] == [ntf_token]

    assert asyncio.run(service.confirm(ntf_token, "cancel")).success
    assert _inbox().total == 0


def test_inbox_purges_expired_items():
    _reset()
    wo_token = _make_workorder()
    ntf_token, service = _make_notification()
    for pending in (wo._PENDING[wo_token], service._pending[ntf_token]):
        pending["created_at"] -= timedelta(minutes=11)

    assert _inbox().total == 0
