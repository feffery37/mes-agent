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


PARAM_TS: Dict[int, Dict[str, List[Dict]]] = {
    1: {"TEMP_NOZZLE": _gen_series(1, 196.0, 0.42, 168)},
    2: {"ENV_TEMP": _gen_series(2, 24.5, 0.02, 168)},
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
    },
    {
        "id": "SOP-EQ-0201",
        "title": "吸嘴真空不足处理",
        "model": "FUJI-NXT",
        "symptom": "吸附失败",
        "content": "1) 清洁吸嘴与过滤器；2) 检查真空泵压力；3) 更换磨损吸嘴。",
        "cases": 2,
        "root_cause": "真空管路堵塞(1/2)",
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
