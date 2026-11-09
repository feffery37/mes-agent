#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : sample.py
@Desc    : 内置样本数据（设备主数据 / 报警日志 / 工艺参数时序 / 知识库 SOP）。
           对应《iMES 设备洞察 Agent 总体技术方案》中的数据域：
           EQ_EQUIPMENT / EQ_ALARM_LOG / EQ_PARAM_TS / EQ_PARAM_META / KB_DOCUMENT。
           基础框架用内存在内存中模拟；后续替换为真实时序库/数仓即可。
"""
from datetime import datetime, timedelta
from typing import Dict, List

# ---------------------------------------------------------------------------
# 1. 设备主数据 EQ_EQUIPMENT
# ---------------------------------------------------------------------------
EQUIPMENT: Dict[int, Dict] = {
    1: {
        "eid": 1,
        "name": "1号邦定机",
        "model": "ASM-AD830",
        "line": "SMT-A",
        "control_min": 190.0,
        "control_max": 210.0,
        "unit": "℃",
        "param": "TEMP_NOZZLE",
        "param_desc": "喷嘴温度",
    },
    2: {
        "eid": 2,
        "name": "2号贴片机",
        "model": "FUJI-NXT",
        "line": "SMT-A",
        "control_min": 23.0,
        "control_max": 27.0,
        "unit": "℃",
        "param": "ENV_TEMP",
        "param_desc": "环境温度",
    },
    # 3 号与 1 号同产线、同参数，作为 SPC 多设备同期对比的受控对照组
    3: {
        "eid": 3,
        "name": "3号邦定机",
        "model": "ASM-AD830",
        "line": "SMT-A",
        "control_min": 190.0,
        "control_max": 210.0,
        "unit": "℃",
        "param": "TEMP_NOZZLE",
        "param_desc": "喷嘴温度",
    },
}

# ---------------------------------------------------------------------------
# 2. 报警日志 EQ_ALARM_LOG（按设备 + 日期）
# ---------------------------------------------------------------------------
ALARM_LOG: Dict[int, List[Dict]] = {
    1: [
        {"time": "2026-11-02 09:12", "code": "E-210", "desc": "喷嘴温度偏高", "level": "warning"},
        {"time": "2026-11-02 14:35", "code": "E-211", "desc": "温度逼近上限", "level": "warning"},
        {"time": "2026-11-03 08:50", "code": "E-210", "desc": "喷嘴温度偏高", "level": "warning"},
    ],
    2: [
        {"time": "2026-11-03 10:05", "code": "E-301", "desc": "吸嘴真空不足", "level": "error"},
    ],
}

# ---------------------------------------------------------------------------
# 3. 工艺参数时序 EQ_PARAM_TS（按设备 + 参数，合成带上升趋势的序列）
# ---------------------------------------------------------------------------
def _gen_series(eid: int, base: float, slope: float, n: int = 168) -> List[Dict]:
    """生成 n 个小时点的合成时序（基础值 + 线性趋势 + 噪声）。"""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    series = []
    for i in range(n):
        t = now - timedelta(hours=(n - 1 - i))
        value = base + slope * i + (i % 7 - 3) * 0.3
        series.append({"ts": t.strftime("%Y-%m-%d %H:%M"), "value": round(value, 2)})
    return series


def _gen_stable_series(center: float, n: int = 168) -> List[Dict]:
    """受控对照序列：交替小噪声，无趋势、无连续单调、无越界。"""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    series = []
    for i in range(n):
        t = now - timedelta(hours=(n - 1 - i))
        value = center + (0.6 if i % 2 else -0.6) + (i % 5 - 2) * 0.15
        series.append({"ts": t.strftime("%Y-%m-%d %H:%M"), "value": round(value, 2)})
    return series


PARAM_TS: Dict[int, Dict[str, List[Dict]]] = {
    1: {"TEMP_NOZZLE": _gen_series(1, 196.0, 0.42, 168)},
    2: {"ENV_TEMP": _gen_series(2, 24.5, 0.02, 168)},
    3: {"TEMP_NOZZLE": _gen_stable_series(196.0, 168)},
}

# 当前窗口注入业务标记点（P2 白名单演示）：传感器跳变 + 停机记录。
# 真实环境由 MES 停机记录 / 试产工单按时间范围下发，这里用点标记模拟。
_nozzle = PARAM_TS[1]["TEMP_NOZZLE"]
_nozzle[50].update({"value": 260.0, "excluded": True, "reason": "传感器跳变"})
_nozzle[51].update({"excluded": True, "reason": "停机"})

# ---------------------------------------------------------------------------
# 3.1 受控基线期 EQ_PARAM_BASELINE（SPC 用于估计 center / sigma）
#     紧接在当前 168 小时窗口之前；少量点标记停机 / 试产 / 复测口径并排除。
# ---------------------------------------------------------------------------
def _gen_baseline(center: float, n: int = 720) -> List[Dict]:
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    excluded = {120: "停机", 121: "停机", 400: "试产批次", 560: "复测口径切换"}
    points = []
    for i in range(n):
        t = now - timedelta(hours=(n + 168 - 1 - i))
        point = {
            "ts": t.strftime("%Y-%m-%d %H:%M"),
            "value": round(center + (i % 11 - 5) * 0.7, 2),
        }
        if i in excluded:
            point.update({"value": round(center + 18.0, 2), "excluded": True, "reason": excluded[i]})
        points.append(point)
    return points


BASELINE_TS: Dict[int, Dict[str, List[Dict]]] = {
    1: {"TEMP_NOZZLE": _gen_baseline(196.0, 720)},
    2: {"ENV_TEMP": _gen_baseline(24.5, 720)},
    3: {"TEMP_NOZZLE": _gen_baseline(196.0, 720)},
}

# 口径版本：规格 / 复测口径变更时递增，SPC 判定据此提示结论不可用
PARAM_META: Dict[int, Dict[str, Dict]] = {
    1: {"TEMP_NOZZLE": {"limits_version": "v3", "baseline_hours": 720}},
    2: {"ENV_TEMP": {"limits_version": "v1", "baseline_hours": 720}},
    3: {"TEMP_NOZZLE": {"limits_version": "v3", "baseline_hours": 720}},
}

# 口径变更历史：effective_from 落在基线期或当前窗口内时，sigma 与判异结论需人工复核
LIMITS_HISTORY: Dict[int, Dict[str, List[Dict]]] = {
    1: {"TEMP_NOZZLE": [
        {"version": "v2", "effective_from": "2026-08-01 00:00",
         "spec_min": 190.0, "spec_max": 210.0, "reason": "初始规格"},
        {"version": "v3", "effective_from": "2026-09-20 00:00",
         "spec_min": 190.0, "spec_max": 210.0, "reason": "复测口径切换（基线期之前）"},
    ]},
    2: {"ENV_TEMP": [
        {"version": "v1", "effective_from": "2026-01-01 00:00",
         "spec_min": 23.0, "spec_max": 27.0, "reason": "初始规格"},
    ]},
    3: {"TEMP_NOZZLE": [
        {"version": "v2", "effective_from": "2026-08-01 00:00",
         "spec_min": 190.0, "spec_max": 210.0, "reason": "初始规格"},
        {"version": "v3", "effective_from": "2026-11-05 00:00",
         "spec_min": 190.0, "spec_max": 210.0, "reason": "复测口径切换（当前窗口内，演示告警）"},
    ]},
}

# ---------------------------------------------------------------------------
# 4. 知识库 / SOP KB_DOCUMENT
# ---------------------------------------------------------------------------
KB_DOCUMENT: List[Dict] = [
    {
        "id": "SOP-EQ-0123",
        "title": "喷嘴温度异常处理",
        "model": "ASM-AD830",
        "symptom": "温度上升",
        "content": "1) 停机检查加热棒与热电偶；2) 校准温控模块；3) 准备备件 HB-200 并安排计划性更换。",
        "cases": 4,
        "root_cause": "加热棒老化(3/4)",
        "spc_rules": ["N1", "N2", "N3", "N6", "C1"],
    },
    {
        "id": "SOP-EQ-0201",
        "title": "吸嘴真空不足处理",
        "model": "FUJI-NXT",
        "symptom": "吸附失败",
        "content": "1) 清洁吸嘴与过滤器；2) 检查真空泵压力；3) 更换磨损吸嘴。",
        "cases": 2,
        "root_cause": "真空管路堵塞(1/2)",
        "spc_rules": [],
    },
    {
        "id": "SOP-EQ-0310",
        "title": "控制图判异失控处置流程",
        "model": "",
        "symptom": "SPC 判异失控 / 趋势漂移",
        "content": "1) 先核对 LIMITS_VERSION 与复测口径；2) 排除停机、试产批次与传感器跳变点后重新判异；"
                    "3) 通知设备工程师按流程复测并记录；4) 工艺参数调整须走变更流程，不得直接给出数值。",
        "cases": 6,
        "root_cause": "需现场复核（未验证）",
        "spc_rules": ["N1", "N2", "N3", "N5", "N6", "C1"],
    },
    {
        "id": "SOP-EQ-0311",
        "title": "停机与试产批次数据排查",
        "model": "",
        "symptom": "异常点疑似由停机 / 试产引起",
        "content": "1) 核对 MES 停机记录与试产工单时间范围；2) 对标记点做豁免并留痕；"
                    "3) 豁免后重新计算控制限与 Cpk；4) 不得直接删除原始记录。",
        "cases": 3,
        "root_cause": "数据口径问题（待确认）",
        "spc_rules": [],
        "exclude_reasons": ["停机", "试产批次", "传感器跳变"],
    },
]

# ---------------------------------------------------------------------------
# 5. 故障代码标准动作 EQ_FAULT_CODE
# ---------------------------------------------------------------------------
FAULT_CODE: Dict[str, str] = {
    "E-210": "检查加热系统，记录温度曲线",
    "E-211": "立即降速并上报设备工程师",
    "E-301": "检查真空发生装置与吸嘴",
}
