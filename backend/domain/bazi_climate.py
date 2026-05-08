"""调候用神（《穷通宝鉴》简化体系）。

调候 = 根据日主 + 出生月份的寒暑燥湿，给出寒暖调和的喜用五行。
本模块提供保守、流派共识度较高的简化版本：
- 寒月（亥/子/丑）：日主普遍喜火（暖局）
- 暑月（巳/午/未）：日主普遍喜水（润局）
- 春月（寅/卯/辰）：木旺，金/火/水视日主决定
- 秋月（申/酉/戌）：金旺，火/木视日主决定

注意
----
1. 这是「简化版」，不替代《穷通宝鉴》完整逐月详查。
2. 输出 confidence 标注：寒/暑月共识高，春/秋月低。
3. 合理与否取决于格局法/旺衰法是否冲突，不应作为唯一依据。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .bazi_rules import GAN_WUXING

# ========================== 调候表 ==========================

# 月支 → 季节类别
MONTH_SEASON: Dict[str, str] = {
    "寅": "spring", "卯": "spring", "辰": "spring",
    "巳": "summer", "午": "summer", "未": "summer",
    "申": "autumn", "酉": "autumn", "戌": "autumn",
    "亥": "winter", "子": "winter", "丑": "winter",
}

# 调候用神简表：(日主五行, 季节) → {"primary": [...], "secondary": [...], "confidence", "note"}
CLIMATE_TABLE: Dict[tuple, Dict[str, Any]] = {
    # ===== 木日主 =====
    ("木", "winter"): {"primary": ["火"], "secondary": ["土"], "confidence": "high",
                       "note": "木生寒月需火暖局，土培根。"},
    ("木", "summer"): {"primary": ["水"], "secondary": ["金"], "confidence": "high",
                       "note": "木生暑月喜水润局，金生水源。"},
    ("木", "spring"): {"primary": ["金", "火"], "secondary": [], "confidence": "medium",
                       "note": "春木旺，喜金修削、火吐秀；具体看强弱。"},
    ("木", "autumn"): {"primary": ["水", "火"], "secondary": [], "confidence": "medium",
                       "note": "秋金克木，喜水通关、火制金。"},

    # ===== 火日主 =====
    ("火", "winter"): {"primary": ["木", "火"], "secondary": [], "confidence": "high",
                       "note": "火生寒月需木生火、比肩助身。"},
    ("火", "summer"): {"primary": ["水"], "secondary": ["金"], "confidence": "high",
                       "note": "火生暑月旺极，喜水克之、金生水。"},
    ("火", "spring"): {"primary": ["木", "水"], "secondary": [], "confidence": "medium",
                       "note": "春火渐旺，喜木生扶或水调候。"},
    ("火", "autumn"): {"primary": ["木", "火"], "secondary": [], "confidence": "medium",
                       "note": "秋火渐衰，喜木生火、火帮身。"},

    # ===== 土日主 =====
    ("土", "winter"): {"primary": ["火"], "secondary": ["木"], "confidence": "high",
                       "note": "土生寒月冻土需火暖，木疏松（少量）。"},
    ("土", "summer"): {"primary": ["水", "金"], "secondary": [], "confidence": "high",
                       "note": "土生暑月燥裂，喜水润、金生水。"},
    ("土", "spring"): {"primary": ["火", "土"], "secondary": [], "confidence": "medium",
                       "note": "春土虚薄，喜火生土、比肩助身。"},
    ("土", "autumn"): {"primary": ["火", "木"], "secondary": [], "confidence": "low",
                       "note": "秋土秉令而泄于金，喜火生扶或木疏。"},

    # ===== 金日主 =====
    ("金", "winter"): {"primary": ["火", "土"], "secondary": [], "confidence": "high",
                       "note": "金生寒月寒冷，喜火暖局、土生金。"},
    ("金", "summer"): {"primary": ["水", "土"], "secondary": [], "confidence": "high",
                       "note": "金生暑月被火克，喜水润、土生金。"},
    ("金", "spring"): {"primary": ["土", "火"], "secondary": [], "confidence": "medium",
                       "note": "春金衰弱，喜土生扶或火炼真金。"},
    ("金", "autumn"): {"primary": ["火", "木"], "secondary": [], "confidence": "medium",
                       "note": "秋金当令旺极，喜火炼、木耗。"},

    # ===== 水日主 =====
    ("水", "winter"): {"primary": ["火", "土"], "secondary": [], "confidence": "high",
                       "note": "水生寒月寒水冰冻，喜火解寒、土制水。"},
    ("水", "summer"): {"primary": ["金", "水"], "secondary": [], "confidence": "high",
                       "note": "水生暑月源涸，喜金生水、比肩助身。"},
    ("水", "spring"): {"primary": ["金", "火"], "secondary": [], "confidence": "medium",
                       "note": "春水气泄于木，喜金生水或火调候。"},
    ("水", "autumn"): {"primary": ["木", "火"], "secondary": [], "confidence": "low",
                       "note": "秋水得金生旺，喜木泄秀或火克。"},
}


# ========================== 主函数 ==========================

def get_climate_gods(chart: Dict[str, Any]) -> Dict[str, Any]:
    """根据日主 + 月令推断调候用神。

    返回
    ----
    {
        "day_wx": str,
        "season": "spring/summer/autumn/winter",
        "month_branch": str,
        "primary_useful": [str],
        "secondary_useful": [str],
        "confidence": "high/medium/low",
        "note": str,
        "evidence": [str],
    }
    """
    pillars = chart.get("pillars") or {}
    day_cell = pillars.get("day") or {}
    month_cell = pillars.get("month") or {}

    day_gan = day_cell.get("stem") or ""
    month_zhi = month_cell.get("branch") or ""

    if not day_gan or not month_zhi:
        return _empty("日主或月令信息缺失")

    day_wx = GAN_WUXING.get(day_gan)
    if not day_wx:
        return _empty(f"未知日主天干 {day_gan!r}")

    season = MONTH_SEASON.get(month_zhi)
    if not season:
        return _empty(f"未知月支 {month_zhi!r}")

    entry = CLIMATE_TABLE.get((day_wx, season))
    if not entry:
        return _empty(f"调候表未覆盖 ({day_wx}, {season})")

    evidence = [
        f"日主 {day_gan}({day_wx}) 生 {month_zhi} 月（{season}）",
        f"调候建议：{'、'.join(entry['primary'])}（主用）"
        + (f" + {'、'.join(entry['secondary'])}（次用）" if entry["secondary"] else ""),
        entry["note"],
    ]

    return {
        "day_wx": day_wx,
        "season": season,
        "month_branch": month_zhi,
        "primary_useful": list(entry["primary"]),
        "secondary_useful": list(entry["secondary"]),
        "confidence": entry["confidence"],
        "note": entry["note"],
        "evidence": evidence,
    }


def merge_with_useful_gods(climate_result: Dict[str, Any], useful_gods_v2: Dict[str, Any]) -> Dict[str, Any]:
    """把调候建议与 v2 喜用神交叉验证，输出综合视图。

    返回
    ----
    {
        "climate_useful": [str],          # 调候喜
        "wangshuai_useful": [str],        # 旺衰法喜
        "pattern_useful": [str],          # 格局法喜
        "consensus_three_way": [str],     # 三法共识
        "any_method_useful": [str],       # 至少一法支持
        "climate_pattern_conflict": bool,
        "note": str,
    }
    """
    climate_useful = set(climate_result.get("primary_useful") or [])
    climate_secondary = set(climate_result.get("secondary_useful") or [])

    ws = useful_gods_v2.get("wangshuai_method") or useful_gods_v2.get("method_wangshuai") or {}
    gj = useful_gods_v2.get("pattern_method") or useful_gods_v2.get("method_geju") or {}
    ws_useful = set(ws.get("useful_elements") or ws.get("useful") or [])
    gj_useful = set(gj.get("useful_elements") or gj.get("useful") or [])

    consensus = climate_useful & ws_useful & gj_useful
    any_method = climate_useful | ws_useful | gj_useful

    # 调候 vs 格局冲突：调候喜某五行，但格局法忌之
    gj_avoid = set(gj.get("avoid_elements") or gj.get("avoid") or [])
    conflict = bool(climate_useful & gj_avoid)

    note = ""
    if consensus:
        note = f"三法共识喜用：{'、'.join(sorted(consensus))}"
    elif conflict:
        note = "调候与格局法存在冲突，需结合大运流年具体看"
    elif any_method:
        note = "三法各有侧重，无完全共识"

    return {
        "climate_useful": sorted(climate_useful),
        "climate_secondary": sorted(climate_secondary),
        "wangshuai_useful": sorted(ws_useful),
        "pattern_useful": sorted(gj_useful),
        "consensus_three_way": sorted(consensus),
        "any_method_useful": sorted(any_method),
        "climate_pattern_conflict": conflict,
        "note": note,
    }


def _empty(reason: str) -> Dict[str, Any]:
    return {
        "day_wx": "",
        "season": "",
        "month_branch": "",
        "primary_useful": [],
        "secondary_useful": [],
        "confidence": "low",
        "note": reason,
        "evidence": [reason],
    }
