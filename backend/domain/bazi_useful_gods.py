"""喜用神推断 v2 —— 旺衰扶抑法 + 格局法双轨。

规则：
1. 身弱 → 喜印比帮身，忌官杀财食伤
2. 身强 → 喜食伤财官泄耗克，忌印比
3. 格局法按格局类型专项推断
4. 两法冲突必须标记
5. 中和/不确定/疑似从格 → 低信心
"""

from __future__ import annotations

from typing import Any, Dict, List

from .bazi_rules import (
    GAN_WUXING,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_SHENG_WO,
    WUXING_KE_WO,
)


def infer_useful_gods_v2(
    chart: Dict[str, Any],
    strength_result: Dict[str, Any],
    pattern_result: Dict[str, Any],
    relations_result: Dict[str, Any],
    climate_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """推断喜用忌神。

    返回
    ----
    {
        "wangshuai_method": {useful_elements, avoid_elements, reason, confidence},
        "pattern_method":   {useful_elements, avoid_elements, reason, confidence},
        "conflict": bool,
        "final_suggestion": {preferred, avoid, confidence, note},
    }
    """
    day_wx = strength_result.get("day_wx") or ""
    level = strength_result.get("strength_level") or "不确定"
    ptn = pattern_result.get("pattern") or "不明显"
    ptn_conf = pattern_result.get("confidence") or "low"
    ptn_established = pattern_result.get("is_established")

    # =================== 旺衰扶抑法 ===================
    ws = _wangshuai_method(day_wx, level)

    # =================== 格局法 ===================
    gj = _pattern_method(day_wx, ptn, ptn_conf, ptn_established)

    # =================== 冲突检测 ===================
    ws_useful_set = set(ws["useful_elements"])
    ws_avoid_set = set(ws["avoid_elements"])
    gj_useful_set = set(gj["useful_elements"])
    gj_avoid_set = set(gj["avoid_elements"])

    conflict_u = ws_useful_set & gj_avoid_set
    conflict_a = ws_avoid_set & gj_useful_set
    has_conflict = bool(conflict_u or conflict_a)

    conflict_notes: List[str] = []
    if conflict_u:
        for w in conflict_u:
            conflict_notes.append(f"{w}在旺衰法为喜用，在格局法为忌避")
    if conflict_a:
        for w in conflict_a:
            conflict_notes.append(f"{w}在旺衰法为忌避，在格局法为喜用")

    # =================== 综合建议 ===================
    final = _final_suggestion(ws, gj, has_conflict, level, ptn_conf, climate_result)

    return {
        "wangshuai_method": ws,
        "pattern_method": gj,
        "conflict": has_conflict,
        "conflict_notes": conflict_notes,
        "final_suggestion": final,
    }


# ========================== 旺衰法 ==========================

def _wangshuai_method(day_wx: str, level: str) -> Dict[str, Any]:
    if not day_wx:
        return {"useful_elements": [], "avoid_elements": [], "reason": ["日主信息缺失"], "confidence": "low"}

    yinxing = WUXING_SHENG_WO[day_wx]    # 生我
    bijie = day_wx                         # 同我
    shishang = WUXING_SHENG[day_wx]       # 我生
    caixing = WUXING_KE[day_wx]           # 我克
    guansha = WUXING_KE_WO[day_wx]        # 克我

    useful: List[str] = []
    avoid: List[str] = []
    reason: List[str] = []
    confidence = "medium"

    if level in ("身弱", "偏弱"):
        useful = [yinxing, bijie]
        avoid = [guansha, caixing, shishang]
        reason.append(f"{level}：喜{yinxing}(印)和{bijie}(比劫)帮身")
        reason.append(f"忌{guansha}(官杀)克身、{caixing}(财)耗身、{shishang}(食伤)泄身")
        confidence = "high" if level == "身弱" else "medium"

    elif level in ("身强", "偏强"):
        useful = [shishang, caixing, guansha]
        avoid = [yinxing, bijie]
        reason.append(f"{level}：喜{shishang}(食伤)泄秀、{caixing}(财)耗身、{guansha}(官杀)制身")
        reason.append(f"忌{yinxing}(印)和{bijie}(比劫)再添旺")
        confidence = "high" if level == "身强" else "medium"

    elif level == "中和":
        # 中和盘不宜强判
        useful = [shishang, caixing]  # 温和泄耗优先
        avoid = []
        reason.append("中和盘：倾向喜食伤/财星温和调候，无明确忌避")
        confidence = "low"

    elif "从强" in level:
        useful = [yinxing, bijie]
        avoid = [guansha, caixing]
        reason.append(f"疑似从强：顺势喜印比，忌官杀财星（低信心）")
        confidence = "low"

    elif "从弱" in level:
        useful = [caixing, guansha, shishang]
        avoid = [yinxing, bijie]
        reason.append(f"疑似从弱：顺势喜财官食伤，忌印比（低信心）")
        confidence = "low"

    else:
        reason.append("旺衰不确定，无法给出明确喜忌")
        confidence = "low"

    return {"useful_elements": useful, "avoid_elements": avoid, "reason": reason, "confidence": confidence}


# ========================== 格局法 ==========================

def _pattern_method(day_wx: str, ptn: str, ptn_conf: str, ptn_est: Any) -> Dict[str, Any]:
    if not day_wx:
        return {"useful_elements": [], "avoid_elements": [], "reason": ["日主信息缺失"], "confidence": "low"}

    yinxing = WUXING_SHENG_WO[day_wx]
    bijie = day_wx
    shishang = WUXING_SHENG[day_wx]
    caixing = WUXING_KE[day_wx]
    guansha = WUXING_KE_WO[day_wx]

    useful: List[str] = []
    avoid: List[str] = []
    reason: List[str] = []
    confidence = ptn_conf if ptn_conf else "low"

    # 破格降信心
    if ptn_est is False:
        confidence = "low"

    if "正官" in ptn:
        useful = [yinxing]       # 印配官
        avoid = [shishang]       # 伤官破官
        reason.append("正官格：喜印星护官，忌伤官损官")
        if ptn_est is True:
            reason.append("成格 → 官印相生为上")

    elif "七杀" in ptn:
        useful = [shishang, yinxing]   # 食神制杀 / 印化杀
        avoid = [caixing]              # 财生杀
        reason.append("七杀格：喜食神制杀或印星化杀，忌财星生杀")

    elif "食神" in ptn:
        useful = [caixing]       # 食伤生财
        avoid = [yinxing]        # 枭印夺食
        reason.append("食神格：喜财星顺泄，忌枭印夺食")

    elif "伤官" in ptn:
        useful = [caixing, yinxing]
        avoid = [guansha]
        reason.append("伤官格：喜生财或配印，忌见官（伤官见官为祸）")

    elif "正财" in ptn or "偏财" in ptn:
        useful = [shishang]      # 食伤生财
        avoid = [bijie]          # 比劫争财
        reason.append("财格：喜食伤生财，忌比劫争财")

    elif "正印" in ptn or "偏印" in ptn:
        useful = [guansha]       # 官杀生印
        avoid = [caixing]        # 财星坏印
        reason.append("印格：喜官杀生印，忌财星坏印")

    elif "建禄" in ptn or "月劫" in ptn:
        useful = [guansha, caixing]
        avoid = []
        reason.append("建禄/月劫格：喜官杀或财星引用")

    elif "从强" in ptn:
        useful = [yinxing, bijie]
        avoid = [guansha, caixing]
        reason.append("从强格：顺其旺势，喜印比，忌官杀财星逆势")
        confidence = "medium"

    elif "从弱" in ptn:
        useful = [caixing, guansha, shishang]
        avoid = [yinxing, bijie]
        reason.append("从弱格：顺其弱势，喜财官食伤，忌印比帮身")
        confidence = "medium"

    elif "化" in ptn and "格" in ptn:
        # 化气格：顺从合化后的五行属性
        化_wx = ptn.replace("化", "").replace("格", "")
        if 化_wx in WUXING_SHENG:
            # 化气格喜生合化五行的元素和同类，忌克合化五行的元素
            useful = [WUXING_SHENG_WO.get(化_wx, ""), 化_wx]
            avoid = [WUXING_KE_WO.get(化_wx, "")]
            useful = [u for u in useful if u]
            avoid = [a for a in avoid if a]
            reason.append(f"化{化_wx}格：顺化气势，喜生扶{化_wx}之五行，忌克{化_wx}")
            confidence = "medium"
        else:
            reason.append(f"化气格({ptn})：无法确定合化五行")
            confidence = "low"

    elif "杂气" in ptn:
        reason.append("杂气格：需看透出何星再定喜忌（低信心）")
        confidence = "low"

    else:
        reason.append(f"格局不明显({ptn})，无法给出格局法喜忌")
        confidence = "low"

    return {"useful_elements": useful, "avoid_elements": avoid, "reason": reason, "confidence": confidence}


# ========================== 综合建议 ==========================

def _final_suggestion(
    ws: Dict[str, Any],
    gj: Dict[str, Any],
    has_conflict: bool,
    level: str,
    ptn_conf: str,
    climate_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    ws_conf = ws.get("confidence", "low")
    gj_conf = gj.get("confidence", "low")

    ws_useful = set(ws.get("useful_elements") or [])
    gj_useful = set(gj.get("useful_elements") or [])
    ws_avoid = set(ws.get("avoid_elements") or [])
    gj_avoid = set(gj.get("avoid_elements") or [])

    # 调候用神
    climate_useful = set()
    climate_conf = "low"
    if climate_result and climate_result.get("primary_useful"):
        climate_useful = set(climate_result["primary_useful"])
        climate_conf = climate_result.get("confidence") or "low"

    # 共识
    consensus_useful = list(ws_useful & gj_useful)
    consensus_avoid = list(ws_avoid & gj_avoid)

    # 信心等级
    conf_rank = {"high": 3, "medium": 2, "low": 1}
    avg_conf = (conf_rank.get(ws_conf, 1) + conf_rank.get(gj_conf, 1)) / 2

    if has_conflict:
        avg_conf = min(avg_conf, 2)
    if "中和" in level or "不确定" in level:
        avg_conf = min(avg_conf, 1.5)
    elif "疑似" in level:
        avg_conf = min(avg_conf, 2)  # 疑似从格降为 medium 而非 low

    # 调候高信心时可提升整体信心
    if climate_conf == "high" and climate_useful:
        avg_conf = min(avg_conf + 0.3, 3)

    if avg_conf >= 2.5:
        final_conf = "high"
    elif avg_conf >= 1.5:
        final_conf = "medium"
    else:
        final_conf = "low"

    # 优先取共识，否则取高信心一方
    if consensus_useful:
        preferred = consensus_useful
    elif conf_rank.get(ws_conf, 1) >= conf_rank.get(gj_conf, 1):
        preferred = list(ws_useful)
    else:
        preferred = list(gj_useful)

    if consensus_avoid:
        avoid_final = consensus_avoid
    elif conf_rank.get(ws_conf, 1) >= conf_rank.get(gj_conf, 1):
        avoid_final = list(ws_avoid)
    else:
        avoid_final = list(gj_avoid)

    # 调候加权：如果调候高信心且调候喜用在 preferred 中，优先排列；
    # 如果调候喜用不在 preferred 但也不在 avoid 中，且调候高信心，加入补充
    if climate_conf == "high" and climate_useful:
        climate_in_preferred = climate_useful & set(preferred)
        climate_not_in_avoid = climate_useful - set(avoid_final)
        climate_supplement = climate_not_in_avoid - set(preferred)
        if climate_in_preferred:
            # 调候验证了现有喜用，把调候五行排到前面
            preferred = list(climate_in_preferred) + [p for p in preferred if p not in climate_in_preferred]
        elif climate_supplement:
            # 调候补充：高信心调候喜用加入 preferred 末尾
            preferred = preferred + list(climate_supplement)

    note = ""
    if has_conflict:
        note = "两法存在分歧，建议结合实际经历验证"
    elif final_conf == "low":
        note = "信心偏低，结论仅供参考"
    elif climate_conf == "high" and climate_useful & set(preferred):
        note = f"调候法亦支持{'、'.join(climate_useful & set(preferred))}为喜用"

    return {
        "preferred": preferred,
        "avoid": avoid_final,
        "confidence": final_conf,
        "note": note,
    }
