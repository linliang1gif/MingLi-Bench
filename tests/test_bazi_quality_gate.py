"""八字质量门禁测试。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.check_bazi_quality_gate import (
    check_rule_evaluation,
    check_ai_output,
    RULE_REPORT,
    AI_REPORT,
)


@pytest.fixture
def tmp_rule_report(monkeypatch, tmp_path):
    """临时替换 RULE_REPORT 路径。"""
    fake = tmp_path / "rule.json"
    monkeypatch.setattr("scripts.check_bazi_quality_gate.RULE_REPORT", fake)
    return fake


@pytest.fixture
def tmp_ai_report(monkeypatch, tmp_path):
    fake = tmp_path / "ai.json"
    monkeypatch.setattr("scripts.check_bazi_quality_gate.AI_REPORT", fake)
    return fake


def _write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ========================== 规则评估检查 ==========================

class TestRuleEvaluationCheck:
    def test_missing_report_fails(self, tmp_rule_report):
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is False
        assert any("未找到" in r for r in reasons)

    def test_high_score_passes(self, tmp_rule_report):
        _write(tmp_rule_report, {
            "summary": {"avg_score": 95.0, "pass_rate": 100.0, "total": 5},
            "results": [
                {"dimension_scores": {"pillars": 100, "day_master": 100}, "rejected_hit": False}
                for _ in range(5)
            ],
        })
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is True

    def test_low_avg_fails(self, tmp_rule_report):
        _write(tmp_rule_report, {
            "summary": {"avg_score": 60.0, "pass_rate": 100.0, "total": 5},
            "results": [{"dimension_scores": {"pillars": 100, "day_master": 100}, "rejected_hit": False}],
        })
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is False
        assert any("平均分" in r for r in reasons)

    def test_low_pass_rate_fails(self, tmp_rule_report):
        _write(tmp_rule_report, {
            "summary": {"avg_score": 90.0, "pass_rate": 50.0, "total": 5},
            "results": [{"dimension_scores": {"pillars": 100, "day_master": 100}, "rejected_hit": False}],
        })
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is False
        assert any("通过率" in r for r in reasons)

    def test_pillar_error_fails(self, tmp_rule_report):
        _write(tmp_rule_report, {
            "summary": {"avg_score": 95.0, "pass_rate": 100.0, "total": 1},
            "results": [{"dimension_scores": {"pillars": 50, "day_master": 100}, "rejected_hit": False}],
        })
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is False
        assert any("排盘" in r for r in reasons)

    def test_day_master_error_fails(self, tmp_rule_report):
        _write(tmp_rule_report, {
            "summary": {"avg_score": 95.0, "pass_rate": 100.0, "total": 1},
            "results": [{"dimension_scores": {"pillars": 100, "day_master": 0}, "rejected_hit": False}],
        })
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is False
        assert any("日主" in r for r in reasons)

    def test_rejected_hit_fails(self, tmp_rule_report):
        _write(tmp_rule_report, {
            "summary": {"avg_score": 90.0, "pass_rate": 100.0, "total": 1},
            "results": [{"dimension_scores": {"pillars": 100, "day_master": 100}, "rejected_hit": True}],
        })
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        assert passed is False
        assert any("rejected" in r.lower() for r in reasons)


# ========================== AI 输出检查 ==========================

class TestAIOutputCheck:
    def test_missing_report_skipped(self, tmp_ai_report):
        passed, reasons = check_ai_output()
        assert passed is True
        assert any("跳过" in r or "skip" in r.lower() for r in reasons)

    def test_dry_run_self_test_pass(self, tmp_ai_report):
        # dry-run，所有违规都来自 expected=fail 样本（unexpected_errors=0）
        _write(tmp_ai_report, {
            "mode": "dry-run",
            "summary": {
                "mode": "dry-run", "total": 5, "passed": 5,
                "errors": 6, "warnings": 1,
                "unexpected_errors": 0, "unexpected_warnings": 0,
                "violation_types": {},
            },
            "results": [],
        })
        passed, reasons = check_ai_output()
        assert passed is True
        assert any("self-test" in r.lower() or "dry-run" in r.lower() for r in reasons)

    def test_live_no_errors_pass(self, tmp_ai_report):
        _write(tmp_ai_report, {
            "mode": "live",
            "summary": {
                "mode": "live", "total": 5, "passed": 5,
                "errors": 0, "warnings": 0,
                "unexpected_errors": 0, "unexpected_warnings": 0,
                "violation_types": {},
            },
            "results": [],
        })
        passed, reasons = check_ai_output()
        assert passed is True

    def test_live_with_errors_fails(self, tmp_ai_report):
        _write(tmp_ai_report, {
            "mode": "live",
            "summary": {
                "mode": "live", "total": 5, "passed": 3,
                "errors": 2, "warnings": 1,
                "unexpected_errors": 2, "unexpected_warnings": 1,
                "violation_types": {"forbidden_phrase": 2},
            },
            "results": [],
        })
        passed, reasons = check_ai_output()
        assert passed is False
        assert any("error" in r.lower() for r in reasons)

    def test_dry_run_with_unexpected_errors_fails(self, tmp_ai_report):
        # dry-run 中 expected=pass 的样本却失败了
        _write(tmp_ai_report, {
            "mode": "dry-run",
            "summary": {
                "mode": "dry-run", "total": 5, "passed": 4,
                "errors": 7, "warnings": 0,
                "unexpected_errors": 1, "unexpected_warnings": 0,
                "violation_types": {"forbidden_phrase": 1},
            },
            "results": [],
        })
        passed, reasons = check_ai_output()
        assert passed is False


# ========================== 真实数据冒烟 ==========================

class TestSmokeReal:
    def test_real_rule_report_loadable(self):
        """如果项目里已有真实报告，应该可以读取。"""
        if not RULE_REPORT.exists():
            pytest.skip("real rule report 未生成")
        passed, reasons = check_rule_evaluation(80.0, 80.0)
        # 不强制断言通过，只确保函数能跑
        assert isinstance(passed, bool)
        assert isinstance(reasons, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
