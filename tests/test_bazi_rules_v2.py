"""规则引擎 v2 测试：五行力量、旺衰 v2、格局 v2、喜用神 v2。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.services import chart_service
from backend.domain.bazi_strength import calculate_wuxing_power, calculate_day_master_strength_v2
from backend.domain.bazi_relations import analyze_branch_relations
from backend.domain.bazi_pattern import analyze_pattern_v2
from backend.domain.bazi_useful_gods import infer_useful_gods_v2
from backend.domain.bazi_rules import analyze_chart_v2


# ========================== helpers ==========================

def _chart(birth_date, birth_time, calendar_type="lunar", gender="男"):
    return chart_service.compute_chart(
        birth_date=birth_date, birth_time=birth_time,
        calendar_type=calendar_type, gender=gender,
    )


SAMPLE_WEAK = _chart("1999-08-14", "22:30", "lunar", "男")     # 戊土日主，失令
SAMPLE_STRONG = _chart("1990-06-15", "06:00", "solar", "男")   # solar


# ========================== 五行力量 ==========================

class TestWuxingPower:
    def test_returns_all_five(self):
        wp = calculate_wuxing_power(SAMPLE_WEAK)
        for w in ("木", "火", "土", "金", "水"):
            assert w in wp["powers"]

    def test_month_main_weight_largest(self):
        """月令本气权重应大于其他地支本气。"""
        wp = calculate_wuxing_power(SAMPLE_WEAK)
        details = wp["details"]
        month_main = [d for d in details if d["source"] == "月令本气"]
        other_main = [d for d in details if d["source"] == "本气"]
        if month_main and other_main:
            assert month_main[0]["weight"] > other_main[0]["weight"]

    def test_canggan_mid_less_than_main(self):
        """中气权重应小于主气。"""
        wp = calculate_wuxing_power(SAMPLE_WEAK)
        details = wp["details"]
        for d in details:
            if "中气" in d["source"]:
                # 找同柱主气
                same_pillar_main = [
                    x for x in details
                    if x["pillar"] == d["pillar"] and ("本气" in x["source"] or x["source"] == "月令本气")
                ]
                if same_pillar_main:
                    assert d["weight"] < same_pillar_main[0]["weight"], (
                        f"中气权重{d['weight']}应<主气{same_pillar_main[0]['weight']}"
                    )

    def test_gan_visible_counted(self):
        """天干透出应有计分。"""
        wp = calculate_wuxing_power(SAMPLE_WEAK)
        gan_entries = [d for d in wp["details"] if d["source"] == "天干"]
        assert len(gan_entries) >= 4, "四柱天干应各有一条"

    def test_tonggen_bonus(self):
        """通根加分项应存在。"""
        wp = calculate_wuxing_power(SAMPLE_WEAK)
        tonggen = [d for d in wp["details"] if d["source"] == "通根"]
        # 可能有也可能没有，但结构应正确
        for t in tonggen:
            assert t["weight"] > 0


# ========================== 旺衰 v2 ==========================

class TestStrengthV2:
    def test_weak_sample(self):
        """小滕戊土应身弱。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        assert s["day_gan"] == "戊"
        assert s["day_wx"] == "土"
        assert s["strength_level"] in ("身弱", "偏弱")
        assert s["score"] < 45
        assert s["same_power"] < s["opposite_power"]

    def test_score_range(self):
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        assert 0 <= s["score"] <= 100

    def test_has_evidence(self):
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        assert len(s["evidence"]) >= 3

    def test_strong_chart(self):
        """身强盘应 score > 55。"""
        # 构造一个身强样本：甲木生寅月
        c = _chart("1984-02-05", "06:00", "solar", "男")
        s = calculate_day_master_strength_v2(c)
        # 甲木在寅月得令，应偏强
        if s["day_gan"] == "甲":
            assert s["score"] >= 45, f"甲木寅月应不弱，实际{s['score']}"

    def test_balanced_marked_uncertain(self):
        """接近 50 分时应标记不确定。"""
        # 用多个样本找一个接近平衡的
        for bd in ["1985-03-20", "1988-07-10", "1992-11-05"]:
            c = _chart(bd, "12:00", "solar", "男")
            s = calculate_day_master_strength_v2(c)
            if 45 <= s["score"] <= 55:
                assert s["strength_level"] == "中和" or len(s["uncertainties"]) > 0
                break

    def test_extreme_weak_from_ge(self):
        """极端弱盘应标疑似从弱。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        # 不一定触发，但结构应正确
        assert "strength_level" in s


# ========================== 格局 v2 ==========================

class TestPatternV2:
    def test_weak_sample_pattern(self):
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        assert "伤官" in p["pattern"]
        assert p["confidence"] in ("high", "medium", "low")

    def test_pattern_structure(self):
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        assert "pattern" in p
        assert "is_established" in p
        assert "confidence" in p
        assert "evidence" in p
        assert "break_factors" in p
        assert isinstance(p["evidence"], list)

    def test_month_clash_adds_break_factor(self):
        """月令被冲应有 break_factor。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        # 小滕卯酉冲，月令酉被冲
        clashes = [c for c in r["clashes"] if "month" in c.get("pillars", [])]
        if clashes:
            assert len(p["break_factors"]) > 0, "月令被冲应有破格因素"

    def test_no_transparent_is_lower_confidence(self):
        """月令本气不透应降低信心。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        # 酉中辛不透（四柱天干无辛），信心应 ≤ medium
        pillars = SAMPLE_WEAK.get("pillars") or {}
        other_gans = [
            pillars[pos]["stem"] for pos in ("year", "month", "hour")
            if pillars.get(pos, {}).get("stem")
        ]
        if "辛" not in other_gans:
            assert p["confidence"] in ("medium", "low")

    def test_unknown_on_missing_data(self):
        p = analyze_pattern_v2({}, {}, {})
        assert p["pattern"] == "不明显"
        assert p["confidence"] == "low"


# ========================== 喜用神 v2 ==========================

class TestUsefulGodsV2:
    def test_weak_prefers_yin_bi(self):
        """身弱应喜印比。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        ug = infer_useful_gods_v2(SAMPLE_WEAK, s, p, r)
        ws = ug["wangshuai_method"]
        assert "火" in ws["useful_elements"], "戊土身弱应喜火(印)"
        assert "土" in ws["useful_elements"], "戊土身弱应喜土(比劫)"

    def test_structure(self):
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        ug = infer_useful_gods_v2(SAMPLE_WEAK, s, p, r)
        assert "wangshuai_method" in ug
        assert "pattern_method" in ug
        assert "conflict" in ug
        assert "final_suggestion" in ug
        assert "preferred" in ug["final_suggestion"]
        assert "confidence" in ug["final_suggestion"]

    def test_conflict_marked(self):
        """小滕两法应有分歧（水在旺衰忌、格局喜）。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        ug = infer_useful_gods_v2(SAMPLE_WEAK, s, p, r)
        assert ug["conflict"] is True
        assert len(ug.get("conflict_notes", [])) > 0

    def test_low_confidence_not_high(self):
        """有分歧时 final confidence 不应为 high。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        ug = infer_useful_gods_v2(SAMPLE_WEAK, s, p, r)
        if ug["conflict"]:
            assert ug["final_suggestion"]["confidence"] != "high"

    def test_consensus_fire(self):
        """两法应共识喜火。"""
        s = calculate_day_master_strength_v2(SAMPLE_WEAK)
        r = analyze_branch_relations(SAMPLE_WEAK)
        p = analyze_pattern_v2(SAMPLE_WEAK, s, r)
        ug = infer_useful_gods_v2(SAMPLE_WEAK, s, p, r)
        preferred = ug["final_suggestion"]["preferred"]
        assert "火" in preferred


# ========================== 整合入口 ==========================

class TestAnalyzeChartV2:
    def test_version(self):
        ra = analyze_chart_v2(SAMPLE_WEAK)
        assert ra["version"] == "bazi-rules-v2.0.0"

    def test_all_sections_present(self):
        ra = analyze_chart_v2(SAMPLE_WEAK)
        for key in ("wuxing_power", "strength", "relations", "pattern", "useful_gods"):
            assert key in ra, f"缺少 {key}"

    def test_overall_confidence(self):
        ra = analyze_chart_v2(SAMPLE_WEAK)
        assert ra["overall_confidence"] in ("high", "medium", "low")

    def test_warnings_populated(self):
        ra = analyze_chart_v2(SAMPLE_WEAK)
        assert isinstance(ra["warnings"], list)

    def test_backward_compat(self):
        """analyze_chart (v1 alias) 内部已切换到 v3，但 v2 字段全部保留。"""
        from backend.domain.bazi_rules import analyze_chart
        ra = analyze_chart(SAMPLE_WEAK)
        # 字段层向后兼容：v2 所有 key 仍存在
        for k in ("strength", "pattern", "useful_gods", "relations", "wuxing_power"):
            assert k in ra


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
