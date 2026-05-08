"""AI 输出评估脚本测试（dry-run）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.evaluate_bazi_ai_outputs import (
    load_samples,
    run_dry_run,
    aggregate,
    build_chart_for_case,
)
from backend.domain.bazi_case_loader import load_standard_cases


# ========================== fixtures ==========================

class TestFixtures:
    def test_samples_load(self):
        samples = load_samples()
        assert isinstance(samples, list)
        assert len(samples) >= 5, "应至少 5 个 fixture 样本"

    def test_each_sample_has_required_fields(self):
        samples = load_samples()
        for s in samples:
            assert "case_id" in s
            assert "label" in s
            assert "text" in s
            assert "expected_outcome" in s
            assert s["expected_outcome"] in ("pass", "fail")

    def test_at_least_one_pass_sample(self):
        samples = load_samples()
        pass_samples = [s for s in samples if s.get("expected_outcome") == "pass"]
        assert len(pass_samples) >= 1, "应至少 1 个干净样本"

    def test_at_least_three_fail_samples(self):
        samples = load_samples()
        fail_samples = [s for s in samples if s.get("expected_outcome") == "fail"]
        assert len(fail_samples) >= 3, "应至少 3 个负样本"


# ========================== dry-run ==========================

class TestDryRun:
    def test_runs_without_error(self):
        cases = load_standard_cases()
        cases_by_id = {c["case_id"]: c for c in cases}
        results = run_dry_run(cases_by_id)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_each_result_has_self_test(self):
        cases = load_standard_cases()
        cases_by_id = {c["case_id"]: c for c in cases}
        results = run_dry_run(cases_by_id)
        for r in results:
            assert "expected_outcome" in r
            assert "actual_outcome" in r
            assert "self_test_passed" in r

    def test_clean_sample_passes(self):
        """expected=pass 的 clean_sample 应通过 self-test。"""
        cases = load_standard_cases()
        cases_by_id = {c["case_id"]: c for c in cases}
        results = run_dry_run(cases_by_id)
        clean = [r for r in results if r["label"] == "clean_sample"]
        assert len(clean) == 1
        assert clean[0]["self_test_passed"] is True

    def test_violation_samples_detected(self):
        """expected=fail 的样本应被 validator 检测到，self-test 通过。"""
        cases = load_standard_cases()
        cases_by_id = {c["case_id"]: c for c in cases}
        results = run_dry_run(cases_by_id)
        violations = [r for r in results if r["expected_outcome"] == "fail"]
        for r in violations:
            assert r["self_test_passed"] is True, (
                f"{r['label']}: validator 未识别预期违规，actual={r['actual_outcome']}"
            )


# ========================== aggregate ==========================

class TestAggregate:
    def test_empty_results(self):
        s = aggregate([])
        assert s["total"] == 0

    def test_dry_run_unexpected_zero_when_all_match(self):
        results = [
            {"expected_outcome": "pass", "passed": True, "violations": []},
            {"expected_outcome": "fail", "passed": True, "violations": [{"type": "x", "severity": "error"}]},
        ]
        s = aggregate(results, mode="dry-run")
        # expected=fail 的违规不计入 unexpected
        assert s["unexpected_errors"] == 0
        assert s["errors"] == 1

    def test_dry_run_unexpected_when_mismatch(self):
        results = [
            {"expected_outcome": "pass", "passed": False, "violations": [{"type": "x", "severity": "error"}]},
        ]
        s = aggregate(results, mode="dry-run")
        assert s["unexpected_errors"] == 1

    def test_live_all_violations_unexpected(self):
        results = [
            {"expected_outcome": "pass", "passed": False, "violations": [{"type": "x", "severity": "error"}]},
        ]
        s = aggregate(results, mode="live")
        assert s["unexpected_errors"] == 1


# ========================== chart 构造 ==========================

class TestBuildChart:
    def test_works_with_real_case(self):
        cases = load_standard_cases()
        if not cases:
            pytest.skip("无案例可测")
        c = build_chart_for_case(cases[0])
        assert c.get("available") is True
        assert "pillars" in c


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
