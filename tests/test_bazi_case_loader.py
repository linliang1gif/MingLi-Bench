"""标准案例加载器测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.domain.bazi_case_loader import (
    load_standard_cases,
    get_case_by_id,
    list_case_ids,
    validate_case_schema,
)


# ========================== 加载器 ==========================

class TestLoader:
    def test_load_returns_list(self):
        cases = load_standard_cases()
        assert isinstance(cases, list)

    def test_load_at_least_5_cases(self):
        cases = load_standard_cases()
        assert len(cases) >= 5, f"标准案例库至少 5 例，实际 {len(cases)}"

    def test_each_case_has_required_fields(self):
        cases = load_standard_cases()
        for c in cases:
            assert "case_id" in c
            assert "title" in c
            assert "input" in c
            assert "expected" in c

    def test_case_ids_unique(self):
        ids = list_case_ids()
        assert len(ids) == len(set(ids)), "case_id 必须唯一"

    def test_get_case_by_id(self):
        cases = load_standard_cases()
        if cases:
            cid = cases[0]["case_id"]
            assert get_case_by_id(cid) is not None

    def test_get_nonexistent_returns_none(self):
        assert get_case_by_id("nonexistent_case_xyz_999") is None


# ========================== Schema 校验 ==========================

class TestValidateCaseSchema:
    def _valid_case(self):
        return {
            "case_id": "test_1",
            "title": "测试",
            "input": {
                "gender": "male",
                "calendar_type": "solar",
                "birth_date": "1990-01-01",
                "birth_time": "12:00",
            },
            "expected": {
                "pillars": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"},
                "day_master": "丙",
            },
        }

    def test_valid_case(self):
        r = validate_case_schema(self._valid_case())
        assert r["valid"] is True
        assert r["errors"] == []

    def test_missing_top_field(self):
        c = self._valid_case()
        del c["case_id"]
        r = validate_case_schema(c)
        assert r["valid"] is False
        assert any("case_id" in e for e in r["errors"])

    def test_missing_input_field(self):
        c = self._valid_case()
        del c["input"]["birth_date"]
        r = validate_case_schema(c)
        assert r["valid"] is False
        assert any("birth_date" in e for e in r["errors"])

    def test_invalid_calendar_type(self):
        c = self._valid_case()
        c["input"]["calendar_type"] = "weird"
        r = validate_case_schema(c)
        assert r["valid"] is False
        assert any("calendar_type" in e for e in r["errors"])

    def test_invalid_gender(self):
        c = self._valid_case()
        c["input"]["gender"] = "robot"
        r = validate_case_schema(c)
        assert r["valid"] is False
        assert any("gender" in e for e in r["errors"])

    def test_missing_expected_pillars(self):
        c = self._valid_case()
        del c["expected"]["pillars"]
        r = validate_case_schema(c)
        assert r["valid"] is False

    def test_pillar_string_format(self):
        c = self._valid_case()
        c["expected"]["pillars"]["year"] = "甲"  # 只有1个字
        r = validate_case_schema(c)
        assert r["valid"] is False

    def test_strength_must_be_dict(self):
        c = self._valid_case()
        c["expected"]["strength"] = "wrong"
        r = validate_case_schema(c)
        assert r["valid"] is False

    def test_strength_lists_must_be_lists(self):
        c = self._valid_case()
        c["expected"]["strength"] = {"accepted_levels": "not-a-list"}
        r = validate_case_schema(c)
        assert r["valid"] is False

    def test_non_dict_input(self):
        r = validate_case_schema("not a dict")
        assert r["valid"] is False


# ========================== 真实案例库结构 ==========================

class TestRealCases:
    def test_all_cases_pass_schema(self):
        cases = load_standard_cases(strict=False)
        for c in cases:
            r = validate_case_schema(c)
            assert r["valid"], f"{c.get('case_id')}: {r['errors']}"

    def test_case_001_exists(self):
        c = get_case_by_id("case_001")
        assert c is not None
        assert "戊" in c["expected"]["day_master"]

    def test_all_have_notes(self):
        cases = load_standard_cases()
        for c in cases:
            assert c.get("notes"), f"{c.get('case_id')} 缺少 notes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
