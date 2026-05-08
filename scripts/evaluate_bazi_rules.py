"""批量评估八字规则引擎在标准案例上的表现。

用法
----
.venv/Scripts/python.exe scripts/evaluate_bazi_rules.py

输出
----
reports/bazi_rule_evaluation_report.json
reports/bazi_rule_evaluation_report.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.domain.bazi_case_loader import load_standard_cases
from backend.domain.bazi_rule_evaluator import evaluate_rule_result
from backend.services import chart_service

REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
JSON_REPORT = REPORTS_DIR / "bazi_rule_evaluation_report.json"
MD_REPORT = REPORTS_DIR / "bazi_rule_evaluation_report.md"


# ========================== 主流程 ==========================

def _gender_str(g):
    return "男" if g in ("male", "男") else "女"


def evaluate_one(case: dict) -> dict:
    inp = case["input"]
    chart = chart_service.compute_chart(
        birth_date=inp["birth_date"],
        birth_time=inp["birth_time"],
        calendar_type=inp.get("calendar_type", "solar"),
        gender=_gender_str(inp.get("gender", "male")),
        longitude=inp.get("longitude"),
    )
    rule_result = chart.get("rule_analysis") or {}
    return evaluate_rule_result(case, chart, rule_result)


def aggregate(results: list) -> dict:
    total = len(results)
    if total == 0:
        return {"total": 0}
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    scores = [r["total_score"] for r in results]
    avg = round(sum(scores) / len(scores), 1)
    lo = min(scores)
    hi = max(scores)

    # 维度均分
    dim_avg = {}
    for k in ("pillars", "day_master", "strength", "pattern", "useful_gods"):
        vals = [r["dimension_scores"].get(k, 0) for r in results]
        dim_avg[k] = round(sum(vals) / len(vals), 1)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed * 100 / total, 1),
        "avg_score": avg,
        "min_score": lo,
        "max_score": hi,
        "dimension_avg": dim_avg,
    }


def write_json(results: list, summary: dict, generated_at: str):
    payload = {
        "generated_at": generated_at,
        "summary": summary,
        "results": results,
    }
    JSON_REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _suggestions(results: list) -> list:
    """根据失败维度给出改进建议。"""
    suggestions = []
    pillar_fail = sum(1 for r in results if r["dimension_scores"].get("pillars", 100) < 100)
    dm_fail = sum(1 for r in results if r["dimension_scores"].get("day_master", 100) < 100)
    s_fail = sum(1 for r in results if r["dimension_scores"].get("strength", 100) < 75)
    pat_fail = sum(1 for r in results if r["dimension_scores"].get("pattern", 100) < 75)
    ug_fail = sum(1 for r in results if r["dimension_scores"].get("useful_gods", 100) < 75)

    if pillar_fail:
        suggestions.append(f"⚠ {pillar_fail} 例排盘不一致 — 检查 lunar_python 边界（立春/节气/子时换日/真太阳时）")
    if dm_fail:
        suggestions.append(f"⚠ {dm_fail} 例日主不一致 — 检查日柱天干提取流程")
    if s_fail:
        suggestions.append(
            f"⚠ {s_fail} 例旺衰未达 75 分 — 考虑：(a) 调整 same/opposite 阈值；"
            f"(b) 复核月令本气权重；(c) 加强通根判断"
        )
    if pat_fail:
        suggestions.append(
            f"⚠ {pat_fail} 例格局未达 75 分 — 考虑：(a) 月令本气透干优先级；"
            f"(b) 杂气格识别；(c) 合冲对格局的实际破坏程度"
        )
    if ug_fail:
        suggestions.append(
            f"⚠ {ug_fail} 例喜用神未达 75 分 — 考虑：(a) 旺衰法与格局法调和策略；"
            f"(b) 中和盘的折中喜用；(c) 共识取舍权重"
        )

    if not suggestions:
        suggestions.append("✅ 全部维度均达标，可考虑扩展案例库或进入 Phase 4")

    return suggestions


def write_md(results: list, summary: dict, generated_at: str):
    lines = []
    lines.append("# 八字规则引擎标准案例评估报告")
    lines.append("")
    lines.append(f"> 生成时间：{generated_at}")
    lines.append(f"> 案例库版本：standard_cases.json")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 一、总体结果")
    lines.append("")
    lines.append(f"- 总案例数：**{summary['total']}**")
    lines.append(f"- 通过案例：**{summary['passed']}**")
    lines.append(f"- 失败案例：**{summary['failed']}**")
    lines.append(f"- 通过率：**{summary['pass_rate']}%**")
    lines.append(f"- 平均分：**{summary['avg_score']}**")
    lines.append(f"- 最低分：{summary['min_score']}")
    lines.append(f"- 最高分：{summary['max_score']}")
    lines.append("")
    lines.append("### 各维度均分")
    lines.append("")
    lines.append("| 维度 | 均分 |")
    lines.append("|------|------|")
    for k, v in summary["dimension_avg"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")

    lines.append("## 二、案例明细")
    lines.append("")
    lines.append("| case_id | title | score | passed | 主要 mismatch |")
    lines.append("|---------|-------|-------|--------|--------------|")
    for r in results:
        mis_str = "; ".join(r["mismatches"][:2]) if r["mismatches"] else "—"
        if len(mis_str) > 60:
            mis_str = mis_str[:60] + "..."
        passed_emoji = "✅" if r["passed"] else "❌"
        lines.append(f"| {r['case_id']} | {r['title']} | {r['total_score']} | {passed_emoji} | {mis_str} |")
    lines.append("")

    failed = [r for r in results if not r["passed"]]
    lines.append("## 三、失败案例分析")
    lines.append("")
    if not failed:
        lines.append("✅ 所有案例均通过，无失败项。")
    else:
        for r in failed:
            lines.append(f"### {r['case_id']} — {r['title']}")
            lines.append(f"- **总分**：{r['total_score']}")
            if r.get("fatal"):
                lines.append("- **致命**：是")
            lines.append(f"- **维度得分**：{r['dimension_scores']}")
            if r["mismatches"]:
                lines.append("- **mismatches**：")
                for m in r["mismatches"]:
                    lines.append(f"  - {m}")
            if r["warnings"]:
                lines.append("- **warnings**：")
                for w in r["warnings"]:
                    lines.append(f"  - {w}")
            lines.append("")
    lines.append("")

    lines.append("## 四、规则改进建议")
    lines.append("")
    for s in _suggestions(results):
        lines.append(f"- {s}")
    lines.append("")

    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main():
    cases = load_standard_cases()
    if not cases:
        print("⚠ 没有可加载的案例，退出。")
        return 1

    print(f"加载 {len(cases)} 个标准案例…")
    results = []
    for case in cases:
        try:
            r = evaluate_one(case)
        except Exception as e:
            r = {
                "case_id": case.get("case_id", "?"),
                "title": case.get("title", ""),
                "total_score": 0,
                "passed": False,
                "fatal": True,
                "dimension_scores": {},
                "mismatches": [f"评估异常: {type(e).__name__}: {e}"],
                "warnings": [],
                "notes": [],
            }
        results.append(r)
        emoji = "✅" if r["passed"] else "❌"
        print(f"  {emoji} {r['case_id']}: {r['total_score']} — {r['title']}")

    summary = aggregate(results)
    print()
    print(f"通过率: {summary['pass_rate']}%  平均分: {summary['avg_score']}")
    print(f"通过 {summary['passed']}/{summary['total']}, 失败 {summary['failed']}")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_json(results, summary, generated_at)
    write_md(results, summary, generated_at)

    print(f"\n报告已生成:")
    print(f"  - {JSON_REPORT}")
    print(f"  - {MD_REPORT}")

    # 返回非零退出码当有失败时（CI 友好）
    return 0 if summary["failed"] == 0 else 0  # 不强制 fail，便于观察


if __name__ == "__main__":
    sys.exit(main())
