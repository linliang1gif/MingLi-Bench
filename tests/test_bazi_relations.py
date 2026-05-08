"""地支关系测试：六合、六冲、三合、三会、六害、三刑、自刑。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.domain.bazi_relations import (
    analyze_branch_relations,
    LIU_HE, LIU_CHONG, LIU_HAI, SAN_HE, SAN_HUI,
    SAN_XING_WUEN, SAN_XING_SHISHI, XING_PAIR, ZI_XING,
)
from backend.services import chart_service


# ========================== helpers ==========================

def _chart(birth_date, birth_time, cal="solar", gender="男"):
    return chart_service.compute_chart(
        birth_date=birth_date, birth_time=birth_time,
        calendar_type=cal, gender=gender,
    )

def _make_chart_with_branches(year_b, month_b, day_b, hour_b):
    """构造一个只有地支的假 chart 用于单元测试。"""
    return {
        "pillars": {
            "year": {"stem": "甲", "branch": year_b},
            "month": {"stem": "甲", "branch": month_b},
            "day": {"stem": "甲", "branch": day_b},
            "hour": {"stem": "甲", "branch": hour_b},
        }
    }


# ========================== 关系表完整性 ==========================

class TestRelationTables:
    def test_liu_he_has_6_pairs(self):
        assert len(LIU_HE) == 6

    def test_liu_chong_has_6_pairs(self):
        assert len(LIU_CHONG) == 6

    def test_liu_hai_has_6_pairs(self):
        assert len(LIU_HAI) == 6

    def test_san_he_has_4_groups(self):
        assert len(SAN_HE) == 4

    def test_san_hui_has_4_groups(self):
        assert len(SAN_HUI) == 4

    def test_zi_xing_has_4(self):
        assert len(ZI_XING) == 4
        assert ZI_XING == {"辰", "午", "酉", "亥"}


# ========================== 六合 ==========================

class TestLiuHe:
    def test_yin_hai_he(self):
        """寅亥合木。"""
        c = _make_chart_with_branches("寅", "子", "午", "亥")
        r = analyze_branch_relations(c)
        he = [x for x in r["combinations"] if x["type"] == "六合" and set(x["branches"]) == {"寅", "亥"}]
        assert len(he) == 1
        assert "木" in he[0]["result"]

    def test_chen_you_he(self):
        """辰酉合金。"""
        c = _make_chart_with_branches("辰", "酉", "午", "子")
        r = analyze_branch_relations(c)
        he = [x for x in r["combinations"] if x["type"] == "六合" and set(x["branches"]) == {"辰", "酉"}]
        assert len(he) == 1
        assert "金" in he[0]["result"]


# ========================== 六冲 ==========================

class TestLiuChong:
    def test_zi_wu_chong(self):
        """子午冲。"""
        c = _make_chart_with_branches("子", "卯", "午", "酉")
        r = analyze_branch_relations(c)
        chong = [x for x in r["clashes"] if set(x["branches"]) == {"子", "午"}]
        assert len(chong) == 1

    def test_mao_you_chong(self):
        """卯酉冲（小滕有此冲）。"""
        c = _make_chart_with_branches("卯", "酉", "寅", "亥")
        r = analyze_branch_relations(c)
        chong = [x for x in r["clashes"] if set(x["branches"]) == {"卯", "酉"}]
        assert len(chong) == 1

    def test_sample_weak_has_mao_you_chong(self):
        """小滕实例应检测到卯酉冲。"""
        c = _chart("1999-08-14", "22:30", "lunar", "男")
        r = analyze_branch_relations(c)
        chong_pairs = [tuple(sorted(x["branches"])) for x in r["clashes"]]
        assert ("卯", "酉") in chong_pairs


# ========================== 三合 ==========================

class TestSanHe:
    def test_shen_zi_chen_full(self):
        """申子辰三合水局。"""
        c = _make_chart_with_branches("申", "子", "辰", "午")
        r = analyze_branch_relations(c)
        san = [x for x in r["combinations"] if x["type"] == "三合"]
        assert len(san) >= 1
        assert "水" in san[0]["result"]

    def test_half_combination(self):
        """半合检测。"""
        c = _make_chart_with_branches("申", "子", "午", "卯")
        r = analyze_branch_relations(c)
        half = [x for x in r["combinations"] if x["type"] == "半合"]
        assert len(half) >= 1


# ========================== 三会 ==========================

class TestSanHui:
    def test_yin_mao_chen_hui(self):
        """寅卯辰三会木局。"""
        c = _make_chart_with_branches("寅", "卯", "辰", "午")
        r = analyze_branch_relations(c)
        hui = [x for x in r["meetings"] if x["type"] == "三会"]
        assert len(hui) >= 1
        assert "木" in hui[0]["result"]


# ========================== 六害 ==========================

class TestLiuHai:
    def test_zi_wei_hai(self):
        """子未害。"""
        c = _make_chart_with_branches("子", "卯", "未", "午")
        r = analyze_branch_relations(c)
        hai = [x for x in r["harms"] if set(x["branches"]) == {"子", "未"}]
        assert len(hai) == 1

    def test_you_xu_hai(self):
        """酉戌害。"""
        c = _make_chart_with_branches("酉", "戌", "午", "子")
        r = analyze_branch_relations(c)
        hai = [x for x in r["harms"] if set(x["branches"]) == {"酉", "戌"}]
        assert len(hai) == 1


# ========================== 三刑 ==========================

class TestSanXing:
    def test_yin_si_shen_xing(self):
        """寅巳申无恩之刑。"""
        c = _make_chart_with_branches("寅", "巳", "申", "午")
        r = analyze_branch_relations(c)
        xing = [x for x in r["punishments"] if x["type"] == "无恩之刑"]
        assert len(xing) >= 1
        assert xing[0]["full"] is True

    def test_zi_mao_xing(self):
        """子卯无礼之刑。"""
        c = _make_chart_with_branches("子", "卯", "午", "酉")
        r = analyze_branch_relations(c)
        xing = [x for x in r["punishments"] if x["type"] == "无礼之刑"]
        assert len(xing) == 1

    def test_chou_wei_xu_xing(self):
        """丑未戌恃势之刑。"""
        c = _make_chart_with_branches("丑", "未", "戌", "午")
        r = analyze_branch_relations(c)
        xing = [x for x in r["punishments"] if x["type"] == "恃势之刑"]
        assert len(xing) >= 1


# ========================== 自刑 ==========================

class TestZiXing:
    def test_wu_wu_zi_xing(self):
        """午午自刑。"""
        c = _make_chart_with_branches("午", "午", "子", "卯")
        r = analyze_branch_relations(c)
        zx = [x for x in r["punishments"] if x["type"] == "自刑"]
        assert len(zx) == 1
        assert zx[0]["branches"] == ["午", "午"]

    def test_you_you_zi_xing(self):
        """酉酉自刑。"""
        c = _make_chart_with_branches("酉", "酉", "子", "卯")
        r = analyze_branch_relations(c)
        zx = [x for x in r["punishments"] if x["type"] == "自刑"]
        assert len(zx) == 1


# ========================== 综合 ==========================

class TestIntegrated:
    def test_evidence_populated(self):
        c = _chart("1999-08-14", "22:30", "lunar", "男")
        r = analyze_branch_relations(c)
        assert len(r["evidence"]) > 0

    def test_output_structure(self):
        c = _chart("1999-08-14", "22:30", "lunar", "男")
        r = analyze_branch_relations(c)
        for key in ("combinations", "clashes", "harms", "punishments", "meetings", "evidence"):
            assert key in r
            assert isinstance(r[key], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
