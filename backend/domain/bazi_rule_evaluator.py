"""规则引擎评分器 v2 (Phase 3.6)。

支持两种 schema：
- 旧 schema: expected.strength.{accepted_levels, rejected_levels} / expected.pattern.{accepted_patterns, rejected_patterns}
- 新 schema: expected.{primary_strength_level, accepted_strength_levels, rejected_strength_levels,
                       primary_pattern, accepted_patterns, rejected_patterns,
                       accepted_useful_elements, accepted_avoid_elements, allow_conflict, dispute_notes}

打分维度：
- pillars: 四柱完全匹配
- day_master: 日主匹配
- strength: primary 命中=100, accepted=80, rejected=0(致命)
- pattern: primary 命中=100, accepted=80, rejected=0
- useful_gods: useful/avoid 与 accepted 集合的交集比例

通过条件：
- total_score >= 75
- pillars 或 day_master 错误 → 直接 failed
- strength 落入 rejected_levels → 直接 failed
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# ========================== 维度权重 ==========================

WEIGHTS = {
    "pillars": 30,
    "day_master": 10,
    "strength": 25,
    "pattern": 20,
    "useful_gods": 15,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())  # 100

# 命中类型 → 分数
PRIMARY_SCORE = 100
ACCEPTED_SCORE = 80
LOW_CONF_CAP = 80   # confidence=low 的案例，'不明显/中和' 类灰区最多给 80


# ========================== 主评估函数 ==========================

def evaluate_rule_result(
    case: Dict[str, Any],
    chart: Dict[str, Any],
    rule_result: Dict[str, Any],
) -> Dict[str, Any]:
    """对 chart+rule_result 与 case.expected 比对，返回评分明细。"""
    case_id = case.get("case_id", "?")
    expected = case.get("expected") or {}
    case_conf = (case.get("confidence") or "medium").lower()

    mismatches: List[str] = []
    warnings: List[str] = []
    notes: List[str] = []
    dim_scores: Dict[str, int] = {}
    fatal = False

    # --- 1. 四柱 ---
    p_score, p_mis, p_fatal = _score_pillars(chart, expected.get("pillars") or {})
    dim_scores["pillars"] = p_score
    mismatches.extend(p_mis)
    if p_fatal:
        fatal = True

    # --- 2. 日主 ---
    dm_score, dm_mis, dm_fatal = _score_day_master(chart, expected.get("day_master"))
    dim_scores["day_master"] = dm_score
    mismatches.extend(dm_mis)
    if dm_fatal:
        fatal = True

    # --- 3. 旺衰 ---
    s_score, s_mis, s_warn, s_fatal, s_hit = _score_strength(rule_result, expected, case_conf)
    dim_scores["strength"] = s_score
    mismatches.extend(s_mis)
    warnings.extend(s_warn)
    if s_fatal:
        fatal = True

    # --- 4. 格局 ---
    pat_score, pat_mis, pat_warn, pat_hit = _score_pattern(rule_result, expected, case_conf)
    dim_scores["pattern"] = pat_score
    mismatches.extend(pat_mis)
    warnings.extend(pat_warn)

    # --- 5. 喜用神 ---
    ug_score, ug_mis, ug_warn = _score_useful_gods(rule_result, expected, case_conf)
    dim_scores["useful_gods"] = ug_score
    mismatches.extend(ug_mis)
    warnings.extend(ug_warn)

    # --- 加权总分 ---
    total = sum(dim_scores[k] * WEIGHTS[k] / 100 for k in WEIGHTS)
    total = round(total, 1)

    if fatal:
        passed = False
        notes.append("致命错误：四柱/日主/旺衰落入禁区，强制不通过")
    else:
        passed = total >= 75

    # 命中类型汇总
    primary_hit = (s_hit == "primary") and (pat_hit == "primary")
    accepted_hit = (s_hit in ("primary", "accepted")) and (pat_hit in ("primary", "accepted"))
    rejected_hit = (s_hit == "rejected") or (pat_hit == "rejected")

    dispute_reason = ""
    if expected.get("dispute_notes"):
        # 当落在 accepted 而非 primary 时，说明命中了"流派分歧区"
        if (s_hit == "accepted") or (pat_hit == "accepted"):
            dispute_reason = "实际结论命中 accepted 但非 primary，可能反映流派分歧"

    return {
        "case_id": case_id,
        "title": case.get("title", ""),
        "total_score": total,
        "passed": passed,
        "fatal": fatal,
        "dimension_scores": dim_scores,
        "primary_hit": primary_hit,
        "accepted_hit": accepted_hit,
        "rejected_hit": rejected_hit,
        "hit_breakdown": {"strength": s_hit, "pattern": pat_hit},
        "dispute_reason": dispute_reason,
        "mismatches": mismatches,
        "warnings": warnings,
        "notes": notes,
    }


# ========================== 维度评分 ==========================

def _score_pillars(chart: Dict[str, Any], expected_pillars: Dict[str, str]):
    if not expected_pillars:
        return 100, [], False
    pillars = chart.get("pillars") or {}
    mis: List[str] = []
    correct = 0
    total = 0
    for pos in ("year", "month", "day", "hour"):
        exp = expected_pillars.get(pos)
        if not exp:
            continue
        total += 1
        cell = pillars.get(pos) or {}
        actual = (cell.get("stem") or "") + (cell.get("branch") or "")
        if actual == exp:
            correct += 1
        else:
            mis.append(f"{pos}柱: 期望 {exp}, 实际 {actual}")
    if total == 0:
        return 100, [], False
    score = int(correct * 100 / total)
    fatal = correct < total
    return score, mis, fatal


def _score_day_master(chart: Dict[str, Any], expected_dm: Optional[str]):
    if not expected_dm:
        return 100, [], False
    actual = (chart.get("wuxing") or {}).get("day_master") or ""
    if actual == expected_dm:
        return 100, [], False
    return 0, [f"日主: 期望 {expected_dm}, 实际 {actual}"], True


def _resolve_strength_expected(expected: Dict[str, Any]) -> Tuple[Optional[str], List[str], List[str]]:
    """同时支持新/旧 schema，返回 (primary, accepted, rejected)。"""
    primary = expected.get("primary_strength_level")
    accepted = list(expected.get("accepted_strength_levels") or [])
    rejected = list(expected.get("rejected_strength_levels") or [])

    # 兼容旧 schema
    old = expected.get("strength") or {}
    if not accepted:
        accepted = list(old.get("accepted_levels") or [])
    if not rejected:
        rejected = list(old.get("rejected_levels") or [])
    if primary is None and accepted:
        primary = accepted[0]

    return primary, accepted, rejected


def _resolve_pattern_expected(expected: Dict[str, Any]) -> Tuple[Optional[str], List[str], List[str]]:
    primary = expected.get("primary_pattern")
    accepted = list(expected.get("accepted_patterns") or [])
    rejected = list(expected.get("rejected_patterns") or [])

    # 旧 schema
    old = expected.get("pattern") or {}
    if not accepted:
        accepted = list(old.get("accepted_patterns") or [])
    if not rejected:
        rejected = list(old.get("rejected_patterns") or [])
    if primary is None and accepted:
        primary = accepted[0]

    return primary, accepted, rejected


def _score_strength(rule_result: Dict[str, Any], expected: Dict[str, Any], case_conf: str):
    """旺衰评分。返回 (score, mismatches, warnings, fatal, hit_type)。

    hit_type ∈ {"primary", "accepted", "grey", "rejected", "miss", "n/a"}
    """
    primary, accepted, rejected = _resolve_strength_expected(expected)

    if not primary and not accepted and not rejected:
        return 100, [], [], False, "n/a"

    strength = rule_result.get("strength") or {}
    actual = strength.get("strength_level") or "未知"

    # rejected → 致命
    if rejected and actual in rejected:
        return 0, [f"旺衰: 实际 {actual} 落入 rejected_strength_levels {rejected}"], [], True, "rejected"

    # primary 命中
    if primary and actual == primary:
        return PRIMARY_SCORE, [], [], False, "primary"

    # accepted 命中
    if actual in accepted:
        return ACCEPTED_SCORE, [], [f"旺衰: 命中 accepted ({actual}) 但非 primary ({primary})"], False, "accepted"

    # 灰区（中和/不确定/疑似从）
    if actual in ("中和", "不确定", "疑似从强", "疑似从弱"):
        score = 60 if case_conf == "low" else 40
        if case_conf == "low":
            score = min(score, LOW_CONF_CAP)
        return score, [f"旺衰: 实际 {actual} 不在 accepted {accepted}"], [
            f"旺衰落入灰区({actual})，confidence={case_conf}，部分分 {score}"
        ], False, "grey"

    # 未命中
    return 30, [f"旺衰: 实际 {actual} 不在 accepted {accepted}"], [
        f"旺衰未命中预期范围"
    ], False, "miss"


def _score_pattern(rule_result: Dict[str, Any], expected: Dict[str, Any], case_conf: str):
    primary, accepted, rejected = _resolve_pattern_expected(expected)

    if not primary and not accepted and not rejected:
        return 100, [], [], "n/a"

    pattern = rule_result.get("pattern") or {}
    actual = pattern.get("pattern") or "未知"

    if rejected and actual in rejected:
        return 0, [f"格局: 实际 {actual} 落入 rejected_patterns {rejected}"], [], "rejected"

    if primary and actual == primary:
        return PRIMARY_SCORE, [], [], "primary"

    if actual in accepted:
        return ACCEPTED_SCORE, [], [f"格局: 命中 accepted ({actual}) 但非 primary ({primary})"], "accepted"

    # 不明显 / 杂气
    if actual in ("不明显", "杂气格"):
        score = 60 if case_conf in ("low", "medium") else 40
        if case_conf == "low":
            score = min(score, LOW_CONF_CAP)
        return score, [], [f"格局判定为 '{actual}'，confidence={case_conf}，部分分 {score}"], "grey"

    return 30, [f"格局: 实际 {actual} 不在 accepted {accepted}"], [], "miss"


def _resolve_useful_expected(expected: Dict[str, Any]):
    """同时支持新/旧 schema."""
    accepted_use = expected.get("accepted_useful_elements")
    accepted_av = expected.get("accepted_avoid_elements")
    allow_conflict = expected.get("allow_conflict")

    # 旧 schema
    old = expected.get("useful_gods") or {}
    if accepted_use is None:
        accepted_use = old.get("accepted_useful_elements") or []
    if accepted_av is None:
        accepted_av = old.get("accepted_avoid_elements") or []
    if allow_conflict is None:
        allow_conflict = old.get("allow_conflict", True)

    return list(accepted_use or []), list(accepted_av or []), bool(allow_conflict)


def _score_useful_gods(rule_result: Dict[str, Any], expected: Dict[str, Any], case_conf: str):
    accepted_use_list, accepted_av_list, allow_conflict = _resolve_useful_expected(expected)

    if not accepted_use_list and not accepted_av_list:
        return 100, [], []

    ug = rule_result.get("useful_gods") or {}
    final = ug.get("final_suggestion") or {}
    final_pref = set(final.get("preferred") or [])
    final_avoid = set(final.get("avoid") or [])

    ws = ug.get("wangshuai_method") or ug.get("method_wangshuai") or {}
    gj = ug.get("pattern_method") or ug.get("method_geju") or {}
    ws_use = set(ws.get("useful_elements") or ws.get("useful") or [])
    ws_av = set(ws.get("avoid_elements") or ws.get("avoid") or [])
    gj_use = set(gj.get("useful_elements") or gj.get("useful") or [])
    gj_av = set(gj.get("avoid_elements") or gj.get("avoid") or [])

    all_useful = final_pref | ws_use | gj_use
    all_avoid = final_avoid | ws_av | gj_av

    accepted_use = set(accepted_use_list)
    accepted_av = set(accepted_av_list)

    warns: List[str] = []
    mis: List[str] = []

    use_score = 100
    if accepted_use:
        intersect = all_useful & accepted_use
        if not intersect:
            use_score = 0
            mis.append(f"喜用: 输出 {sorted(all_useful)} 与 accepted {sorted(accepted_use)} 无交集")
        else:
            ratio = len(intersect) / max(1, len(accepted_use))
            use_score = int(min(100, 60 + ratio * 40))
            if intersect != accepted_use:
                warns.append(f"喜用部分匹配: 命中 {sorted(intersect)} / 期望 {sorted(accepted_use)}")

    avoid_score = 100
    if accepted_av:
        intersect = all_avoid & accepted_av
        if not intersect:
            avoid_score = 50
            warns.append(f"忌避: 输出 {sorted(all_avoid)} 与 accepted {sorted(accepted_av)} 无交集，给部分分 50")
        else:
            ratio = len(intersect) / max(1, len(accepted_av))
            avoid_score = int(min(100, 60 + ratio * 40))

    score = int((use_score + avoid_score) / 2)

    if ug.get("conflict") and not allow_conflict:
        score = max(0, score - 30)
        warns.append("两法存在分歧但案例 allow_conflict=false，扣 30")

    return score, mis, warns
