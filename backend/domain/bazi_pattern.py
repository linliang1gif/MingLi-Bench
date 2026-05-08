"""格局判断 v2 —— 基于月令 + 透干 + 合冲影响。

规则：
1. 月令本气透干 → 高信心取格
2. 月令本气不透但中气/余气透干 → 低信心 / 杂气格
3. 月令被严重冲克 → break_factor
4. 不确定时输出"不明显"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .bazi_rules import (
    GAN_WUXING,
    GAN_POLARITY,
    TIAN_GAN,
    ZHI_CANG_GAN,
    WUXING_SHENG_WO,
    get_shishen,
)


def analyze_pattern_v2(
    chart: Dict[str, Any],
    strength_result: Dict[str, Any],
    relations_result: Dict[str, Any],
) -> Dict[str, Any]:
    """分析八字格局。

    返回
    ----
    {
        "pattern": str,
        "is_established": bool | None,
        "confidence": "high" | "medium" | "low",
        "evidence": [str],
        "break_factors": [str],
        "uncertainties": [str],
    }
    """
    pillars = chart.get("pillars") or {}
    day_cell = pillars.get("day") or {}
    month_cell = pillars.get("month") or {}
    day_gan = day_cell.get("stem") or ""
    month_zhi = month_cell.get("branch") or ""

    if not day_gan or not month_zhi:
        return _unknown("日主或月令信息缺失")

    # 优先检查特殊格局（从格）
    special = _check_special_pattern(chart, strength_result)
    if special:
        return special

    evidence: List[str] = []
    break_factors: List[str] = []
    uncertainties: List[str] = []

    # --- 月令藏干 ---
    cang_list = ZHI_CANG_GAN.get(month_zhi, [])
    if not cang_list:
        return _unknown(f"月支{month_zhi}藏干数据缺失")

    # --- 收集其他天干 ---
    other_gans: List[str] = []
    for pos in ("year", "month", "hour"):
        cell = pillars.get(pos) or {}
        g = cell.get("stem") or ""
        if g and g != day_gan:
            other_gans.append(g)

    # --- 月令是否被冲 ---
    month_clashed = False
    for clash in (relations_result.get("clashes") or []):
        if "month" in (clash.get("pillars") or []):
            month_clashed = True
            break_factors.append(f"月令{month_zhi}被冲（{clash.get('branches')}），格局动摇")

    # --- 取格 ---
    pattern_gan: Optional[str] = None
    pattern_ss: str = ""
    pattern_source: str = ""
    confidence: str = "low"

    # 规则1：月令藏干透于天干（优先取非比劫的透干）
    for cg, _ in cang_list:
        ss = get_shishen(day_gan, cg)
        if ss in ("比肩", "劫财"):
            continue
        if cg in other_gans:
            pattern_gan = cg
            pattern_ss = ss
            is_main = (cg == cang_list[0][0])
            if is_main:
                confidence = "high" if not month_clashed else "medium"
                pattern_source = f"月令{month_zhi}本气{cg}({ss})透干"
                evidence.append(f"{pattern_source} → 取{ss}格（信心{'高' if confidence == 'high' else '中'}）")
            else:
                confidence = "medium" if not month_clashed else "low"
                idx = next(i for i, (c, _) in enumerate(cang_list) if c == cg)
                qi_label = "中气" if idx == 1 else "余气"
                pattern_source = f"月令{month_zhi}{qi_label}{cg}({ss})透干"
                evidence.append(f"{pattern_source} → 取{ss}格（杂气透出，信心{'中' if confidence == 'medium' else '低'}）")
            break

    # 规则2：无透干 → 取月令主气（非比劫时）
    if not pattern_gan:
        main_cg, _ = cang_list[0]
        main_ss = get_shishen(day_gan, main_cg)
        if main_ss not in ("比肩", "劫财"):
            pattern_gan = main_cg
            pattern_ss = main_ss
            confidence = "medium" if not month_clashed else "low"
            pattern_source = f"月令{month_zhi}本气{main_cg}({main_ss})不透"
            evidence.append(f"{pattern_source} → 仍取{main_ss}格（不透减信心）")
        else:
            # 本气为比劫 → 建禄格/月劫格
            if GAN_POLARITY.get(main_cg) == GAN_POLARITY.get(day_gan):
                pattern_ss = "建禄格"
            else:
                pattern_ss = "月劫格"
            confidence = "medium"
            pattern_source = f"月令{month_zhi}本气{main_cg}为比劫"
            evidence.append(f"{pattern_source} → {pattern_ss}")

            # 检查中气余气是否透干
            for cg, _ in cang_list[1:]:
                ss_inner = get_shishen(day_gan, cg)
                if cg in other_gans and ss_inner not in ("比肩", "劫财"):
                    evidence.append(f"但{cg}({ss_inner})透干 → 可兼论{ss_inner}格")
                    break

    pattern_name = f"{pattern_ss}格" if pattern_ss and "格" not in pattern_ss else (pattern_ss or "不明显")

    # --- 成格/破格判断 ---
    is_established: Optional[bool] = None

    if pattern_ss in ("正官",):
        # 正官格忌伤官/七杀混杂
        for g in other_gans:
            ss = get_shishen(day_gan, g)
            if ss == "伤官":
                break_factors.append(f"正官格遇伤官({g})克官 → 破格风险")
            elif ss == "七杀":
                break_factors.append(f"正官格遇七杀({g})混杂 → 官杀混杂，破格风险")
        if not break_factors:
            for g in other_gans:
                ss = get_shishen(day_gan, g)
                if ss in ("正印", "偏印"):
                    evidence.append(f"正官格配印({g}) → 成格之象")

    elif pattern_ss in ("七杀",):
        for g in other_gans:
            ss = get_shishen(day_gan, g)
            if ss == "食神":
                evidence.append(f"七杀格遇食神({g})制杀 → 成格之象")
            elif ss == "正印":
                evidence.append(f"七杀格遇印星({g})化杀 → 成格之象（杀印相生）")

    elif pattern_ss in ("食神",):
        has_cai = False
        for g in other_gans:
            ss = get_shishen(day_gan, g)
            if ss in ("正财", "偏财"):
                has_cai = True
                evidence.append(f"食神格见财星({g}) → 食神生财成格之象")
            elif ss == "偏印":
                break_factors.append(f"食神格遇枭印({g})夺食 → 破格风险")
        if not has_cai and not break_factors:
            evidence.append("食神格无财星亦无枭印 → 食神制杀待查")

    elif pattern_ss in ("伤官",):
        for g in other_gans:
            ss = get_shishen(day_gan, g)
            if ss in ("正财", "偏财"):
                evidence.append(f"伤官格见财星({g}) → 伤官生财成格之象")
            elif ss in ("正印",):
                evidence.append(f"伤官格见正印({g}) → 伤官配印成格之象")
            elif ss == "正官":
                break_factors.append(f"伤官格见正官({g}) → 伤官见官为祸")

    elif pattern_ss in ("正财", "偏财"):
        for g in other_gans:
            ss = get_shishen(day_gan, g)
            if ss in ("比肩", "劫财"):
                break_factors.append(f"财格遇比劫({g})争财 → 破格风险")
            elif ss in ("食神", "伤官"):
                evidence.append(f"财格见食伤({g}) → 食伤生财成格之象")

    elif pattern_ss in ("正印", "偏印"):
        for g in other_gans:
            ss = get_shishen(day_gan, g)
            if ss in ("正财", "偏财"):
                break_factors.append(f"印格遇财星({g})坏印 → 破格风险")
            elif ss in ("正官", "七杀"):
                evidence.append(f"印格见官杀({g}) → 官印相生成格之象")

    # 综合判断
    if break_factors:
        is_established = False
        if confidence == "high":
            confidence = "medium"
        uncertainties.append("存在破格因素，需结合全局判断")
    elif len(evidence) >= 2 and confidence in ("high", "medium"):
        is_established = True
    else:
        is_established = None
        uncertainties.append("成格/破格尚不明确，需结合合冲刑害深入分析")

    # 月冲降级
    if month_clashed and confidence == "high":
        confidence = "medium"

    return {
        "pattern": pattern_name,
        "pattern_source": pattern_source,
        "is_established": is_established,
        "confidence": confidence,
        "evidence": evidence,
        "break_factors": break_factors,
        "uncertainties": uncertainties,
    }


# ========================== 天干五合 表 ==========================
_TIAN_GAN_HE_TABLE: Dict[frozenset, str] = {
    frozenset(("甲", "己")): "土",
    frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水",
    frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}

# 月支 → 主气五行
_ZHI_MAIN_WX = {
    "寅": "木", "卯": "木", "辰": "土",
    "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土",
    "亥": "水", "子": "水", "丑": "土",
}


def _check_huaqi_pattern(chart: Dict[str, Any], strength_result: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """检查化气格：天干五合且合化成功。

    条件（保守版）：
    1. 日主与邻柱天干成五合
    2. 月令主气 = 合化五行（最关键条件）
    3. 四柱不见克制合化五行的天干有力透出
    4. 合化五行在四柱藏干中有根
    5. 日主不能身强/偏强（强身不化）
    """
    pillars = chart.get("pillars") or {}
    day_cell = pillars.get("day") or {}
    day_gan = day_cell.get("stem") or ""
    if not day_gan:
        return None

    month_cell = pillars.get("month") or {}
    month_zhi = month_cell.get("branch") or ""

    # 找到日主参与的五合
    neighbor_positions = ["month", "hour"]  # 日主只与月干、时干紧邻
    合_partner = None
    合_wx = None
    partner_pos = None

    for pos in neighbor_positions:
        g = (pillars.get(pos) or {}).get("stem") or ""
        if not g:
            continue
        pair = frozenset((day_gan, g))
        if pair in _TIAN_GAN_HE_TABLE:
            合_partner = g
            合_wx = _TIAN_GAN_HE_TABLE[pair]
            partner_pos = pos
            break

    if not 合_wx:
        return None  # 日主无五合

    # 条件5: 日主身强不化 —— 强身保留本气，不会失去身份
    if strength_result:
        s_level = strength_result.get("strength_level", "")
        s_score = strength_result.get("score", 50)
        if s_level in ("身强", "偏强") or s_score >= 60:
            return None  # 日主身强不会化气

    evidence: List[str] = []
    evidence.append(f"日主{day_gan}与{partner_pos}干{合_partner}成五合，化{合_wx}")

    # 条件1: 月令主气支持合化五行
    month_main_wx = _ZHI_MAIN_WX.get(month_zhi, "")
    if month_main_wx != 合_wx:
        # 月令不支持，不成化
        return None
    evidence.append(f"月令{month_zhi}主气为{month_main_wx}，支持合化{合_wx} ✓")

    # 条件2: 合化五行在柱中是否有根（至少2处藏干含合化五行）
    from .bazi_rules import WUXING_KE
    root_count = 0
    for pos in ("year", "month", "day", "hour"):
        zhi = (pillars.get(pos) or {}).get("branch") or ""
        cang_list = ZHI_CANG_GAN.get(zhi, [])
        for cg, _ in cang_list:
            if GAN_WUXING.get(cg) == 合_wx:
                root_count += 1
                break
    if root_count < 2:
        return None  # 合化五行根弱，不成化
    evidence.append(f"合化五行{合_wx}在地支有{root_count}处通根 ✓")

    # 条件3: 无有力克制合化五行的天干
    ke_wx = WUXING_KE.get(合_wx, "")  # 克合化五行的五行
    has_ke = False
    for pos in ("year", "month", "hour"):
        g = (pillars.get(pos) or {}).get("stem") or ""
        if g and GAN_WUXING.get(g) == ke_wx:
            # 检查克者是否有根
            has_root = False
            for p2 in ("year", "month", "day", "hour"):
                zhi = (pillars.get(p2) or {}).get("branch") or ""
                for cg, _ in ZHI_CANG_GAN.get(zhi, []):
                    if GAN_WUXING.get(cg) == ke_wx:
                        has_root = True
                        break
                if has_root:
                    break
            if has_root:
                has_ke = True
                break

    if has_ke:
        return None  # 有力克制，不成化
    evidence.append(f"无有力{ke_wx}(克{合_wx})天干破化 ✓")

    # 化气格成立
    化名 = f"化{合_wx}格"
    return {
        "pattern": 化名,
        "pattern_source": f"{day_gan}{合_partner}合化{合_wx}，月令{month_zhi}支持",
        "is_established": True,
        "confidence": "medium",
        "evidence": evidence,
        "break_factors": [],
        "uncertainties": ["化气格判定严格依赖月令与四柱配合，需人工复核"],
    }


def _check_special_pattern(
    chart: Dict[str, Any],
    strength_result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """检查是否为特殊格局（化气格/从格/专旺格）。

    化气格条件：日主参与天干五合 + 月令支持合化五行 + 合化五行在柱中旺
    从强格条件：同类力量占比 ≥85%，且无有力克泄（无财/官/食透干或仅弱透）
    从弱格条件：同类力量占比 ≤12%，且无有力帮扶（无印/比透干或仅弱透）
    """
    # --- 先检查化气格 ---
    huaqi = _check_huaqi_pattern(chart, strength_result)
    if huaqi:
        return huaqi

    level = strength_result.get("strength_level", "")
    score = strength_result.get("score", 50)
    same_power = strength_result.get("same_power", 0)
    opposite_power = strength_result.get("opposite_power", 0)
    total = same_power + opposite_power
    if total == 0:
        return None

    ratio = same_power / total
    evidence: List[str] = []

    # --- 从强格 ---
    # 严格条件：旺衰模块已标记"疑似从强"，或比例极端（≥88%）
    is_suspected_strong = "从强" in level
    if (is_suspected_strong and ratio >= 0.78) or (ratio >= 0.88 and score >= 85):
        pillars = chart.get("pillars") or {}
        day_gan = (pillars.get("day") or {}).get("stem") or ""
        day_wx = GAN_WUXING.get(day_gan, "")

        # 检查是否有有力财/官/食透干
        has_strong_opposition = False
        for pos in ("year", "month", "hour"):
            g = (pillars.get(pos) or {}).get("stem") or ""
            if not g or g not in GAN_WUXING:
                continue
            gwx = GAN_WUXING[g]
            from .bazi_rules import WUXING_SHENG, WUXING_KE, WUXING_KE_WO
            # 财、官杀、食伤都是克泄耗
            if gwx != day_wx and gwx != WUXING_SHENG_WO.get(day_wx, ""):
                # 检查是否有根（通根则为有力）
                has_root = False
                for p2 in ("year", "month", "day", "hour"):
                    zhi = (pillars.get(p2) or {}).get("branch") or ""
                    for cg, _ in ZHI_CANG_GAN.get(zhi, []):
                        if GAN_WUXING.get(cg) == gwx:
                            has_root = True
                            break
                    if has_root:
                        break
                if has_root:
                    has_strong_opposition = True
                    break

        if not has_strong_opposition:
            evidence.append(f"同类力量占比{ratio*100:.0f}%，异类无根或极弱 → 从强格")
            return {
                "pattern": "从强格",
                "pattern_source": f"日主{day_gan}极旺，同类{same_power:.0f}/异类{opposite_power:.0f}",
                "is_established": True,
                "confidence": "medium",
                "evidence": evidence,
                "break_factors": [],
                "uncertainties": ["从格判定需人工复核，实际命例中从格条件苛刻"],
            }

    # --- 从弱格 ---
    # 严格条件：旺衰模块已标记"疑似从弱"，或比例极端（≤10%）
    is_suspected_weak = "从弱" in level
    if (is_suspected_weak and ratio <= 0.18) or (ratio <= 0.10 and score <= 15):
        pillars = chart.get("pillars") or {}
        day_gan = (pillars.get("day") or {}).get("stem") or ""
        day_wx = GAN_WUXING.get(day_gan, "")

        # 检查是否有有力帮扶（印/比有根）
        has_strong_help = False
        for pos in ("year", "month", "hour"):
            g = (pillars.get(pos) or {}).get("stem") or ""
            if not g or g not in GAN_WUXING:
                continue
            gwx = GAN_WUXING[g]
            from .bazi_rules import WUXING_SHENG_WO as WSW
            if gwx == day_wx or gwx == WSW.get(day_wx, ""):
                # 有帮扶天干，检查通根
                has_root = False
                for p2 in ("year", "month", "day", "hour"):
                    zhi = (pillars.get(p2) or {}).get("branch") or ""
                    for cg, _ in ZHI_CANG_GAN.get(zhi, []):
                        if GAN_WUXING.get(cg) == gwx:
                            has_root = True
                            break
                    if has_root:
                        break
                if has_root:
                    has_strong_help = True
                    break

        if not has_strong_help:
            evidence.append(f"同类力量占比{ratio*100:.0f}%，帮扶无根或极弱 → 从弱格")
            return {
                "pattern": "从弱格",
                "pattern_source": f"日主{day_gan}极弱，同类{same_power:.0f}/异类{opposite_power:.0f}",
                "is_established": True,
                "confidence": "medium",
                "evidence": evidence,
                "break_factors": [],
                "uncertainties": ["从格判定需人工复核，实际命例中从格条件苛刻"],
            }

    return None


def _unknown(reason: str) -> Dict[str, Any]:
    return {
        "pattern": "不明显",
        "pattern_source": "",
        "is_established": None,
        "confidence": "low",
        "evidence": [],
        "break_factors": [],
        "uncertainties": [reason],
    }
