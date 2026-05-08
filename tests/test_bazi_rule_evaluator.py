"""规则引擎评分器测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.domain.bazi_rule_evaluator import evaluate_rule_result, WEIGHTS
from backend.domain.bazi_case_loader import get_case_by_id
from backend.services import chart_service


# ========================== helpers ==========================

def _make_chart_pillars(year_gz, month_gz, day_gz, hour_gz):
    """构造一个最小可评估的 chart。"""
    return {
        "pillars": {
            "year": {"stem": year_gz[0], "branch": year_gz[1]},
            "month": {"stem": month_gz[0], "branch": month_gz[1]},
            "day": {"stem": day_gz[0], "branch": day_gz[1]},
            "hour": {"stem": hour_gz[0], "branch": hour_gz[1]},
        },
        "wuxing": {"day_master": day_gz[0]},
    }


def _base_case():
    """旧 schema（兼容性）。"""
    return {
        "case_id": "test",
        "title": "测试",
        "confidence": "medium",
        "input": {},
        "expected": {
            "pillars": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"},
            "day_master": "丙",
            "strength": {"accepted_levels": ["身强"], "rejected_levels": ["身弱"]},
            "pattern": {"accepted_patterns": ["建禄格"], "rejected_patterns": []},
            "useful_gods": {
                "accepted_useful_elements": ["土", "金"],
                "accepted_avoid_elements": ["木", "水"],
                "allow_conflict": True,
            },
        },
    }


def _base_case_v36():
    """新 schema (Phase 3.6)。"""
    return {
        "case_id": "test_v36",
        "title": "测试 v3.6 schema",
        "confidence": "medium",
        "input": {},
        "expected": {
            "pillars": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"},
            "day_master": "丙",
            "primary_strength_level": "身强",
            "accepted_strength_levels": ["身强", "偏强"],
            "rejected_strength_levels": ["身弱", "偏弱"],
            "primary_pattern": "建禄格",
            "accepted_patterns": ["建禄格", "月劫格"],
            "rejected_patterns": ["伤官格"],
            "accepted_useful_elements": ["土", "金"],
            "accepted_avoid_elements": ["木", "水"],
            "allow_conflict": True,
            "dispute_notes": ["建禄/月劫流派分歧"],
        },
    }


def _base_rule_result(level="身强", pattern="建禄格"):
    return {
        "strength": {"strength_level": level, "score": 70},
        "pattern": {"pattern": pattern, "confidence": "high"},
        "useful_gods": {
            "wangshuai_method": {"useful_elements": ["土", "金"], "avoid_elements": ["木", "水"]},
            "pattern_method": {"useful_elements": ["土", "金"], "avoid_elements": ["木"]},
            "final_suggestion": {"preferred": ["土"], "avoid": ["木"], "confidence": "high"},
            "conflict": False,
        },
    }


# ========================== 四柱评分 ==========================

class TestPillarsScore:
    def test_perfect_match(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result()
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["pillars"] == 100

    def test_pillar_mismatch_fatal(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丁卯", "丁卯")  # day 错
        rr = _base_rule_result()
        r = evaluate_rule_result(case, chart, rr)
        assert r["fatal"] is True
        assert r["passed"] is False
        assert any("day" in m for m in r["mismatches"])


# ========================== 日主评分 ==========================

class TestDayMasterScore:
    def test_match(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        r = evaluate_rule_result(case, chart, _base_rule_result())
        assert r["dimension_scores"]["day_master"] == 100

    def test_mismatch_fatal(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        chart["wuxing"]["day_master"] = "戊"  # 错误日主
        r = evaluate_rule_result(case, chart, _base_rule_result())
        assert r["fatal"] is True
        assert r["dimension_scores"]["day_master"] == 0


# ========================== 旺衰评分 ==========================

class TestStrengthScore:
    def test_in_accepted(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身强")
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["strength"] == 100

    def test_in_rejected_fatal(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身弱")  # 在 rejected
        r = evaluate_rule_result(case, chart, rr)
        assert r["fatal"] is True
        assert r["dimension_scores"]["strength"] == 0

    def test_grey_zone_partial(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="中和")  # 灰区
        r = evaluate_rule_result(case, chart, rr)
        assert 30 <= r["dimension_scores"]["strength"] <= 70

    def test_grey_zone_low_conf_higher(self):
        case = _base_case()
        case["confidence"] = "low"
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="中和")
        r = evaluate_rule_result(case, chart, rr)
        # low confidence 灰区给更高分
        assert r["dimension_scores"]["strength"] >= 60


# ========================== 格局评分 ==========================

class TestPatternScore:
    def test_match(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        r = evaluate_rule_result(case, chart, _base_rule_result(pattern="建禄格"))
        assert r["dimension_scores"]["pattern"] == 100

    def test_unknown_partial(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(pattern="不明显")
        r = evaluate_rule_result(case, chart, rr)
        # 不明显应该给部分分（<100但不为0）
        s = r["dimension_scores"]["pattern"]
        assert 30 <= s < 100

    def test_rejected(self):
        case = _base_case()
        case["expected"]["pattern"]["rejected_patterns"] = ["伤官格"]
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(pattern="伤官格")
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["pattern"] == 0


# ========================== 喜用神评分 ==========================

class TestUsefulGodsScore:
    def test_full_intersection(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        r = evaluate_rule_result(case, chart, _base_rule_result())
        assert r["dimension_scores"]["useful_gods"] >= 80

    def test_no_intersection(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result()
        rr["useful_gods"]["wangshuai_method"]["useful_elements"] = ["木"]
        rr["useful_gods"]["pattern_method"]["useful_elements"] = ["水"]
        rr["useful_gods"]["final_suggestion"]["preferred"] = ["水"]
        r = evaluate_rule_result(case, chart, rr)
        # 喜用无交集 → use_score=0，但 avoid 仍可能有交集
        assert r["dimension_scores"]["useful_gods"] < 80

    def test_partial_intersection(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result()
        rr["useful_gods"]["wangshuai_method"]["useful_elements"] = ["土"]  # 部分匹配
        rr["useful_gods"]["pattern_method"]["useful_elements"] = ["土"]
        rr["useful_gods"]["final_suggestion"]["preferred"] = ["土"]
        r = evaluate_rule_result(case, chart, rr)
        # 命中50%
        assert 60 <= r["dimension_scores"]["useful_gods"] <= 100


# ========================== 通过条件 ==========================

class TestPassFail:
    def test_full_match_passes(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        r = evaluate_rule_result(case, chart, _base_rule_result())
        assert r["passed"] is True
        assert r["total_score"] >= 75

    def test_pillar_error_forces_fail(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "戊辰", "丁卯")
        r = evaluate_rule_result(case, chart, _base_rule_result())
        assert r["passed"] is False

    def test_strength_rejected_forces_fail(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身弱")
        r = evaluate_rule_result(case, chart, rr)
        assert r["passed"] is False

    def test_total_score_weighted_correctly(self):
        case = _base_case()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        r = evaluate_rule_result(case, chart, _base_rule_result())
        # 各维度均 100 → 总分应为 100
        if all(v == 100 for v in r["dimension_scores"].values()):
            assert r["total_score"] == 100


# ========================== 真实案例端到端 ==========================

class TestRealCaseEndToEnd:
    def test_case_001_runs(self):
        """case_001 (小滕) 应能完整跑通评估流程。"""
        case = get_case_by_id("case_001")
        assert case is not None
        inp = case["input"]
        chart = chart_service.compute_chart(
            birth_date=inp["birth_date"],
            birth_time=inp["birth_time"],
            calendar_type=inp.get("calendar_type", "solar"),
            gender="男" if inp.get("gender") in ("male", "男") else "女",
        )
        rr = chart.get("rule_analysis") or {}
        r = evaluate_rule_result(case, chart, rr)
        assert "total_score" in r
        assert "dimension_scores" in r
        assert r["dimension_scores"]["pillars"] == 100, "case_001 排盘应完全匹配"
        assert r["dimension_scores"]["day_master"] == 100, "case_001 日主应匹配"


# ========================== Phase 3.6: primary/accepted/rejected ==========================

class TestPhase36Schema:
    def test_primary_hit_full_score(self):
        case = _base_case_v36()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身强", pattern="建禄格")
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["strength"] == 100
        assert r["dimension_scores"]["pattern"] == 100
        assert r["primary_hit"] is True
        assert r["accepted_hit"] is True
        assert r["rejected_hit"] is False
        assert r["hit_breakdown"]["strength"] == "primary"
        assert r["hit_breakdown"]["pattern"] == "primary"

    def test_accepted_non_primary_partial(self):
        """命中 accepted 但非 primary → strength=80。"""
        case = _base_case_v36()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="偏强", pattern="月劫格")  # 都在 accepted 但非 primary
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["strength"] == 80
        assert r["dimension_scores"]["pattern"] == 80
        assert r["primary_hit"] is False
        assert r["accepted_hit"] is True
        assert r["rejected_hit"] is False
        assert r["dispute_reason"] != ""

    def test_rejected_strength_fatal(self):
        case = _base_case_v36()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身弱")
        r = evaluate_rule_result(case, chart, rr)
        assert r["fatal"] is True
        assert r["dimension_scores"]["strength"] == 0
        assert r["rejected_hit"] is True
        assert r["passed"] is False

    def test_rejected_pattern_zero(self):
        case = _base_case_v36()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身强", pattern="伤官格")  # 伤官在 rejected
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["pattern"] == 0
        assert r["rejected_hit"] is True

    def test_low_confidence_grey_capped(self):
        """confidence=low + 灰区 → 最多 80。"""
        case = _base_case_v36()
        case["confidence"] = "low"
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="中和", pattern="不明显")
        r = evaluate_rule_result(case, chart, rr)
        assert r["dimension_scores"]["strength"] <= 80
        assert r["dimension_scores"]["pattern"] <= 80

    def test_mixed_primary_and_accepted(self):
        case = _base_case_v36()
        chart = _make_chart_pillars("甲子", "乙丑", "丙寅", "丁卯")
        rr = _base_rule_result(level="身强", pattern="月劫格")  # strength primary, pattern accepted
        r = evaluate_rule_result(case, chart, rr)
        assert r["primary_hit"] is False  # 必须两者都 primary 才算
        assert r["accepted_hit"] is True
        assert r["dimension_scores"]["strength"] == 100
        assert r["dimension_scores"]["pattern"] == 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
