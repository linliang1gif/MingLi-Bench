"""AI 输出后置校验器测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.services.ai_output_validator import validate_bazi_ai_output
from backend.services import chart_service


# ========================== helpers ==========================

SAMPLE_CHART = chart_service.compute_chart(
    birth_date="1999-08-14", birth_time="22:30",
    calendar_type="lunar", gender="男",
)


# ========================== 禁止词检测 ==========================

class TestForbiddenPhrases:
    def test_clean_text_passes(self):
        r = validate_bazi_ai_output("你的命盘整体偏向稳健发展。", SAMPLE_CHART)
        assert r["passed"] is True
        assert r["suggested_action"] == "pass"

    @pytest.mark.parametrize("phrase", [
        "必定发财",
        "注定孤独",
        "一定离婚",
        "必有大灾",
        "活不过60",
    ])
    def test_forbidden_detected(self, phrase):
        text = f"根据命盘分析，你{phrase}。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        assert r["passed"] is False
        assert any(v["type"] == "forbidden_phrase" for v in r["violations"])

    def test_absolute_pattern(self):
        r = validate_bazi_ai_output("你必定会遇到贵人。", SAMPLE_CHART)
        violations = r["violations"]
        types = {v["type"] for v in violations}
        assert "forbidden_phrase" in types or "absolute_language" in types

    def test_medical_legal(self):
        r = validate_bazi_ai_output("建议购买比特币来改善财运。", SAMPLE_CHART)
        assert any(v["type"] == "medical_legal_absolute" for v in r["violations"])


# ========================== 大运校验 ==========================

class TestDayunValidation:
    def test_valid_dayun_passes(self):
        # 庚午是小滕当前大运
        text = "当前大运庚午，火土旺相。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        dayun_violations = [v for v in r["violations"] if v["type"] == "invalid_dayun"]
        assert len(dayun_violations) == 0

    def test_invalid_dayun_caught(self):
        text = "当前行运甲午大运中，事业有所起色。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        dayun_violations = [v for v in r["violations"] if v["type"] == "invalid_dayun"]
        assert len(dayun_violations) >= 1


# ========================== 本命年校验 ==========================

class TestBenmingValidation:
    def test_correct_benming_passes(self):
        text = "本命年兔年需注意健康。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        benming_v = [v for v in r["violations"] if v["type"] == "wrong_benming"]
        assert len(benming_v) == 0

    def test_wrong_benming_caught(self):
        text = "本命年龙年是一个关键年份。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        benming_v = [v for v in r["violations"] if v["type"] == "wrong_benming"]
        assert len(benming_v) >= 1


# ========================== 四柱校验 ==========================

class TestPillarValidation:
    def test_correct_pillars_pass(self):
        text = "年柱己卯，月柱癸酉，日柱戊寅，时柱癸亥。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        pillar_v = [v for v in r["violations"] if v["type"] == "wrong_pillar"]
        assert len(pillar_v) == 0

    def test_wrong_year_pillar_caught(self):
        text = "年柱甲子代表命主早年。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        pillar_v = [v for v in r["violations"] if v["type"] == "wrong_pillar"]
        assert len(pillar_v) >= 1
        assert "甲子" in pillar_v[0]["detail"]


# ========================== 综合 ==========================

class TestIntegrated:
    def test_empty_text_passes(self):
        r = validate_bazi_ai_output("", SAMPLE_CHART)
        assert r["passed"] is True

    def test_none_chart_still_checks_forbidden(self):
        r = validate_bazi_ai_output("必有大灾", None)
        assert r["passed"] is False

    def test_suggested_action_retry_on_error(self):
        r = validate_bazi_ai_output("你注定一定发财必定成功", SAMPLE_CHART)
        assert r["suggested_action"] == "retry"

    def test_multiple_violations_all_reported(self):
        text = "你必定发财，年柱甲子显示你注定富贵。"
        r = validate_bazi_ai_output(text, SAMPLE_CHART)
        assert len(r["violations"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
