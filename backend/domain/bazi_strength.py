"""五行力量模型 & 日主旺衰判断 v2。

权重体系：
- 月令本气：30
- 其他地支本气：12
- 中气：6
- 余气：3
- 天干透出：8
- 同类通根额外加权：5

所有权重集中在 WEIGHT_* 常量中，方便后续调参。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .bazi_rules import (
    GAN_WUXING,
    GAN_POLARITY,
    TIAN_GAN,
    ZHI_CANG_GAN,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_SHENG_WO,
    WUXING_KE_WO,
)

# ========================== 权重常量 ==========================

WEIGHT_MONTH_MAIN = 30    # 月令本气
WEIGHT_MONTH_MID = 15     # 月令中气
WEIGHT_MONTH_SUB = 7      # 月令余气
WEIGHT_OTHER_MAIN = 12    # 非月令地支本气
WEIGHT_OTHER_MID = 6      # 非月令地支中气
WEIGHT_OTHER_SUB = 3      # 非月令地支余气
WEIGHT_GAN_VISIBLE = 8    # 天干透出
WEIGHT_TONGGEN_BONUS = 5  # 天干在地支有同五行根气，额外加权

WUXING_FIVE = ("木", "火", "土", "金", "水")


# ========================== 五行力量计算 ==========================

def _cang_weights(is_month: bool) -> Tuple[float, float, float]:
    """返回 (主气, 中气, 余气) 权重。"""
    if is_month:
        return WEIGHT_MONTH_MAIN, WEIGHT_MONTH_MID, WEIGHT_MONTH_SUB
    return WEIGHT_OTHER_MAIN, WEIGHT_OTHER_MID, WEIGHT_OTHER_SUB


def calculate_wuxing_power(chart: Dict[str, Any]) -> Dict[str, Any]:
    """计算五行加权力量。

    返回
    ----
    {
        "powers": {"木": float, ...},
        "details": [{"source", "pillar", "char", "element", "weight", "reason"}, ...],
    }
    """
    pillars = chart.get("pillars") or {}
    powers: Dict[str, float] = {w: 0.0 for w in WUXING_FIVE}
    details: List[Dict[str, Any]] = []

    # 收集所有天干（用于通根检测）
    all_gans: Dict[str, str] = {}  # {pillar_key: gan}
    for pos in ("year", "month", "day", "hour"):
        cell = pillars.get(pos) or {}
        g = cell.get("stem") or ""
        if g and g in GAN_WUXING:
            all_gans[pos] = g

    # --- 天干力量 ---
    for pos, g in all_gans.items():
        wx = GAN_WUXING[g]
        w = WEIGHT_GAN_VISIBLE
        powers[wx] += w
        details.append({
            "source": "天干",
            "pillar": pos,
            "char": g,
            "element": wx,
            "weight": w,
            "reason": f"{pos}干{g}透出",
        })

    # --- 地支藏干力量 ---
    for pos in ("year", "month", "day", "hour"):
        cell = pillars.get(pos) or {}
        zhi = cell.get("branch") or ""
        if not zhi or zhi not in ZHI_CANG_GAN:
            continue
        is_month = (pos == "month")
        cg_list = ZHI_CANG_GAN[zhi]
        wt_main, wt_mid, wt_sub = _cang_weights(is_month)

        for idx, (cg, _original_weight) in enumerate(cg_list):
            cg_wx = GAN_WUXING.get(cg, "")
            if not cg_wx:
                continue
            # 按序分配权重：idx=0 主气, idx=1 中气, idx=2 余气
            if idx == 0:
                w = wt_main
                label = "月令本气" if is_month else "本气"
            elif idx == 1:
                w = wt_mid
                label = "月令中气" if is_month else "中气"
            else:
                w = wt_sub
                label = "月令余气" if is_month else "余气"

            powers[cg_wx] += w
            details.append({
                "source": label,
                "pillar": pos,
                "char": zhi,
                "element": cg_wx,
                "weight": w,
                "reason": f"{pos}支{zhi}藏{cg}({cg_wx}) {label}",
            })

    # --- 通根加权 ---
    # 天干在地支中有同五行藏干 → 额外加权
    gan_wuxing_set = {pos: GAN_WUXING[g] for pos, g in all_gans.items()}
    for pos in ("year", "month", "day", "hour"):
        cell = pillars.get(pos) or {}
        zhi = cell.get("branch") or ""
        if not zhi or zhi not in ZHI_CANG_GAN:
            continue
        for cg, _ in ZHI_CANG_GAN[zhi]:
            cg_wx = GAN_WUXING.get(cg, "")
            if not cg_wx:
                continue
            # 检查是否有天干与此藏干同五行
            for gpos, gwx in gan_wuxing_set.items():
                if gwx == cg_wx and gpos != pos:
                    # 通根加分（每对只算一次）
                    bonus_key = f"tonggen_{gpos}_{pos}_{cg_wx}"
                    # 简单去重：只在地支侧加分
                    if not any(d.get("_key") == bonus_key for d in details):
                        powers[cg_wx] += WEIGHT_TONGGEN_BONUS
                        details.append({
                            "source": "通根",
                            "pillar": pos,
                            "char": f"{all_gans[gpos]}→{zhi}",
                            "element": cg_wx,
                            "weight": WEIGHT_TONGGEN_BONUS,
                            "reason": f"{gpos}干{all_gans[gpos]}({cg_wx})通根于{pos}支{zhi}藏{cg}",
                            "_key": bonus_key,
                        })

    # 清理内部 key
    for d in details:
        d.pop("_key", None)

    return {
        "powers": {w: round(powers[w], 1) for w in WUXING_FIVE},
        "details": details,
    }


def adjust_power_for_relations(powers: Dict[str, float], chart: Dict[str, Any]) -> Dict[str, float]:
    """根据合冲关系调整五行力量。

    - 被冲的地支：其藏干五行力量 -40%
    - 三合/三会成局：合化五行 +15%
    """
    from .bazi_relations import analyze_branch_relations, LIU_CHONG, SAN_HE, SAN_HUI
    from .bazi_rules import ZHI_CANG_GAN, GAN_WUXING

    pillars = chart.get("pillars") or {}
    adjusted = dict(powers)

    # 收集地支
    branches = []
    for pos in ("year", "month", "day", "hour"):
        b = (pillars.get(pos) or {}).get("branch") or ""
        if b:
            branches.append((pos, b))

    branch_set = {b for _, b in branches}

    # 冲减力：被冲的地支藏干力量削弱
    CLASH_PENALTY = 0.4
    for i in range(len(branches)):
        for j in range(i + 1, len(branches)):
            _, b1 = branches[i]
            _, b2 = branches[j]
            if frozenset((b1, b2)) in LIU_CHONG:
                # 双方都被削弱
                for b in (b1, b2):
                    for cg, _ in ZHI_CANG_GAN.get(b, []):
                        wx = GAN_WUXING.get(cg, "")
                        if wx:
                            # 估算该藏干贡献并扣除
                            penalty = CLASH_PENALTY * 5.0  # 约扣 2 分
                            adjusted[wx] = max(0, adjusted.get(wx, 0) - penalty)

    # 三合/三会成局加力
    COMBO_BONUS = 0.15
    for a, b, c, wx in SAN_HE + SAN_HUI:
        if {a, b, c} <= branch_set:
            bonus = adjusted.get(wx, 0) * COMBO_BONUS
            adjusted[wx] = adjusted.get(wx, 0) + bonus

    return {w: round(adjusted.get(w, 0), 1) for w in WUXING_FIVE}


# ========================== 日主旺衰判断 v2 ==========================

def _relation_category(day_wx: str, target_wx: str) -> str:
    """目标五行相对于日主的关系类别。"""
    if target_wx == day_wx:
        return "比劫"
    if target_wx == WUXING_SHENG_WO.get(day_wx):
        return "印星"
    if target_wx == WUXING_SHENG.get(day_wx):
        return "食伤"
    if target_wx == WUXING_KE.get(day_wx):
        return "财星"
    if target_wx == WUXING_KE_WO.get(day_wx):
        return "官杀"
    return "未知"


def calculate_day_master_strength_v2(chart: Dict[str, Any]) -> Dict[str, Any]:
    """基于五行加权力量模型判断日主旺衰。

    返回
    ----
    {
        "day_gan", "day_wx",
        "strength_level": "身强/偏强/中和/偏弱/身弱/疑似从强/疑似从弱/不确定",
        "score": 0-100,
        "same_power", "opposite_power",
        "season_score", "root_score", "support_score",
        "evidence", "uncertainties",
    }
    """
    pillars = chart.get("pillars") or {}
    day_cell = pillars.get("day") or {}
    day_gan = day_cell.get("stem") or ""
    if not day_gan or day_gan not in GAN_WUXING:
        return {
            "day_gan": day_gan, "day_wx": "",
            "strength_level": "不确定", "score": 50,
            "same_power": 0, "opposite_power": 0,
            "season_score": 0, "root_score": 0, "support_score": 0,
            "evidence": [], "uncertainties": ["日主天干缺失"],
        }

    day_wx = GAN_WUXING[day_gan]

    # 计算五行力量（含合冲修正）
    wp = calculate_wuxing_power(chart)
    powers = adjust_power_for_relations(wp["powers"], chart)

    evidence: List[str] = []
    uncertainties: List[str] = []

    # --- 同类力量（比劫 + 印星） ---
    bijie_wx = day_wx
    yinxing_wx = WUXING_SHENG_WO[day_wx]
    same_power = powers.get(bijie_wx, 0) + powers.get(yinxing_wx, 0)

    # --- 异类力量（食伤 + 财星 + 官杀） ---
    shishang_wx = WUXING_SHENG[day_wx]
    caixing_wx = WUXING_KE[day_wx]
    guansha_wx = WUXING_KE_WO[day_wx]
    opposite_power = powers.get(shishang_wx, 0) + powers.get(caixing_wx, 0) + powers.get(guansha_wx, 0)

    evidence.append(f"同类({bijie_wx}+{yinxing_wx})={same_power:.1f}  异类({shishang_wx}+{caixing_wx}+{guansha_wx})={opposite_power:.1f}")

    total = same_power + opposite_power
    if total == 0:
        return {
            "day_gan": day_gan, "day_wx": day_wx,
            "strength_level": "不确定", "score": 50,
            "same_power": 0, "opposite_power": 0,
            "season_score": 0, "root_score": 0, "support_score": 0,
            "evidence": evidence, "uncertainties": ["五行力量为零"],
        }

    # 基准分：同类占比 × 100
    ratio = same_power / total
    raw_score = ratio * 100

    # --- 季节分（得令/失令） ---
    month_cell = pillars.get("month") or {}
    month_zhi = month_cell.get("branch") or ""
    season_score = 0.0
    if month_zhi and month_zhi in ZHI_CANG_GAN:
        main_cg = ZHI_CANG_GAN[month_zhi][0][0]
        main_wx = GAN_WUXING.get(main_cg, "")
        if main_wx == day_wx:
            season_score = 8.0
            evidence.append(f"得令：月令{month_zhi}本气{main_cg}({main_wx})与日主同行 +{season_score}")
        elif main_wx == yinxing_wx:
            season_score = 5.0
            evidence.append(f"得令(生)：月令{month_zhi}本气{main_cg}({main_wx})生日主 +{season_score}")
        else:
            season_score = -3.0
            evidence.append(f"失令：月令{month_zhi}本气{main_cg}({main_wx})不助日主 {season_score}")

    # --- 通根分 ---
    root_score = 0.0
    day_zhi = (pillars.get("day") or {}).get("branch") or ""
    if day_zhi and day_zhi in ZHI_CANG_GAN:
        for cg, _ in ZHI_CANG_GAN[day_zhi]:
            if GAN_WUXING.get(cg, "") == day_wx:
                root_score = 6.0
                evidence.append(f"坐根：日支{day_zhi}藏{cg}({day_wx}) +{root_score}")
                break
        if root_score == 0:
            for cg, _ in ZHI_CANG_GAN[day_zhi]:
                if GAN_WUXING.get(cg, "") == yinxing_wx:
                    root_score = 3.0
                    evidence.append(f"坐印根：日支{day_zhi}藏{cg}({yinxing_wx}) +{root_score}")
                    break

    # --- 天干帮扶分 ---
    support_score = 0.0
    for pos in ("year", "month", "hour"):
        g = (pillars.get(pos) or {}).get("stem") or ""
        if not g or g not in GAN_WUXING:
            continue
        gwx = GAN_WUXING[g]
        cat = _relation_category(day_wx, gwx)
        if cat in ("比劫", "印星"):
            support_score += 3.0
            evidence.append(f"帮扶：{pos}干{g}({gwx}/{cat}) +3")
        else:
            support_score -= 2.0
            evidence.append(f"耗泄：{pos}干{g}({gwx}/{cat}) -2")

    # --- 综合 ---
    score = raw_score + season_score + root_score + support_score
    score = max(0.0, min(100.0, score))

    evidence.append(f"综合：基准={raw_score:.1f} + 季节={season_score} + 通根={root_score} + 帮扶={support_score:.1f} → {score:.1f}")

    # --- 定级 ---
    if score >= 75:
        if opposite_power <= total * 0.1:
            level = "疑似从强"
            uncertainties.append("异类力量极弱，疑似从强格，需人工确认")
        else:
            level = "身强"
    elif score >= 60:
        level = "偏强"
    elif score >= 55:
        level = "中和"
        uncertainties.append("旺衰接近平衡，两法结论可能不同")
    elif score >= 45:
        level = "中和"
        uncertainties.append("旺衰接近平衡，建议结合实际验证")
    elif score >= 35:
        level = "偏弱"
    elif score >= 20:
        level = "身弱"
    else:
        if same_power <= total * 0.1:
            level = "疑似从弱"
            uncertainties.append("同类力量极弱，疑似从弱格，需人工确认")
        else:
            level = "身弱"

    return {
        "day_gan": day_gan,
        "day_wx": day_wx,
        "strength_level": level,
        "score": round(score, 1),
        "same_power": round(same_power, 1),
        "opposite_power": round(opposite_power, 1),
        "season_score": round(season_score, 1),
        "root_score": round(root_score, 1),
        "support_score": round(support_score, 1),
        "evidence": evidence,
        "uncertainties": uncertainties,
    }
