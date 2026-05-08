"""地支关系分析：六合、六冲、三合、三会、六害、三刑、自刑。

初版只识别关系，不过度推断吉凶。
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

# ========================== 关系表 ==========================

# 六合 {(A, B): 合化五行}
LIU_HE: Dict[frozenset, str] = {
    frozenset(("子", "丑")): "土",
    frozenset(("寅", "亥")): "木",
    frozenset(("卯", "戌")): "火",
    frozenset(("辰", "酉")): "金",
    frozenset(("巳", "申")): "水",
    frozenset(("午", "未")): "火/土",
}

# 六冲 {(A, B)}
LIU_CHONG: Set[frozenset] = {
    frozenset(("子", "午")),
    frozenset(("丑", "未")),
    frozenset(("寅", "申")),
    frozenset(("卯", "酉")),
    frozenset(("辰", "戌")),
    frozenset(("巳", "亥")),
}

# 三合 [(A, B, C, 合化五行)]
SAN_HE: List[Tuple[str, str, str, str]] = [
    ("申", "子", "辰", "水"),
    ("寅", "午", "戌", "火"),
    ("巳", "酉", "丑", "金"),
    ("亥", "卯", "未", "木"),
]

# 三会 [(A, B, C, 会化五行)]
SAN_HUI: List[Tuple[str, str, str, str]] = [
    ("寅", "卯", "辰", "木"),
    ("巳", "午", "未", "火"),
    ("申", "酉", "戌", "金"),
    ("亥", "子", "丑", "水"),
]

# 六害 {(A, B)}
LIU_HAI: Set[frozenset] = {
    frozenset(("子", "未")),
    frozenset(("丑", "午")),
    frozenset(("寅", "巳")),
    frozenset(("卯", "辰")),
    frozenset(("申", "亥")),
    frozenset(("酉", "戌")),
}

# 三刑
# 无恩之刑
SAN_XING_WUEN: List[Tuple[str, str, str]] = [
    ("寅", "巳", "申"),
]
# 恃势之刑
SAN_XING_SHISHI: List[Tuple[str, str, str]] = [
    ("丑", "未", "戌"),
]
# 无礼之刑 (两两互刑)
XING_PAIR: Set[frozenset] = {
    frozenset(("子", "卯")),
}
# 自刑
ZI_XING: Set[str] = {"辰", "午", "酉", "亥"}


# ========================== 主分析函数 ==========================

def _get_branches(chart: Dict[str, Any]) -> List[Tuple[str, str]]:
    """提取四柱地支列表 [(pillar_key, branch), ...]"""
    pillars = chart.get("pillars") or {}
    result = []
    for pos in ("year", "month", "day", "hour"):
        cell = pillars.get(pos) or {}
        b = cell.get("branch") or ""
        if b:
            result.append((pos, b))
    return result


def analyze_branch_relations(chart: Dict[str, Any]) -> Dict[str, Any]:
    """分析四柱地支间的合冲刑害关系。

    返回
    ----
    {
        "combinations": [{"type": "六合", "branches": [...], "pillars": [...], "result": str}],
        "clashes": [...],
        "harms": [...],
        "punishments": [...],
        "meetings": [...],
        "evidence": [str],
    }
    """
    branches = _get_branches(chart)
    branch_set = {b for _, b in branches}
    branch_list = [b for _, b in branches]

    combinations: List[Dict[str, Any]] = []
    clashes: List[Dict[str, Any]] = []
    harms: List[Dict[str, Any]] = []
    punishments: List[Dict[str, Any]] = []
    meetings: List[Dict[str, Any]] = []
    evidence: List[str] = []

    # --- 两两关系 ---
    for i in range(len(branches)):
        for j in range(i + 1, len(branches)):
            p1, b1 = branches[i]
            p2, b2 = branches[j]
            pair = frozenset((b1, b2))

            # 六合
            if pair in LIU_HE:
                result_wx = LIU_HE[pair]
                combinations.append({
                    "type": "六合",
                    "branches": [b1, b2],
                    "pillars": [p1, p2],
                    "result": f"合化{result_wx}",
                })
                evidence.append(f"{p1}{b1}与{p2}{b2}六合（合化{result_wx}）")

            # 六冲
            if pair in LIU_CHONG:
                clashes.append({
                    "type": "六冲",
                    "branches": [b1, b2],
                    "pillars": [p1, p2],
                })
                evidence.append(f"{p1}{b1}与{p2}{b2}六冲")

            # 六害
            if pair in LIU_HAI:
                harms.append({
                    "type": "六害",
                    "branches": [b1, b2],
                    "pillars": [p1, p2],
                })
                evidence.append(f"{p1}{b1}与{p2}{b2}六害")

            # 子卯刑
            if pair in XING_PAIR:
                punishments.append({
                    "type": "无礼之刑",
                    "branches": [b1, b2],
                    "pillars": [p1, p2],
                })
                evidence.append(f"{p1}{b1}与{p2}{b2}无礼之刑")

    # --- 三合 ---
    for a, b, c, wx in SAN_HE:
        present = []
        present_pillars = []
        for pos, br in branches:
            if br in (a, b, c):
                present.append(br)
                present_pillars.append(pos)
        unique_present = set(present)
        if len(unique_present) >= 3 and {a, b, c} <= unique_present:
            combinations.append({
                "type": "三合",
                "branches": [a, b, c],
                "pillars": present_pillars[:3],
                "result": f"合化{wx}局",
            })
            evidence.append(f"{a}{b}{c}三合{wx}局")
        elif len(unique_present) == 2:
            # 半合
            missing = ({a, b, c} - unique_present).pop()
            combinations.append({
                "type": "半合",
                "branches": sorted(unique_present),
                "pillars": present_pillars[:2],
                "result": f"半合{wx}（缺{missing}）",
            })
            evidence.append(f"{''.join(sorted(unique_present))}半合{wx}（缺{missing}）")

    # --- 三会 ---
    for a, b, c, wx in SAN_HUI:
        if {a, b, c} <= branch_set:
            p_list = []
            for pos, br in branches:
                if br in (a, b, c):
                    p_list.append(pos)
            meetings.append({
                "type": "三会",
                "branches": [a, b, c],
                "pillars": p_list[:3],
                "result": f"会{wx}局",
            })
            evidence.append(f"{a}{b}{c}三会{wx}局")

    # --- 三刑（寅巳申 / 丑未戌） ---
    for xing_group in SAN_XING_WUEN + SAN_XING_SHISHI:
        present_b = [br for br in xing_group if br in branch_set]
        if len(present_b) >= 2:
            label = "无恩之刑" if xing_group in SAN_XING_WUEN else "恃势之刑"
            p_list = []
            for pos, br in branches:
                if br in present_b:
                    p_list.append(pos)
            full = len(present_b) == 3
            punishments.append({
                "type": label,
                "branches": present_b,
                "pillars": p_list,
                "full": full,
            })
            evidence.append(f"{''.join(present_b)}{label}（{'三刑全' if full else '部分'}）")

    # --- 自刑 ---
    from collections import Counter
    branch_counts = Counter(branch_list)
    for zx in ZI_XING:
        if branch_counts.get(zx, 0) >= 2:
            p_list = [pos for pos, br in branches if br == zx]
            punishments.append({
                "type": "自刑",
                "branches": [zx, zx],
                "pillars": p_list,
            })
            evidence.append(f"{zx}见{zx}自刑")

    return {
        "combinations": combinations,
        "clashes": clashes,
        "harms": harms,
        "punishments": punishments,
        "meetings": meetings,
        "evidence": evidence,
    }


# ========================== 天干五合 ==========================

# 天干五合：{frozenset({A,B}): 合化五行}
TIAN_GAN_HE: Dict[frozenset, str] = {
    frozenset(("甲", "己")): "土",
    frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水",
    frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}


def analyze_tiangan_he(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    """识别四柱天干五合（不判合化）。"""
    pillars = chart.get("pillars") or {}
    gans: List[Tuple[str, str]] = []
    for pos in ("year", "month", "day", "hour"):
        g = (pillars.get(pos) or {}).get("stem") or ""
        if g:
            gans.append((pos, g))

    out: List[Dict[str, Any]] = []
    for i in range(len(gans)):
        for j in range(i + 1, len(gans)):
            p1, g1 = gans[i]
            p2, g2 = gans[j]
            pair = frozenset((g1, g2))
            if pair in TIAN_GAN_HE:
                out.append({
                    "type": "天干五合",
                    "gans": [g1, g2],
                    "pillars": [p1, p2],
                    "result": f"合化{TIAN_GAN_HE[pair]}",
                })
    return out


# ========================== 合化成功判定 ==========================

def analyze_combination_transformation(chart: Dict[str, Any], relations: Dict[str, Any]) -> Dict[str, Any]:
    """判断已识别的合（六合/三合/天干五合）是否真正合化。

    合化条件（保守版）：
    1. 月令支持合化神（合化神在月令藏干中出现）→ +关键
    2. 合化神透干（四柱天干至少一个等于合化神五行）→ +
    3. 无被冲（合的两支不被冲克）→ 必要

    返回
    ----
    {
        "checked": [
            {
                "type": str,
                "members": [str],
                "result_wx": str,
                "is_transformed": True/False/None,
                "confidence": "high/medium/low",
                "evidence": [str],
            }
        ],
        "summary_note": str,
    }
    """
    from .bazi_rules import GAN_WUXING, ZHI_CANG_GAN

    pillars = chart.get("pillars") or {}
    month_zhi = (pillars.get("month") or {}).get("branch") or ""
    month_cang = [g for g, _ in ZHI_CANG_GAN.get(month_zhi, [])]
    month_cang_wx = {GAN_WUXING.get(g) for g in month_cang if g in GAN_WUXING}

    visible_gan_wx = set()
    for pos in ("year", "month", "day", "hour"):
        g = (pillars.get(pos) or {}).get("stem") or ""
        if g in GAN_WUXING:
            visible_gan_wx.add(GAN_WUXING[g])

    chong_pairs = {frozenset(c["branches"]) for c in (relations.get("clashes") or [])}

    checked: List[Dict[str, Any]] = []

    # 候选：六合 + 三合（来自 relations.combinations）+ 天干五合（独立扫）
    items: List[Dict[str, Any]] = []
    for c in (relations.get("combinations") or []):
        if c.get("type") in ("六合", "三合"):
            items.append({
                "type": c["type"],
                "members": list(c.get("branches") or []),
                "result_wx": (c.get("result") or "").replace("合化", "").replace("半合", "").strip("局"),
                "result_raw": c.get("result", ""),
                "kind": "branch",
            })
    for tg in analyze_tiangan_he(chart):
        items.append({
            "type": tg["type"],
            "members": list(tg.get("gans") or []),
            "result_wx": (tg.get("result") or "").replace("合化", ""),
            "result_raw": tg.get("result", ""),
            "kind": "gan",
        })

    for item in items:
        ev: List[str] = []
        score = 0  # 内部打分
        result_wx = item["result_wx"]
        # 处理 "火/土" 这种二元结果
        target_wx_set = set(result_wx.replace("局", "").split("/")) if result_wx else set()

        # 1. 月令支持？
        month_support = bool(target_wx_set & month_cang_wx)
        if month_support:
            score += 2
            ev.append(f"月令{month_zhi}藏干含合化神五行 ✓")
        else:
            ev.append(f"月令{month_zhi}藏干不含合化神五行 ✗")

        # 2. 透干？
        gan_support = bool(target_wx_set & visible_gan_wx)
        if gan_support:
            score += 1
            ev.append(f"四柱天干见合化神五行 ✓")
        else:
            ev.append(f"四柱天干未透合化神五行 ✗")

        # 3. 是否被冲（仅地支）
        broken = False
        if item["kind"] == "branch" and len(item["members"]) >= 2:
            members_pair = frozenset(item["members"][:2])
            for cp in chong_pairs:
                if members_pair & cp:
                    broken = True
                    ev.append(f"合的成员被冲（{tuple(cp)}），破合 ✗")
                    break

        is_transformed = None
        confidence = "low"
        if broken:
            is_transformed = False
            confidence = "medium"
        elif score >= 3:
            is_transformed = True
            confidence = "high"
        elif score == 2:
            is_transformed = True
            confidence = "medium"
        elif score == 1:
            is_transformed = False
            confidence = "medium"
            ev.append("仅满足部分条件，倾向合而不化")
        else:
            is_transformed = False
            confidence = "low"
            ev.append("条件不足，仅作合论，不作化论")

        checked.append({
            "type": item["type"],
            "members": item["members"],
            "result": item["result_raw"],
            "is_transformed": is_transformed,
            "confidence": confidence,
            "evidence": ev,
        })

    transformed_count = sum(1 for c in checked if c["is_transformed"] is True)
    if transformed_count > 0:
        summary = f"识别 {len(checked)} 项合，其中 {transformed_count} 项判定为真合化（参考用）。"
    elif checked:
        summary = f"识别 {len(checked)} 项合，均为合而不化或破合。"
    else:
        summary = "未识别到合的关系。"

    return {"checked": checked, "summary_note": summary}


# ========================== 流年/大运动态交互 ==========================

def analyze_dynamic_relations(
    chart: Dict[str, Any],
    dayun_ganzhi: str = "",
    liunian_ganzhi: str = "",
) -> Dict[str, Any]:
    """计算大运 / 流年与命局四柱地支的合冲关系。

    参数
    ----
    dayun_ganzhi: 当前大运（2 字干支，如 "庚午"）
    liunian_ganzhi: 当前流年（2 字干支，如 "丙午"）

    返回
    ----
    {
        "dayun": {
            "ganzhi": str,
            "branch": str,
            "interactions": [{"type", "with_pillar", "with_branch", "note"}],
        },
        "liunian": {同上},
        "dayun_liunian": [...],   # 大运 vs 流年自身的关系
        "evidence": [str],
    }
    """
    pillars = chart.get("pillars") or {}
    natal_branches: List[Tuple[str, str]] = []
    for pos in ("year", "month", "day", "hour"):
        b = (pillars.get(pos) or {}).get("branch") or ""
        if b:
            natal_branches.append((pos, b))

    def _scan_against_natal(target_branch: str) -> List[Dict[str, Any]]:
        """扫描 target_branch 与四柱各支的关系。"""
        out: List[Dict[str, Any]] = []
        if not target_branch:
            return out
        for pos, b in natal_branches:
            pair = frozenset((target_branch, b))
            if target_branch == b:
                continue
            if pair in LIU_CHONG:
                out.append({"type": "六冲", "with_pillar": pos, "with_branch": b,
                            "note": f"动支{target_branch}与{pos}支{b}六冲"})
            elif pair in LIU_HE:
                out.append({"type": "六合", "with_pillar": pos, "with_branch": b,
                            "result": f"合化{LIU_HE[pair]}",
                            "note": f"动支{target_branch}与{pos}支{b}六合"})
            elif pair in LIU_HAI:
                out.append({"type": "六害", "with_pillar": pos, "with_branch": b,
                            "note": f"动支{target_branch}与{pos}支{b}六害"})
            elif pair in XING_PAIR:
                out.append({"type": "无礼之刑", "with_pillar": pos, "with_branch": b,
                            "note": f"动支{target_branch}与{pos}支{b}互刑"})
        # 三合检测：动支 + 至少一个原局支构成半合，两个构成全合
        for a, bb, c, wx in SAN_HE:
            if target_branch in (a, bb, c):
                others = {a, bb, c} - {target_branch}
                natal_set = {b for _, b in natal_branches}
                hits = others & natal_set
                if len(hits) >= 2:
                    out.append({"type": "三合", "with_branch": "+".join(sorted(hits)),
                                "result": f"合化{wx}局", "with_pillar": "natal",
                                "note": f"动支{target_branch}与原局{'+'.join(sorted(hits))}三合化{wx}"})
                elif len(hits) == 1:
                    h = next(iter(hits))
                    # 找对应柱
                    pp = next((p for p, b in natal_branches if b == h), "natal")
                    out.append({"type": "半合", "with_branch": h, "with_pillar": pp,
                                "result": f"半合{wx}", "note": f"动支{target_branch}与{pp}支{h}半合{wx}"})
        # 自刑
        if target_branch in ZI_XING:
            for pos, b in natal_branches:
                if b == target_branch:
                    out.append({"type": "自刑", "with_pillar": pos, "with_branch": b,
                                "note": f"动支{target_branch}遇{pos}支{b}自刑"})
                    break
        return out

    dy_branch = dayun_ganzhi[1] if len(dayun_ganzhi) >= 2 else ""
    ln_branch = liunian_ganzhi[1] if len(liunian_ganzhi) >= 2 else ""

    dy_inter = _scan_against_natal(dy_branch) if dy_branch else []
    ln_inter = _scan_against_natal(ln_branch) if ln_branch else []

    # 大运 vs 流年自身
    dy_ln: List[Dict[str, Any]] = []
    if dy_branch and ln_branch and dy_branch != ln_branch:
        pair = frozenset((dy_branch, ln_branch))
        if pair in LIU_CHONG:
            dy_ln.append({"type": "六冲", "between": [dy_branch, ln_branch],
                          "note": "大运与流年六冲"})
        elif pair in LIU_HE:
            dy_ln.append({"type": "六合", "between": [dy_branch, ln_branch],
                          "result": f"合化{LIU_HE[pair]}", "note": "大运与流年六合"})

    evidence: List[str] = []
    for x in dy_inter:
        evidence.append(f"[大运] {x['note']}")
    for x in ln_inter:
        evidence.append(f"[流年] {x['note']}")
    for x in dy_ln:
        evidence.append(f"[大运↔流年] {x['note']}")

    return {
        "dayun": {"ganzhi": dayun_ganzhi, "branch": dy_branch, "interactions": dy_inter},
        "liunian": {"ganzhi": liunian_ganzhi, "branch": ln_branch, "interactions": ln_inter},
        "dayun_liunian": dy_ln,
        "evidence": evidence,
    }
