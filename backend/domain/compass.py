"""罗盘角度换算：八方与二十四山。"""

from __future__ import annotations

from typing import Dict


_DIRECTIONS_8 = [
    "北",
    "东北",
    "东",
    "东南",
    "南",
    "西南",
    "西",
    "西北",
]

_MOUNTAINS_24 = [
    "子",
    "癸",
    "丑",
    "艮",
    "寅",
    "甲",
    "卯",
    "乙",
    "辰",
    "巽",
    "巳",
    "丙",
    "午",
    "丁",
    "未",
    "坤",
    "申",
    "庚",
    "酉",
    "辛",
    "戌",
    "乾",
    "亥",
    "壬",
]

MOUNTAINS_24 = tuple(_MOUNTAINS_24)


def normalize_degree(degree: float) -> float:
    value = float(degree)
    if value < 0 or value > 360:
        raise ValueError("degree must be between 0 and 360")
    return 0.0 if value == 360 else value


def direction_8(degree: float) -> str:
    value = normalize_degree(degree)
    idx = int(((value + 22.5) % 360) // 45)
    return _DIRECTIONS_8[idx]


def direction_24(degree: float) -> str:
    value = normalize_degree(degree)
    idx = int(((value + 7.5) % 360) // 15)
    return _MOUNTAINS_24[idx]


def convert_degree(degree: float) -> Dict[str, object]:
    value = normalize_degree(degree)
    return {
        "degree": value,
        "direction_8": direction_8(value),
        "direction_24": direction_24(value),
    }
