"""八字命理规则引擎 —— 旺衰 / 格局 / 喜用神。

纯 Python 规则计算，不依赖 AI。所有判断附带 evidence 证据链，
confidence 置信度，以及 uncertainties 不确定因素。

设计原则：
- 第一版追求稳定可追溯，不追求大师级复杂度
- 不确定时输出 "uncertain"，绝不强行判断
- 所有结论可以被 AI 引用但不可被 AI 覆盖
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ========================== 常量表 ==========================

TIAN_GAN = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
DI_ZHI = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")

GAN_WUXING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土",
    "巳": "火", "午": "火", "未": "土", "申": "金", "酉": "金",
    "戌": "土", "亥": "水",
}

GAN_POLARITY = {g: ("阳" if i % 2 == 0 else "阴") for i, g in enumerate(TIAN_GAN)}

WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
WUXING_SHENG_WO = {v: k for k, v in WUXING_SHENG.items()}
WUXING_KE_WO = {v: k for k, v in WUXING_KE.items()}

# 地支藏干表（主气, [中气, 余气]）—— 权重：主气 60%, 中气 30%, 余气 10%
ZHI_CANG_GAN: Dict[str, List[Tuple[str, float]]] = {
    "子": [("癸", 1.0)],
    "丑": [("己", 0.6), ("癸", 0.3), ("辛", 0.1)],
    "寅": [("甲", 0.6), ("丙", 0.3), ("戊", 0.1)],
    "卯": [("乙", 1.0)],
    "辰": [("戊", 0.6), ("乙", 0.3), ("癸", 0.1)],
    "巳": [("丙", 0.6), ("庚", 0.3), ("戊", 0.1)],
    "午": [("丁", 0.7), ("己", 0.3)],
    "未": [("己", 0.6), ("丁", 0.3), ("乙", 0.1)],
    "申": [("庚", 0.6), ("壬", 0.3), ("戊", 0.1)],
    "酉": [("辛", 1.0)],
    "戌": [("戊", 0.6), ("辛", 0.3), ("丁", 0.1)],
    "亥": [("壬", 0.7), ("甲", 0.3)],
}

# 月令（地支）对应的季节旺相
MONTH_LING_WUXING = {
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "亥": "水", "子": "水",
    "辰": "土", "丑": "土", "未": "土", "戌": "土",
}

# 十神映射
SHISHEN_NAMES = {
    ("same", True): "比肩",
    ("same", False): "劫财",
    ("wo_sheng", True): "食神",
    ("wo_sheng", False): "伤官",
    ("wo_ke", True): "偏财",
    ("wo_ke", False): "正财",
    ("ke_wo", True): "七杀",
    ("ke_wo", False): "正官",
    ("sheng_wo", True): "偏印",
    ("sheng_wo", False): "正印",
}


def get_shishen(day_gan: str, target_gan: str) -> str:
    """计算 target_gan 相对于 day_gan 的十神。"""
    if day_gan == target_gan:
        return "比肩"
    my_wx = GAN_WUXING[day_gan]
    t_wx = GAN_WUXING[target_gan]
    same_pol = GAN_POLARITY[day_gan] == GAN_POLARITY[target_gan]

    if t_wx == my_wx:
        return SHISHEN_NAMES[("same", same_pol)]
    elif t_wx == WUXING_SHENG[my_wx]:
        return SHISHEN_NAMES[("wo_sheng", same_pol)]
    elif t_wx == WUXING_KE[my_wx]:
        return SHISHEN_NAMES[("wo_ke", same_pol)]
    elif t_wx == WUXING_KE_WO[my_wx]:
        return SHISHEN_NAMES[("ke_wo", same_pol)]
    elif t_wx == WUXING_SHENG_WO[my_wx]:
        return SHISHEN_NAMES[("sheng_wo", same_pol)]
    return "未知"


# ===================== 旺衰力量计算 =====================

def _relation_to_day(day_wx: str, target_wx: str) -> str:
    """目标五行相对于日主的关系类别。"""
    if target_wx == day_wx:
        return "帮身"  # 比劫
    if target_wx == WUXING_SHENG_WO[day_wx]:
        return "帮身"  # 印星（生我）
    if target_wx == WUXING_SHENG[day_wx]:
        return "克泄耗"  # 食伤（我生 → 泄）
    if target_wx == WUXING_KE[day_wx]:
        return "克泄耗"  # 财星（我克 → 耗）
    if target_wx == WUXING_KE_WO[day_wx]:
        return "克泄耗"  # 官杀（克我）
    return "未知"


def calculate_strength(chart: Dict[str, Any]) -> Dict[str, Any]:
    """计算日主旺衰。

    输入 chart 结构：compute_chart() 返回的完整 dict。

    返回：
    {
        "day_gan": str,
        "day_wx": str,
        "strength_level": "身强" | "身弱" | "偏强" | "偏弱" | "uncertain",
        "score": float,          # 0-100, 50=平衡, >50 身强, <50 身弱
        "de_ling": bool,         # 得令
        "de_di": float,          # 得地（日支根气力量）
        "de_zhu": float,         # 得助（天干帮身力量）
        "help_score": float,     # 帮身总分
        "drain_score": float,    # 克泄耗总分
        "evidence": [str],
        "uncertainties": [str],
    }
    """
    pillars = chart.get("pillars") or {}
    day_cell = pillars.get("day") or {}
    day_gan = day_cell.get("stem") or ""
    if not day_gan or day_gan not in GAN_WUXING:
        return {"strength_level": "uncertain", "score": 50,
                "evidence": [], "uncertainties": ["日主天干缺失"]}

    day_wx = GAN_WUXING[day_gan]
    month_cell = pillars.get("month") or {}
    month_zhi = month_cell.get("branch") or ""
    evidence: List[str] = []
    uncertainties: List[str] = []

    # ----- 1. 得令（月令）30分 -----
    month_wx = MONTH_LING_WUXING.get(month_zhi, "")
    de_ling = False
    ling_score = 0.0
    if month_wx == day_wx:
        de_ling = True
        ling_score = 30.0
        evidence.append(f"得令：月支{month_zhi}({month_wx})与日主{day_gan}({day_wx})同行，+30")
    elif month_wx == WUXING_SHENG_WO[day_wx]:
        de_ling = True
        ling_score = 20.0
        evidence.append(f"得令（生）：月支{month_zhi}({month_wx})生日主{day_wx}，+20")
    else:
        de_ling = False
        ling_score = 0.0
        evidence.append(f"失令：月支{month_zhi}({month_wx})不帮日主{day_wx}，+0")

    # ----- 2. 得地（地支藏干根气）20分 -----
    de_di_score = 0.0
    for pos in ("year", "day", "hour"):
        cell = pillars.get(pos) or {}
        zhi = cell.get("branch") or ""
        if not zhi or zhi not in ZHI_CANG_GAN:
            continue
        for cg, weight in ZHI_CANG_GAN[zhi]:
            cg_wx = GAN_WUXING.get(cg, "")
            rel = _relation_to_day(day_wx, cg_wx)
            if rel == "帮身":
                pts = weight * 5.0  # 每个藏干最多5分
                de_di_score += pts
                evidence.append(f"得地：{pos}支{zhi}藏{cg}({cg_wx})帮身 +{pts:.1f}")
    de_di_score = min(de_di_score, 20.0)

    # ----- 3. 得助（天干帮身 vs 克泄耗）20分 -----
    help_gan = 0.0
    drain_gan = 0.0
    for pos in ("year", "month", "hour"):
        cell = pillars.get(pos) or {}
        gan = cell.get("stem") or ""
        if not gan or gan not in GAN_WUXING:
            continue
        gan_wx = GAN_WUXING[gan]
        rel = _relation_to_day(day_wx, gan_wx)
        if rel == "帮身":
            help_gan += 5.0
            evidence.append(f"得助：{pos}干{gan}({gan_wx})帮身 +5")
        elif rel == "克泄耗":
            drain_gan += 5.0
            evidence.append(f"克泄耗：{pos}干{gan}({gan_wx})耗身 -5")

    # ----- 4. 月支藏干的额外克泄耗 10分 -----
    drain_month = 0.0
    if month_zhi in ZHI_CANG_GAN:
        for cg, weight in ZHI_CANG_GAN[month_zhi]:
            cg_wx = GAN_WUXING.get(cg, "")
            rel = _relation_to_day(day_wx, cg_wx)
            if rel == "克泄耗":
                pts = weight * 5.0
                drain_month += pts
                evidence.append(f"月藏克泄：月支{month_zhi}藏{cg}({cg_wx})泄身 -{pts:.1f}")
    drain_month = min(drain_month, 10.0)

    # ----- 汇总 -----
    help_total = ling_score + de_di_score + help_gan
    drain_total = drain_gan + drain_month
    # 基准50，帮身加分，克泄耗减分
    raw_score = 50.0 + (help_total - drain_total)
    score = max(0.0, min(100.0, raw_score))

    if score >= 65:
        level = "身强"
    elif score >= 55:
        level = "偏强"
    elif score >= 45:
        level = "uncertain"
        uncertainties.append("旺衰接近平衡，需结合合冲刑害深入分析")
    elif score >= 35:
        level = "偏弱"
    else:
        level = "身弱"

    evidence.append(f"汇总：帮身={help_total:.1f} 克泄耗={drain_total:.1f} 得分={score:.1f}")

    return {
        "day_gan": day_gan,
        "day_wx": day_wx,
        "strength_level": level,
        "score": round(score, 1),
        "de_ling": de_ling,
        "de_di": round(de_di_score, 1),
        "de_zhu": round(help_gan, 1),
        "help_score": round(help_total, 1),
        "drain_score": round(drain_total, 1),
        "evidence": evidence,
        "uncertainties": uncertainties,
    }


# ===================== 格局判断 =====================

def analyze_pattern(chart: Dict[str, Any]) -> Dict[str, Any]:
    """分析八字格局（子平真诠体系）。

    返回：
    {
        "pattern": str,                  # e.g. "伤官格", "正财格"
        "pattern_source": str,           # e.g. "月令酉本气辛(伤官)"
        "is_established": bool | None,   # 成格/破格/不确定
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
        return {
            "pattern": "uncertain",
            "pattern_source": "",
            "is_established": None,
            "evidence": [],
            "break_factors": [],
            "uncertainties": ["日主或月令信息缺失"],
        }

    evidence: List[str] = []
    uncertainties: List[str] = []

    # 月令藏干
    cang_list = ZHI_CANG_GAN.get(month_zhi, [])
    if not cang_list:
        return {
            "pattern": "uncertain",
            "pattern_source": "",
            "is_established": None,
            "evidence": [],
            "break_factors": [],
            "uncertainties": [f"月支{month_zhi}藏干数据缺失"],
        }

    # 取格规则：先看月令藏干是否透于天干
    all_gans = []
    for pos in ("year", "month", "hour"):
        cell = pillars.get(pos) or {}
        g = cell.get("stem") or ""
        if g and g != day_gan:
            all_gans.append(g)

    # 检查月令藏干透出
    pattern_gan = None
    pattern_shishen = ""
    for cg, weight in cang_list:
        if cg in all_gans:
            ss = get_shishen(day_gan, cg)
            if ss not in ("比肩", "劫财"):  # 比劫不取格
                pattern_gan = cg
                pattern_shishen = ss
                evidence.append(f"月令{month_zhi}藏{cg}({ss})透于天干 → 取{ss}格")
                break

    # 如果没有透出，取月令主气（本气不为比劫时）
    if not pattern_gan:
        main_cg, main_wt = cang_list[0]
        ss = get_shishen(day_gan, main_cg)
        if ss not in ("比肩", "劫财"):
            pattern_gan = main_cg
            pattern_shishen = ss
            evidence.append(f"月令{month_zhi}本气{main_cg}({ss})不透 → 仍取{ss}格")
        else:
            # 本气为比劫，看中气余气
            for cg, weight in cang_list[1:]:
                ss_inner = get_shishen(day_gan, cg)
                if cg in all_gans and ss_inner not in ("比肩", "劫财"):
                    pattern_gan = cg
                    pattern_shishen = ss_inner
                    evidence.append(f"月令本气为比劫，中/余气{cg}({ss_inner})透出 → 取{ss_inner}格")
                    break
            if not pattern_gan:
                pattern_shishen = "建禄/月刃"
                evidence.append(f"月令{month_zhi}本气为比劫且无他透 → 建禄格或月刃格")

    pattern_name = f"{pattern_shishen}格" if pattern_shishen else "uncertain"

    # 简单成格/破格判断（第一版仅基础规则）
    break_factors: List[str] = []
    is_established: Optional[bool] = None

    if pattern_shishen in ("正官", "七杀"):
        # 官杀格忌伤官混杂
        for g in all_gans:
            ss = get_shishen(day_gan, g)
            if pattern_shishen == "正官" and ss == "伤官":
                break_factors.append(f"正官格遇伤官({g})克官，有破格之虞")
            elif pattern_shishen == "七杀" and ss == "食神":
                evidence.append(f"七杀格遇食神({g})制杀，有成格之象")
    elif pattern_shishen in ("食神", "伤官"):
        # 食伤格看是否生财或配印
        for g in all_gans:
            ss = get_shishen(day_gan, g)
            if ss in ("正财", "偏财"):
                evidence.append(f"{pattern_shishen}格见财星({g})，食伤生财有成格之象")
            elif ss in ("偏印",) and pattern_shishen == "食神":
                break_factors.append(f"食神格遇枭印({g})夺食，有破格之虞")

    if break_factors:
        is_established = False
        uncertainties.append("破格因素存在，需结合全局深入分析")
    elif len(evidence) >= 2:
        is_established = True
    else:
        is_established = None
        uncertainties.append("成格/破格需结合合冲刑害等深入分析")

    return {
        "pattern": pattern_name,
        "pattern_source": f"月令{month_zhi}{'本气' if not pattern_gan else '透出'}{pattern_gan or cang_list[0][0]}({pattern_shishen})",
        "is_established": is_established,
        "evidence": evidence,
        "break_factors": break_factors,
        "uncertainties": uncertainties,
    }


# ===================== 喜用神推断 =====================

def infer_useful_gods(
    strength: Dict[str, Any],
    pattern: Dict[str, Any],
    chart: Dict[str, Any],
) -> Dict[str, Any]:
    """根据旺衰和格局，推断喜用忌神。

    返回：
    {
        "method_wangshuai": {
            "useful": [str],       # 喜用五行
            "avoid": [str],        # 忌避五行
            "reasons": [str],
        },
        "method_geju": {
            "useful": [str],
            "avoid": [str],
            "reasons": [str],
        },
        "consensus_useful": [str],    # 两法共识喜用
        "consensus_avoid": [str],     # 两法共识忌避
        "conflict": bool,
        "confidence": "high" | "medium" | "low",
        "evidence": [str],
    }
    """
    day_wx = strength.get("day_wx") or ""
    level = strength.get("strength_level") or "uncertain"
    evidence: List[str] = []

    # ----- 旺衰法 -----
    ws_useful: List[str] = []
    ws_avoid: List[str] = []
    ws_reasons: List[str] = []

    if level in ("身弱", "偏弱"):
        # 身弱喜印（生我）和比劫（同我）
        ws_useful = [WUXING_SHENG_WO[day_wx], day_wx]
        # 忌官杀（克我）、财星（我克/耗身）、食伤（我生/泄身）
        ws_avoid = [WUXING_KE_WO[day_wx], WUXING_KE[day_wx], WUXING_SHENG[day_wx]]
        ws_reasons.append(f"身弱({level})：喜{WUXING_SHENG_WO[day_wx]}(印)和{day_wx}(比劫)帮身")
        ws_reasons.append(f"忌{WUXING_KE_WO[day_wx]}(官杀)克身、{WUXING_KE[day_wx]}(财)耗身、{WUXING_SHENG[day_wx]}(食伤)泄身")
    elif level in ("身强", "偏强"):
        # 身强喜食伤泄秀、财星耗身、官杀制身
        ws_useful = [WUXING_SHENG[day_wx], WUXING_KE[day_wx], WUXING_KE_WO[day_wx]]
        ws_avoid = [WUXING_SHENG_WO[day_wx], day_wx]
        ws_reasons.append(f"身强({level})：喜{WUXING_SHENG[day_wx]}(食伤)泄秀、{WUXING_KE[day_wx]}(财)耗身")
        ws_reasons.append(f"忌{WUXING_SHENG_WO[day_wx]}(印)和{day_wx}(比劫)再添旺")
    else:
        ws_reasons.append("旺衰不确定，无法给出明确喜忌")

    # ----- 格局法 -----
    gj_useful: List[str] = []
    gj_avoid: List[str] = []
    gj_reasons: List[str] = []
    ptn = pattern.get("pattern") or "uncertain"

    if "正官" in ptn:
        gj_useful = [WUXING_SHENG_WO[day_wx]]  # 印配官
        gj_avoid = [WUXING_SHENG[day_wx]]  # 伤官破官
        gj_reasons.append(f"正官格：喜印星护官，忌伤官损官")
    elif "七杀" in ptn:
        gj_useful = [WUXING_SHENG[day_wx]]  # 食神制杀
        gj_avoid = []
        gj_reasons.append(f"七杀格：喜食神制杀（顺用）")
    elif "食神" in ptn:
        gj_useful = [WUXING_KE[day_wx]]  # 食伤生财
        gj_avoid = [WUXING_SHENG_WO[day_wx]]  # 枭印夺食
        gj_reasons.append(f"食神格：喜财星顺泄，忌枭印夺食")
    elif "伤官" in ptn:
        gj_useful = [WUXING_KE[day_wx], WUXING_SHENG_WO[day_wx]]
        gj_avoid = []
        gj_reasons.append(f"伤官格：喜生财或配印（伤官配印 / 伤官生财）")
    elif "正财" in ptn or "偏财" in ptn:
        gj_useful = [WUXING_SHENG[day_wx]]  # 食伤生财
        gj_avoid = [WUXING_KE_WO[day_wx]]  # 劫财争财
        gj_reasons.append(f"财格：喜食伤生财，忌比劫争财")
    elif "正印" in ptn or "偏印" in ptn:
        gj_useful = [WUXING_KE_WO[day_wx]]  # 官杀生印
        gj_avoid = [WUXING_KE[day_wx]]  # 财星破印
        gj_reasons.append(f"印格：喜官杀生印，忌财星坏印")
    elif "建禄" in ptn or "月刃" in ptn:
        gj_useful = [WUXING_KE_WO[day_wx], WUXING_KE[day_wx]]
        gj_avoid = []
        gj_reasons.append(f"建禄/月刃格：喜官杀或财星引用")
    else:
        gj_reasons.append(f"格局不确定({ptn})，无法给出格局法喜忌")

    # ----- 求交集 / 冲突 -----
    consensus_useful = [w for w in ws_useful if w in gj_useful]
    consensus_avoid = [w for w in ws_avoid if w in gj_avoid]
    conflict_useful = [w for w in ws_useful if w in gj_avoid]
    conflict_avoid = [w for w in ws_avoid if w in gj_useful]
    has_conflict = bool(conflict_useful or conflict_avoid)

    if has_conflict:
        for w in conflict_useful:
            evidence.append(f"分歧：{w}在旺衰法为喜用，在格局法为忌避")
        for w in conflict_avoid:
            evidence.append(f"分歧：{w}在旺衰法为忌避，在格局法为喜用")

    if level == "uncertain" or ptn == "uncertain":
        conf = "low"
    elif has_conflict:
        conf = "medium"
    else:
        conf = "high"

    return {
        "method_wangshuai": {
            "useful": ws_useful,
            "avoid": ws_avoid,
            "reasons": ws_reasons,
        },
        "method_geju": {
            "useful": gj_useful,
            "avoid": gj_avoid,
            "reasons": gj_reasons,
        },
        "consensus_useful": consensus_useful,
        "consensus_avoid": consensus_avoid,
        "conflict": has_conflict,
        "confidence": conf,
        "evidence": evidence,
    }


# ===================== 统一入口 =====================

def analyze_chart(chart: Dict[str, Any]) -> Dict[str, Any]:
    """v1 入口（保留兼容）。内部已切换至 v3。"""
    return analyze_chart_v3(chart)


def analyze_chart_v2(chart: Dict[str, Any]) -> Dict[str, Any]:
    """v2 规则引擎统一入口：五行力量 + 旺衰 + 合冲刑害 + 格局 + 喜用。

    返回
    ----
    {
        "version": "bazi-rules-v2.0.0",
        "wuxing_power": {...},
        "strength": {...},
        "relations": {...},
        "pattern": {...},
        "useful_gods": {...},
        "overall_confidence": "high/medium/low",
        "warnings": [str],
        # v1 兼容字段
        "rule_engine_version": "2.0.0",
    }
    """
    from .bazi_strength import calculate_wuxing_power, calculate_day_master_strength_v2
    from .bazi_relations import analyze_branch_relations
    from .bazi_pattern import analyze_pattern_v2
    from .bazi_useful_gods import infer_useful_gods_v2
    from .bazi_climate import get_climate_gods

    wuxing_power = calculate_wuxing_power(chart)
    strength = calculate_day_master_strength_v2(chart)
    relations = analyze_branch_relations(chart)
    pattern = analyze_pattern_v2(chart, strength, relations)
    climate = get_climate_gods(chart)
    useful_gods = infer_useful_gods_v2(chart, strength, pattern, relations, climate)

    # 综合信心
    warnings: List[str] = []
    conf_scores = {"high": 3, "medium": 2, "low": 1}
    s_level = strength.get("strength_level") or ""
    if s_level in ("中和", "不确定"):
        s_conf = "low"
    elif "疑似" in s_level:
        s_conf = "medium"  # 疑似从格有专门处理，给 medium
    else:
        s_conf = "high"
    p_conf = pattern.get("confidence") or "low"
    u_conf = (useful_gods.get("final_suggestion") or {}).get("confidence") or "low"

    avg = (conf_scores.get(s_conf, 1) + conf_scores.get(p_conf, 1) + conf_scores.get(u_conf, 1)) / 3
    if avg >= 2.5:
        overall = "high"
    elif avg >= 1.5:
        overall = "medium"
    else:
        overall = "low"

    for u in strength.get("uncertainties") or []:
        warnings.append(f"旺衰: {u}")
    for u in pattern.get("uncertainties") or []:
        warnings.append(f"格局: {u}")
    if useful_gods.get("conflict"):
        warnings.append("喜用神: 旺衰法与格局法存在分歧")

    return {
        "version": "bazi-rules-v2.0.0",
        "rule_engine_version": "2.0.0",  # v1 兼容
        "wuxing_power": wuxing_power,
        "strength": strength,
        "relations": relations,
        "pattern": pattern,
        "useful_gods": useful_gods,
        "climate": climate,
        "overall_confidence": overall,
        "warnings": warnings,
    }


def analyze_chart_v3(chart: Dict[str, Any]) -> Dict[str, Any]:
    """v3 规则引擎：v2 + 调候 + 合化判定 + 流年大运动态交互。

    输出在 v2 基础上扩展：
        "version": "bazi-rules-v3.0.0",
        "climate": {...},
        "climate_merged": {...},
        "transformation": {...},
        "dynamic_relations": {...},
    """
    from .bazi_climate import get_climate_gods, merge_with_useful_gods
    from .bazi_relations import (
        analyze_combination_transformation,
        analyze_dynamic_relations,
    )

    base = analyze_chart_v2(chart)

    # 调候
    climate = get_climate_gods(chart)
    climate_merged = merge_with_useful_gods(climate, base.get("useful_gods") or {})

    # 合化判定
    transformation = analyze_combination_transformation(chart, base.get("relations") or {})

    # 流年大运动态交互
    dayun_list = chart.get("dayun") or []
    current_dy = next((d for d in dayun_list if d.get("current")), None)
    dy_gz = (current_dy or {}).get("ganzhi") or ""
    ln_data = chart.get("liunian") or {}
    ln_gz = ln_data.get("ganzhi") or ""
    dynamic = analyze_dynamic_relations(chart, dayun_ganzhi=dy_gz, liunian_ganzhi=ln_gz)

    warnings = list(base.get("warnings") or [])
    if climate_merged.get("climate_pattern_conflict"):
        warnings.append("调候与格局法存在冲突")
    if transformation.get("checked"):
        true_count = sum(1 for c in transformation["checked"] if c.get("is_transformed") is True)
        if true_count > 0:
            warnings.append(f"识别到 {true_count} 项真合化（参考用）")

    base.update({
        "version": "bazi-rules-v3.0.0",
        "rule_engine_version": "3.0.0",
        "climate": climate,
        "climate_merged": climate_merged,
        "transformation": transformation,
        "dynamic_relations": dynamic,
        "warnings": warnings,
    })
    return base
