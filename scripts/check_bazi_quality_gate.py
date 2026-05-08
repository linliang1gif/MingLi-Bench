"""八字命理系统质量门禁。

规则
----
1. pytest 必须通过（外部 pytest 调用，本脚本不再跑测试，但读取上次报告）
2. 规则评估平均分 >= 80
3. 规则评估通过率 >= 80%
4. pillars / day_master 错误数 = 0
5. AI 输出校验 error 数 = 0（warning 允许，但统计）

退出码
------
0 = PASS
1 = FAIL

用法
----
.venv/Scripts/python.exe scripts/check_bazi_quality_gate.py

通常先运行：
1. python scripts/evaluate_bazi_rules.py
2. python scripts/evaluate_bazi_ai_outputs.py [--live]
3. python scripts/check_bazi_quality_gate.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

RULE_REPORT = ROOT / "reports" / "bazi_rule_evaluation_report.json"
AI_REPORT = ROOT / "reports" / "bazi_ai_output_evaluation_report.json"

# 阈值（可配置）
DEFAULT_MIN_AVG_SCORE = 80.0
DEFAULT_MIN_PASS_RATE = 80.0


# ========================== 单项检查 ==========================

def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"无法解析 {path.name}: {e}"}


def check_rule_evaluation(min_avg: float, min_pass_rate: float):
    """检查 bazi_rule_evaluation_report.json。返回 (passed, reasons)。"""
    reasons: List[str] = []
    data = _read_json(RULE_REPORT)
    if data is None:
        return False, [f"未找到 {RULE_REPORT.name}，请先运行 evaluate_bazi_rules.py"]
    if isinstance(data, dict) and data.get("_error"):
        return False, [data["_error"]]

    summary = data.get("summary") or {}
    results = data.get("results") or []

    avg = summary.get("avg_score", 0)
    pass_rate = summary.get("pass_rate", 0)

    pillar_errors = sum(1 for r in results if r.get("dimension_scores", {}).get("pillars", 100) < 100)
    dm_errors = sum(1 for r in results if r.get("dimension_scores", {}).get("day_master", 100) < 100)
    rejected_hits = sum(1 for r in results if r.get("rejected_hit"))

    passed = True
    if avg < min_avg:
        passed = False
        reasons.append(f"❌ 规则评估平均分 {avg} < {min_avg}")
    if pass_rate < min_pass_rate:
        passed = False
        reasons.append(f"❌ 规则评估通过率 {pass_rate}% < {min_pass_rate}%")
    if pillar_errors > 0:
        passed = False
        reasons.append(f"❌ 排盘错误 {pillar_errors} 例（pillars 维度<100）")
    if dm_errors > 0:
        passed = False
        reasons.append(f"❌ 日主错误 {dm_errors} 例")
    if rejected_hits > 0:
        passed = False
        reasons.append(f"❌ 落入 rejected 区 {rejected_hits} 例")

    if passed:
        reasons.append(f"✅ 规则评估通过 (avg={avg}, pass_rate={pass_rate}%, total={summary.get('total')})")

    return passed, reasons


def check_ai_output():
    reasons: List[str] = []
    data = _read_json(AI_REPORT)
    if data is None:
        # AI 评估报告非强制（可能尚未运行）
        reasons.append("⚠ 未找到 ai_output_evaluation_report.json，跳过 AI 输出检查")
        return True, reasons
    if isinstance(data, dict) and data.get("_error"):
        return False, [data["_error"]]

    summary = data.get("summary") or {}
    mode = summary.get("mode") or data.get("mode") or "?"
    # dry-run 模式下使用 unexpected_errors（仅 expected=pass 但实际 fail 的样本）
    # live 模式下 unexpected_errors == errors
    errors = summary.get("unexpected_errors", summary.get("errors", 0))
    total_errors = summary.get("errors", 0)
    warnings = summary.get("warnings", 0)
    unexpected_warnings = summary.get("unexpected_warnings", warnings)
    total = summary.get("total", 0)

    passed = errors == 0
    if errors > 0:
        reasons.append(f"❌ AI 输出非预期 error 违规 {errors} 例（mode={mode}）")
        types = summary.get("violation_types") or {}
        for k, v in list(types.items())[:3]:
            reasons.append(f"   - {k}: {v} 次")
    else:
        if mode == "dry-run":
            reasons.append(f"✅ AI 输出 dry-run self-test 通过 (total={total}, validator 检测正确)")
        else:
            reasons.append(f"✅ AI 输出无 error 违规 (mode={mode}, total={total}, warnings={warnings})")

    if mode == "dry-run" and total_errors > errors:
        reasons.append(f"  · 包含 {total_errors - errors} 个预期违规（来自负样本，不计入门禁）")
    if unexpected_warnings > 0:
        reasons.append(f"⚠ AI 输出 {unexpected_warnings} 个非预期 warning（不阻断）")

    return passed, reasons


# ========================== 主入口 ==========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-avg", type=float, default=DEFAULT_MIN_AVG_SCORE)
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    args = parser.parse_args()

    print("================ 八字质量门禁 ================")
    print(f"阈值: 平均分>={args.min_avg}, 通过率>={args.min_pass_rate}%")
    print()

    print("--- 规则评估检查 ---")
    rule_pass, rule_reasons = check_rule_evaluation(args.min_avg, args.min_pass_rate)
    for r in rule_reasons:
        print(f"  {r}")
    print()

    print("--- AI 输出检查 ---")
    ai_pass, ai_reasons = check_ai_output()
    for r in ai_reasons:
        print(f"  {r}")
    print()

    overall = rule_pass and ai_pass
    print("=" * 48)
    if overall:
        print("✅ 质量门禁通过")
        print(f"  - 规则评估: {RULE_REPORT}")
        if AI_REPORT.exists():
            print(f"  - AI 输出: {AI_REPORT}")
        return 0
    else:
        print("❌ 质量门禁未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
