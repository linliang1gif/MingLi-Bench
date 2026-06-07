"""玄空飞星基础盘规则。

V1.1 只实现可解释的基础盘：
- 三元九运
- 朝向角度对应二十四山
- 由向首按二十四山相对表反推坐山
- 运星入中顺飞的简化九宫盘
- 年星入中顺飞的简化年度盘

不包含替卦、兼向、山星/向星复杂起飞。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .compass import MOUNTAINS_24, normalize_degree


PERIOD_ANCHOR_YEAR = 1864
ANNUAL_STAR_ANCHOR_YEAR = 2024
ANNUAL_STAR_ANCHOR_NUMBER = 3

FLYING_ORDER = (
    "center",
    "qian",
    "dui",
    "gen",
    "li",
    "kan",
    "kun",
    "zhen",
    "xun",
)

PALACES = {
    "xun": {"name": "巽宫", "trigram": "巽", "direction": "东南", "grid_row": 0, "grid_col": 0},
    "li": {"name": "离宫", "trigram": "离", "direction": "南", "grid_row": 0, "grid_col": 1},
    "kun": {"name": "坤宫", "trigram": "坤", "direction": "西南", "grid_row": 0, "grid_col": 2},
    "zhen": {"name": "震宫", "trigram": "震", "direction": "东", "grid_row": 1, "grid_col": 0},
    "center": {"name": "中宫", "trigram": "中", "direction": "中", "grid_row": 1, "grid_col": 1},
    "dui": {"name": "兑宫", "trigram": "兑", "direction": "西", "grid_row": 1, "grid_col": 2},
    "gen": {"name": "艮宫", "trigram": "艮", "direction": "东北", "grid_row": 2, "grid_col": 0},
    "kan": {"name": "坎宫", "trigram": "坎", "direction": "北", "grid_row": 2, "grid_col": 1},
    "qian": {"name": "乾宫", "trigram": "乾", "direction": "西北", "grid_row": 2, "grid_col": 2},
}

GRID_ORDER = ("xun", "li", "kun", "zhen", "center", "dui", "gen", "kan", "qian")


def _star(value: int) -> int:
    return ((int(value) - 1) % 9) + 1


def period_for_year(year: int) -> Dict[str, Any]:
    year = int(year)
    period_index = (year - PERIOD_ANCHOR_YEAR) // 20
    period_number = _star(period_index + 1)
    cycle_start = PERIOD_ANCHOR_YEAR + period_index * 20
    cycle_end = cycle_start + 19
    yuan = "上元" if period_number <= 3 else ("中元" if period_number <= 6 else "下元")
    period = f"{yuan}{period_number}运"
    return {
        "year": year,
        "period": period,
        "period_number": period_number,
        "yuan": yuan,
        "cycle_start": cycle_start,
        "cycle_end": cycle_end,
    }


def mountain_index_from_degree(degree: float) -> int:
    value = normalize_degree(degree)
    return int(((value + 7.5) % 360) // 15)


def facing_from_degree(degree: float) -> Dict[str, Any]:
    value = normalize_degree(degree)
    facing_index = mountain_index_from_degree(value)
    sitting_index = (facing_index + 12) % len(MOUNTAINS_24)
    return {
        "degree": value,
        "facing_index": facing_index,
        "facing_direction_24": MOUNTAINS_24[facing_index],
        "sitting_index": sitting_index,
        "sitting_direction_24": MOUNTAINS_24[sitting_index],
    }


def annual_star_for_year(year: int) -> int:
    offset = int(year) - ANNUAL_STAR_ANCHOR_YEAR
    return _star(ANNUAL_STAR_ANCHOR_NUMBER - offset)


def flying_chart(center_star: int) -> Dict[str, Any]:
    palace_map: Dict[str, Any] = {}
    for offset, key in enumerate(FLYING_ORDER):
        palace_map[key] = {**PALACES[key], "key": key, "star": _star(center_star + offset)}
    return {
        "center_star": _star(center_star),
        "flying_order": list(FLYING_ORDER),
        "palaces": palace_map,
        "grid": [palace_map[key] for key in GRID_ORDER],
    }


def build_basic_chart(
    *,
    build_year: int,
    move_in_year: int | None,
    facing_degree: float,
    annual_year: int | None = None,
) -> Dict[str, Any]:
    effective_year = int(move_in_year or build_year)
    annual_year = int(annual_year or effective_year)
    period = period_for_year(effective_year)
    facing = facing_from_degree(facing_degree)
    base_star = flying_chart(period["period_number"])
    annual_center_star = annual_star_for_year(annual_year)
    annual_star = flying_chart(annual_center_star)

    grid: List[Dict[str, Any]] = []
    for key in GRID_ORDER:
        base = base_star["palaces"][key]
        annual = annual_star["palaces"][key]
        grid.append(
            {
                **base,
                "base_star": base["star"],
                "annual_star": annual["star"],
            }
        )

    return {
        "build_year": int(build_year),
        "move_in_year": int(move_in_year) if move_in_year else None,
        "effective_period_year": effective_year,
        "annual_year": annual_year,
        "period": period,
        "facing": facing,
        "base_star": base_star,
        "annual_star": annual_star,
        "grid": grid,
        "method_note": "V1.1 基础盘：运星入中顺飞、年星入中顺飞；不含替卦、兼向、山星/向星复杂起飞。",
    }
