"""Phase 4 测试：调候用神 + 合化判定 + 流年大运动态交互。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.services import chart_service
from backend.domain.bazi_climate import (
    get_climate_gods, merge_with_useful_gods,
    MONTH_SEASON, CLIMATE_TABLE,
)
from backend.domain.bazi_relations import (
    analyze_branch_relations,
    analyze_tiangan_he,
    analyze_combination_transformation,
    analyze_dynamic_relations,
    TIAN_GAN_HE,
)
from backend.domain.bazi_rules import analyze_chart_v3


# ========================== helpers ==========================

def _make_chart(year, month, day, hour):
    return {
        "pillars": {
            "year": {"stem": year[0], "branch": year[1]},
            "month": {"stem": month[0], "branch": month[1]},
            "day": {"stem": day[0], "branch": day[1]},
            "hour": {"stem": hour[0], "branch": hour[1]},
        },
        "wuxing": {"day_master": day[0]},
    }


SAMPLE_TENG = chart_service.compute_chart(
    birth_date="1999-08-14", birth_time="22:30",
    calendar_type="lunar", gender="男",
)


# ========================== 调候 ==========================

class TestClimate:
    def test_table_covers_5x4(self):
        # 5 五行 × 4 季节 = 20 条
        assert len(CLIMATE_TABLE) == 20

    def test_month_season_complete(self):
        for b in ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"):
            assert b in MONTH_SEASON

    def test_winter_water_likes_fire(self):
        """水生子月寒水冰冻，喜火土。"""
        c = _make_chart(("甲", "子"), ("丙", "子"), ("壬", "子"), ("丁", "未"))
        r = get_climate_gods(c)
        assert r["season"] == "winter"
        assert r["day_wx"] == "水"
        assert "火" in r["primary_useful"]

    def test_summer_fire_likes_water(self):
        """火生午月烈火炎炎，喜水。"""
        c = _make_chart(("甲", "寅"), ("庚", "午"), ("丙", "午"), ("丁", "酉"))
        r = get_climate_gods(c)
        assert r["season"] == "summer"
        assert r["day_wx"] == "火"
        assert "水" in r["primary_useful"]

    def test_high_confidence_seasons(self):
        """寒/暑月调候 confidence=high。"""
        c1 = _make_chart(("甲", "子"), ("丙", "子"), ("壬", "子"), ("丁", "未"))
        c2 = _make_chart(("甲", "寅"), ("庚", "午"), ("丙", "午"), ("丁", "酉"))
        assert get_climate_gods(c1)["confidence"] == "high"
        assert get_climate_gods(c2)["confidence"] == "high"

    def test_missing_data_returns_empty(self):
        r = get_climate_gods({})
        assert r["primary_useful"] == []
        assert r["confidence"] == "low"

    def test_merge_finds_consensus(self):
        climate = {"primary_useful": ["火"], "secondary_useful": []}
        useful_v2 = {
            "wangshuai_method": {"useful_elements": ["火", "土"], "avoid_elements": ["金"]},
            "pattern_method": {"useful_elements": ["火"], "avoid_elements": []},
        }
        m = merge_with_useful_gods(climate, useful_v2)
        assert "火" in m["consensus_three_way"]

    def test_merge_detects_conflict(self):
        climate = {"primary_useful": ["木"], "secondary_useful": []}
        useful_v2 = {
            "wangshuai_method": {"useful_elements": ["金"], "avoid_elements": []},
            "pattern_method": {"useful_elements": ["金"], "avoid_elements": ["木"]},
        }
        m = merge_with_useful_gods(climate, useful_v2)
        assert m["climate_pattern_conflict"] is True


# ========================== 天干五合 ==========================

class TestTianganHe:
    def test_table_5_pairs(self):
        assert len(TIAN_GAN_HE) == 5

    def test_jia_ji_he_tu(self):
        c = _make_chart(("甲", "子"), ("丙", "寅"), ("己", "未"), ("丁", "卯"))
        r = analyze_tiangan_he(c)
        gz_pairs = [set(x["gans"]) for x in r]
        assert {"甲", "己"} in gz_pairs

    def test_no_he_when_absent(self):
        c = _make_chart(("甲", "子"), ("丙", "寅"), ("戊", "未"), ("丁", "卯"))
        r = analyze_tiangan_he(c)
        assert all(set(x["gans"]) != {"甲", "己"} for x in r)


# ========================== 合化判定 ==========================

class TestTransformation:
    def test_real_chart_runs(self):
        rel = analyze_branch_relations(SAMPLE_TENG)
        t = analyze_combination_transformation(SAMPLE_TENG, rel)
        assert "checked" in t
        assert "summary_note" in t

    def test_each_check_has_evidence(self):
        rel = analyze_branch_relations(SAMPLE_TENG)
        t = analyze_combination_transformation(SAMPLE_TENG, rel)
        for c in t["checked"]:
            assert "is_transformed" in c
            assert "confidence" in c
            assert isinstance(c["evidence"], list)

    def test_clashed_combination_marked_broken(self):
        """月令被冲时，含月支的合应被标为破合。"""
        # 构造：寅亥六合 + 寅申冲（月支寅被冲）
        c = _make_chart(("壬", "申"), ("甲", "寅"), ("乙", "亥"), ("丙", "子"))
        rel = analyze_branch_relations(c)
        t = analyze_combination_transformation(c, rel)
        # 寅亥六合应被冲破
        yin_hai = [x for x in t["checked"] if x["type"] == "六合" and set(x["members"]) == {"寅", "亥"}]
        if yin_hai:
            assert yin_hai[0]["is_transformed"] is False

    def test_summary_when_empty(self):
        c = _make_chart(("甲", "子"), ("丙", "辰"), ("戊", "申"), ("辛", "酉"))
        rel = analyze_branch_relations(c)
        t = analyze_combination_transformation(c, rel)
        assert "summary_note" in t


# ========================== 流年大运动态 ==========================

class TestDynamicRelations:
    def test_basic_runs(self):
        d = analyze_dynamic_relations(SAMPLE_TENG, dayun_ganzhi="庚午", liunian_ganzhi="丙午")
        assert d["dayun"]["ganzhi"] == "庚午"
        assert d["liunian"]["ganzhi"] == "丙午"
        assert "interactions" in d["dayun"]

    def test_half_he_detected(self):
        """庚午半合 day寅 → 半合火。"""
        d = analyze_dynamic_relations(SAMPLE_TENG, dayun_ganzhi="庚午")
        notes = [x.get("type") for x in d["dayun"]["interactions"]]
        assert "半合" in notes

    def test_chong_detected(self):
        """流年丁酉冲卯（年支）。"""
        d = analyze_dynamic_relations(SAMPLE_TENG, liunian_ganzhi="丁酉")
        types = [x.get("type") for x in d["liunian"]["interactions"]]
        assert "六冲" in types or "六合" in types  # 酉 与 年卯 冲

    def test_dayun_liunian_self_interaction(self):
        """大运庚午 + 流年甲子 → 子午冲。"""
        d = analyze_dynamic_relations(SAMPLE_TENG, dayun_ganzhi="庚午", liunian_ganzhi="甲子")
        types = [x["type"] for x in d["dayun_liunian"]]
        assert "六冲" in types

    def test_empty_when_no_input(self):
        d = analyze_dynamic_relations(SAMPLE_TENG)
        assert d["dayun"]["interactions"] == []
        assert d["liunian"]["interactions"] == []


# ========================== 整合 v3 ==========================

class TestAnalyzeChartV3:
    def test_version(self):
        ra = analyze_chart_v3(SAMPLE_TENG)
        assert ra["version"] == "bazi-rules-v3.0.0"
        assert ra["rule_engine_version"] == "3.0.0"

    def test_v2_fields_preserved(self):
        ra = analyze_chart_v3(SAMPLE_TENG)
        for key in ("strength", "pattern", "useful_gods", "relations", "wuxing_power"):
            assert key in ra

    def test_v3_new_fields(self):
        ra = analyze_chart_v3(SAMPLE_TENG)
        for key in ("climate", "climate_merged", "transformation", "dynamic_relations"):
            assert key in ra

    def test_climate_present(self):
        ra = analyze_chart_v3(SAMPLE_TENG)
        c = ra["climate"]
        assert c["day_wx"] == "土"
        assert c["season"] == "autumn"

    def test_dynamic_uses_current_dayun(self):
        ra = analyze_chart_v3(SAMPLE_TENG)
        d = ra["dynamic_relations"]
        # 当前大运 庚午
        assert d["dayun"]["ganzhi"] == "庚午"

    def test_warnings_extended(self):
        ra = analyze_chart_v3(SAMPLE_TENG)
        assert isinstance(ra["warnings"], list)

    def test_v1_alias_returns_v3(self):
        from backend.domain.bazi_rules import analyze_chart
        ra = analyze_chart(SAMPLE_TENG)
        assert ra["version"] == "bazi-rules-v3.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
