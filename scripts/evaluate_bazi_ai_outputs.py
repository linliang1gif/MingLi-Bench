"""AI 实际输出回归评估。

用法
----
# dry-run（默认）：使用预置 fixtures (ai_output_samples.json)，不调用 LLM
.venv/Scripts/python.exe scripts/evaluate_bazi_ai_outputs.py

# live：真实调用当前 LLM provider（生产环境）
.venv/Scripts/python.exe scripts/evaluate_bazi_ai_outputs.py --live

输出
----
reports/bazi_ai_output_evaluation_report.json
reports/bazi_ai_output_evaluation_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.domain.bazi_case_loader import load_standard_cases
from backend.services import chart_service
from backend.services.ai_output_validator import validate_bazi_ai_output

REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
JSON_REPORT = REPORTS_DIR / "bazi_ai_output_evaluation_report.json"
MD_REPORT = REPORTS_DIR / "bazi_ai_output_evaluation_report.md"

SAMPLES_FILE = ROOT / "backend" / "domain" / "fixtures" / "bazi_cases" / "ai_output_samples.json"


# ========================== fixtures 加载 ==========================

def load_samples():
    if not SAMPLES_FILE.exists():
        return []
    return json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))


# ========================== chart 构造 ==========================

def _gender_str(g):
    return "男" if g in ("male", "男") else "女"


def build_chart_for_case(case: dict) -> dict:
    inp = case["input"]
    return chart_service.compute_chart(
        birth_date=inp["birth_date"],
        birth_time=inp["birth_time"],
        calendar_type=inp.get("calendar_type", "solar"),
        gender=_gender_str(inp.get("gender", "male")),
        longitude=inp.get("longitude"),
    )


# ========================== dry-run ==========================

def run_dry_run(cases_by_id: dict) -> list:
    """用预置 fixtures 跑 validator self-test。

    每条 fixture 含 expected_outcome (pass/fail)，
    self_test_passed = (validator 实际结论 == expected_outcome)。
    """
    samples = load_samples()
    if not samples:
        print("⚠ 没有 ai_output_samples.json，dry-run 跳过。")
        return []

    results = []
    for sample in samples:
        cid = sample.get("case_id")
        case = cases_by_id.get(cid)
        if not case:
            print(f"⚠ 样本 {sample.get('label')} 关联的 case {cid} 不存在")
            continue

        chart = build_chart_for_case(case)
        text = sample.get("text", "")
        expected = sample.get("expected_outcome", "pass")
        v = validate_bazi_ai_output(text, chart)

        actual = "pass" if v["passed"] else "fail"
        self_test_passed = (actual == expected)

        results.append({
            "case_id": cid,
            "label": sample.get("label", ""),
            "expected_outcome": expected,
            "actual_outcome": actual,
            "self_test_passed": self_test_passed,
            "passed": self_test_passed,  # 兼容旧字段
            "violations": v["violations"],
            "suggested_action": v["suggested_action"],
            "text_excerpt": text[:80] + ("..." if len(text) > 80 else ""),
        })
    return results


# ========================== live ==========================

def run_live(cases: list) -> list:
    """真实调用 LLM 生成报告，再校验。"""
    try:
        from backend.services import prompt_service, llm_service, subject_service  # noqa
    except Exception as e:
        print(f"❌ live 模式依赖加载失败: {e}")
        return []

    results = []
    for case in cases:
        cid = case["case_id"]
        try:
            chart = build_chart_for_case(case)
            subject = {
                "nickname": "测试用户",
                "gender": _gender_str(case["input"].get("gender", "male")),
                "birth_date": case["input"]["birth_date"],
                "birth_time": case["input"]["birth_time"],
                "birth_place": case["input"].get("birth_place", "未指定"),
                "calendar_type": case["input"].get("calendar_type", "solar"),
                "focus_topics": ["命盘综述"],
            }
            ctx = prompt_service.build_subject_context(subject, chart)
            block = prompt_service.render_subject_block(ctx)
            sys_prompt = prompt_service.get_system_prompt()
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": block + "\n请用 200 字左右概述命盘。"},
            ]
            text = llm_service.chat_complete(messages=messages, max_tokens=500)
        except Exception as e:
            text = f"[live 调用失败: {type(e).__name__}: {e}]"

        v = validate_bazi_ai_output(text, chart if isinstance(chart, dict) else None)
        results.append({
            "case_id": cid,
            "label": "live",
            "passed": v["passed"],
            "violations": v["violations"],
            "suggested_action": v["suggested_action"],
            "text_excerpt": text[:80] + ("..." if len(text) > 80 else ""),
        })
        emoji = "✅" if v["passed"] else "❌"
        print(f"  {emoji} {cid} ({len(v['violations'])} 违规)")

    return results


# ========================== 报告 ==========================

def aggregate(results: list, mode: str = "dry-run") -> dict:
    if not results:
        return {
            "total": 0, "passed": 0, "failed": 0,
            "errors": 0, "warnings": 0,
            "unexpected_errors": 0, "unexpected_warnings": 0,
            "violation_types": {}, "mode": mode,
        }
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    type_counter = Counter()
    error_count = 0
    warning_count = 0
    # dry-run 中只统计「不期望的」违规：expected=pass 但实际 fail
    unexpected_errors = 0
    unexpected_warnings = 0
    for r in results:
        is_unexpected = False
        if mode == "dry-run":
            # 仅当 expected=pass 时违规算"不期望"
            if r.get("expected_outcome") == "pass":
                is_unexpected = True
        else:
            is_unexpected = True  # live 模式下任何违规都是不期望的

        for v in r.get("violations", []):
            type_counter[v["type"]] += 1
            if v["severity"] == "error":
                error_count += 1
                if is_unexpected:
                    unexpected_errors += 1
            else:
                warning_count += 1
                if is_unexpected:
                    unexpected_warnings += 1

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed * 100 / total, 1),
        "errors": error_count,
        "warnings": warning_count,
        "unexpected_errors": unexpected_errors,
        "unexpected_warnings": unexpected_warnings,
        "violation_types": dict(type_counter.most_common()),
        "mode": mode,
    }


def write_json(results, summary, mode, generated_at):
    payload = {
        "generated_at": generated_at,
        "mode": mode,
        "summary": summary,
        "results": results,
    }
    JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_md(results, summary, mode, generated_at):
    lines = []
    lines.append("# 八字 AI 输出回归评估报告")
    lines.append("")
    lines.append(f"> 生成时间：{generated_at}")
    lines.append(f"> 模式：**{mode}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、总体结果")
    lines.append("")
    lines.append(f"- 总样本数：**{summary['total']}**")
    lines.append(f"- 通过：**{summary['passed']}**")
    lines.append(f"- 失败：**{summary['failed']}**")
    lines.append(f"- 通过率：**{summary['pass_rate']}%**")
    lines.append(f"- 错误违规：**{summary['errors']}**")
    lines.append(f"- 警告违规：**{summary['warnings']}**")
    lines.append("")

    lines.append("## 二、违规类型统计")
    lines.append("")
    if summary["violation_types"]:
        lines.append("| 类型 | 出现次数 |")
        lines.append("|------|---------|")
        for k, v in summary["violation_types"].items():
            lines.append(f"| {k} | {v} |")
    else:
        lines.append("✅ 无违规。")
    lines.append("")

    lines.append("## 三、样本明细")
    lines.append("")
    lines.append("| case_id | label | passed | action | 主要违规 |")
    lines.append("|---------|-------|--------|--------|---------|")
    for r in results:
        emoji = "✅" if r["passed"] else "❌"
        v_str = "; ".join(v["detail"] for v in r["violations"][:2]) or "—"
        if len(v_str) > 70:
            v_str = v_str[:70] + "..."
        lines.append(f"| {r['case_id']} | {r['label']} | {emoji} | {r['suggested_action']} | {v_str} |")
    lines.append("")

    lines.append("## 四、最常见问题")
    lines.append("")
    if summary["violation_types"]:
        top3 = list(summary["violation_types"].items())[:3]
        for k, v in top3:
            lines.append(f"- **{k}**：出现 {v} 次")
    else:
        lines.append("无。")
    lines.append("")

    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


# ========================== 主流程 ==========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="真实调用 LLM；默认 dry-run")
    parser.add_argument("--limit", type=int, default=0, help="live 模式下最多评估几例（0=全部）")
    args = parser.parse_args()

    cases = load_standard_cases()
    cases_by_id = {c["case_id"]: c for c in cases}

    mode = "live" if args.live else "dry-run"
    print(f"模式: {mode}")

    if args.live:
        target = cases if args.limit <= 0 else cases[: args.limit]
        results = run_live(target)
    else:
        results = run_dry_run(cases_by_id)

    summary = aggregate(results, mode=mode)
    print()
    print(f"通过 {summary['passed']}/{summary['total']}, 错误违规 {summary['errors']} ({summary.get('unexpected_errors',0)} 非预期), 警告 {summary['warnings']}")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_json(results, summary, mode, generated_at)
    write_md(results, summary, mode, generated_at)
    print(f"报告: {JSON_REPORT}")
    print(f"报告: {MD_REPORT}")


if __name__ == "__main__":
    main()
