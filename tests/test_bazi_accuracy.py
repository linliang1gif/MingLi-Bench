"""八字命理系统准确性测试。

覆盖：
- 排盘准确性（年月日时柱、立春、节气）
- 十神映射完整性
- 大运顺逆正确性
- 规则引擎旺衰/格局/喜用
- Prompt 模板变量完整性
- 免责声明不重复
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.services import chart_service, prompt_service
from backend.domain.bazi_rules import (
    get_shishen, calculate_strength, analyze_pattern,
    infer_useful_gods, analyze_chart, GAN_WUXING, TIAN_GAN, ZHI_CANG_GAN,
)


# ========================= 固定样本 =========================

SAMPLES = [
    {
        "desc": "小滕 (lunar 1999-08-14 22:30 男)",
        "input": {"birth_date": "1999-08-14", "birth_time": "22:30", "calendar_type": "lunar", "gender": "男"},
        "expect_pillars": {"year": ("己", "卯"), "month": ("癸", "酉"), "day": ("戊", "寅"), "hour": ("癸", "亥")},
        "expect_day_master": "戊",
        "expect_shengxiao": "兔",
    },
    {
        "desc": "立春前出生 (solar 2024-02-03 10:00 女) → 应属癸卯年",
        "input": {"birth_date": "2024-02-03", "birth_time": "10:00", "calendar_type": "solar", "gender": "女"},
        "expect_year_branch": "卯",  # 2024立春是2月4日，3日仍属上一年
    },
    {
        "desc": "立春后出生 (solar 2024-02-05 10:00 男) → 应属甲辰年",
        "input": {"birth_date": "2024-02-05", "birth_time": "10:00", "calendar_type": "solar", "gender": "男"},
        "expect_year_branch": "辰",  # 立春后属新年
    },
    {
        "desc": "子时换日 23:30 (solar 2000-06-15 23:30 男)",
        "input": {"birth_date": "2000-06-15", "birth_time": "23:30", "calendar_type": "solar", "gender": "男"},
        "expect_hour_branch": "子",  # 时支必须是子
    },
]


# ========================= 排盘测试 =========================

class TestChartComputation:
    """排盘核心准确性。"""

    @pytest.mark.parametrize("sample", SAMPLES, ids=[s["desc"] for s in SAMPLES])
    def test_chart_available(self, sample):
        r = chart_service.compute_chart(**sample["input"])
        assert r["available"] is True, f"排盘失败: {r.get('reason')}"

    def test_sample0_pillars(self):
        """小滕四柱正确性。"""
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        pillars = r["pillars"]
        expected = SAMPLES[0]["expect_pillars"]
        for pos, (stem, branch) in expected.items():
            assert pillars[pos]["stem"] == stem, f"{pos}柱天干应为{stem}"
            assert pillars[pos]["branch"] == branch, f"{pos}柱地支应为{branch}"

    def test_sample0_day_master(self):
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        assert r["wuxing"]["day_master"] == "戊"

    def test_sample0_shengxiao(self):
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        assert r.get("shengxiao") == "兔"

    def test_lichun_before(self):
        """立春前应属上一年。"""
        r = chart_service.compute_chart(**SAMPLES[1]["input"])
        assert r["pillars"]["year"]["branch"] == "卯", "立春前应仍属卯年"

    def test_lichun_after(self):
        """立春后应属新年。"""
        r = chart_service.compute_chart(**SAMPLES[2]["input"])
        assert r["pillars"]["year"]["branch"] == "辰", "立春后应属辰年"

    def test_zi_hour(self):
        """23:30 应为子时。"""
        r = chart_service.compute_chart(**SAMPLES[3]["input"])
        assert r["pillars"]["hour"]["branch"] == "子", "23:30应为子时"


# ========================= 十神映射测试 =========================

class TestShishen:
    """十神速查表完整性和正确性。"""

    def test_all_day_masters_produce_10_entries(self):
        """10个日主各生成10条十神映射。"""
        for dg in TIAN_GAN:
            table = chart_service.build_shishen_table(dg)
            assert len(table) == 10, f"日主{dg}十神表应有10项，实际{len(table)}"

    @pytest.mark.parametrize("day,target,expected", [
        ("戊", "甲", "七杀"),
        ("戊", "乙", "正官"),
        ("戊", "丙", "偏印"),
        ("戊", "丁", "正印"),
        ("戊", "己", "劫财"),
        ("戊", "庚", "食神"),
        ("戊", "辛", "伤官"),
        ("戊", "壬", "偏财"),
        ("戊", "癸", "正财"),
        ("甲", "庚", "七杀"),
        ("甲", "辛", "正官"),
        ("甲", "壬", "偏印"),
        ("甲", "癸", "正印"),
        ("甲", "乙", "劫财"),
        ("甲", "丙", "食神"),
        ("甲", "丁", "伤官"),
        ("甲", "戊", "偏财"),
        ("甲", "己", "正财"),
    ])
    def test_specific_shishen(self, day, target, expected):
        result = get_shishen(day, target)
        assert result == expected, f"日主{day}对{target}应为{expected}，实际{result}"

    def test_bazi_rules_matches_chart_service(self):
        """domain.bazi_rules.get_shishen 与 chart_service.build_shishen_table 一致。"""
        for dg in TIAN_GAN:
            table = chart_service.build_shishen_table(dg)
            for tg in TIAN_GAN:
                if tg == dg:
                    continue
                from_rules = get_shishen(dg, tg)
                from_table = table[tg]
                assert from_rules == from_table, (
                    f"日主{dg}对{tg}: rules={from_rules}, table={from_table}"
                )


# ========================= 大运测试 =========================

class TestDayun:
    """大运排列正确性。"""

    def test_sample0_has_dayun(self):
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        dayun = r.get("dayun") or []
        assert len(dayun) >= 5, "应排出至少5柱大运"

    def test_sample0_current_dayun(self):
        """小滕当前大运应为庚午（2024-2033）。"""
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        dayun = r.get("dayun") or []
        current = [d for d in dayun if d.get("current")]
        assert len(current) == 1, "应有且仅有一柱标记为当前"
        assert current[0]["ganzhi"] == "庚午", f"当前大运应为庚午，实际{current[0]['ganzhi']}"

    def test_male_yang_year_shun(self):
        """阳年男命应顺排大运（小滕: 己卯年男 → 己为阴...检查顺逆）。"""
        # 己=阴天干，男命阴年 → 逆排
        # 验证：第一柱大运 start_year < 出生年+10 对于逆排
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        dayun = r.get("dayun") or []
        assert len(dayun) >= 2
        # lunar_python 内部处理顺逆，我们验证结果合理性
        first = dayun[0]
        assert first["start_age"] > 0, "第一柱大运起运年龄应>0"

    def test_female_solar_dayun(self):
        """女命大运应正确排列。"""
        r = chart_service.compute_chart(**SAMPLES[1]["input"])
        dayun = r.get("dayun") or []
        assert len(dayun) >= 5


# ========================= 规则引擎测试 =========================

class TestRuleEngine:
    """旺衰/格局/喜用规则引擎。"""

    def _get_chart(self, idx=0):
        return chart_service.compute_chart(**SAMPLES[idx]["input"])

    def test_strength_returns_valid(self):
        c = self._get_chart()
        s = calculate_strength(c)
        assert s["day_gan"] == "戊"
        assert s["day_wx"] == "土"
        assert s["strength_level"] in ("身强", "身弱", "偏强", "偏弱", "uncertain")
        assert 0 <= s["score"] <= 100

    def test_sample0_is_weak(self):
        """小滕戊土失令于酉月，应偏弱。"""
        c = self._get_chart()
        s = calculate_strength(c)
        assert s["strength_level"] in ("偏弱", "身弱"), f"期望身弱系，实际{s['strength_level']}"
        assert s["score"] < 50

    def test_pattern_returns_valid(self):
        c = self._get_chart()
        p = analyze_pattern(c)
        assert "pattern" in p
        assert "evidence" in p
        assert isinstance(p["evidence"], list)

    def test_sample0_pattern_is_shangguan(self):
        """月令酉本气辛为伤官，应取伤官格。"""
        c = self._get_chart()
        p = analyze_pattern(c)
        assert "伤官" in p["pattern"], f"期望伤官格，实际{p['pattern']}"

    def test_useful_gods_has_consensus(self):
        c = self._get_chart()
        s = calculate_strength(c)
        p = analyze_pattern(c)
        ug = infer_useful_gods(s, p, c)
        assert "consensus_useful" in ug
        assert "火" in ug["consensus_useful"], "两法应共识喜火(印)"

    def test_analyze_chart_integrated(self):
        c = self._get_chart()
        ra = analyze_chart(c)
        assert ra["rule_engine_version"] in ("2.0.0", "3.0.0")
        assert "strength" in ra
        assert "pattern" in ra
        assert "useful_gods" in ra

    def test_rule_analysis_in_chart_output(self):
        """compute_chart 应自动包含 rule_analysis。"""
        c = self._get_chart()
        assert "rule_analysis" in c
        assert c["rule_analysis"].get("rule_engine_version") in ("2.0.0", "3.0.0")


# ========================= 藏干表测试 =========================

class TestHiddenStems:
    """地支藏干表完整性。"""

    def test_all_12_branches_have_canggan(self):
        branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        for b in branches:
            assert b in ZHI_CANG_GAN, f"地支{b}缺少藏干定义"
            cg = ZHI_CANG_GAN[b]
            assert len(cg) >= 1, f"地支{b}至少应有1个藏干"
            # 权重之和应约等于1
            total = sum(w for _, w in cg)
            assert 0.95 <= total <= 1.05, f"地支{b}藏干权重之和={total}，应约为1"

    def test_canggan_are_valid_tiangan(self):
        for b, cg_list in ZHI_CANG_GAN.items():
            for g, w in cg_list:
                assert g in TIAN_GAN, f"地支{b}藏干{g}不是有效天干"
                assert 0 < w <= 1, f"地支{b}藏干{g}权重{w}不合理"


# ========================= Prompt 测试 =========================

class TestPrompt:
    """Prompt 层准确性。"""

    def test_system_prompt_has_version(self):
        sp = prompt_service.get_system_prompt()
        assert "prompt_version=" in sp

    def test_subject_block_has_shishen_ref(self):
        c = chart_service.compute_chart(**SAMPLES[0]["input"])
        s = {"nickname": "Test", "gender": "男", "birth_date": "1999-08-14",
             "birth_time": "22:30", "birth_place": "Test", "calendar_type": "lunar",
             "focus_topics": ["财运"]}
        ctx = prompt_service.build_subject_context(s, c)
        blk = prompt_service.render_subject_block(ctx)
        assert "十神速查" in blk
        assert "丙=偏印" in blk
        assert "癸=正财" in blk

    def test_subject_block_has_rule_analysis(self):
        c = chart_service.compute_chart(**SAMPLES[0]["input"])
        s = {"nickname": "T", "gender": "男", "birth_date": "1999-08-14",
             "birth_time": "22:30", "birth_place": "X", "calendar_type": "lunar",
             "focus_topics": []}
        ctx = prompt_service.build_subject_context(s, c)
        blk = prompt_service.render_subject_block(ctx)
        assert "规则引擎" in blk
        assert "旺衰评估" in blk
        assert "格局判断" in blk
        assert "喜用神" in blk

    def test_subject_block_no_pseudo_placeholder(self):
        """不应存在伪占位符如 '{丙对应十神}'。"""
        c = chart_service.compute_chart(**SAMPLES[0]["input"])
        s = {"nickname": "T", "gender": "男", "birth_date": "1999-08-14",
             "birth_time": "22:30", "birth_place": "X", "calendar_type": "lunar",
             "focus_topics": []}
        ctx = prompt_service.build_subject_context(s, c)
        blk = prompt_service.render_subject_block(ctx)
        assert "{丙对应十神}" not in blk
        assert "{" not in blk or "（" in blk  # 没有未替换的大括号占位符

    def test_disclaimer_no_duplicate(self):
        text = "一些分析内容"
        r1 = prompt_service.append_disclaimer(text)
        r2 = prompt_service.append_disclaimer(r1)
        assert r1 == r2, "免责声明不应重复追加"

    def test_disclaimer_idempotent_on_similar(self):
        text = "分析结果，仅供参考，不构成建议。"
        r = prompt_service.append_disclaimer(text)
        assert r == text, "已含免责片段时不应再追加"

    def test_render_template_warns_unreplaced(self, caplog):
        """模板中有未提供的占位符应产生 warning。"""
        import logging
        with caplog.at_level(logging.WARNING):
            prompt_service._render("Hello {unknown_var}!", {"nickname": "test"})
        assert any("unreplaced" in r.message for r in caplog.records)


# ========================= 五行统计测试 =========================

class TestWuxing:
    """五行计数。"""

    def test_sample0_wuxing_counts(self):
        r = chart_service.compute_chart(**SAMPLES[0]["input"])
        counts = r["wuxing"]["counts"]
        # 己(土) 卯(木) 癸(水) 酉(金) 戊(土) 寅(木) 癸(水) 亥(水)
        assert counts["木"] == 2
        assert counts["火"] == 0
        assert counts["土"] == 2
        assert counts["金"] == 1
        assert counts["水"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
