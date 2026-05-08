"""快速评估规则引擎在 20 个标准案例上的准确率。"""
import sys, json
sys.path.insert(0, ".")

from backend.domain.bazi_case_loader import load_standard_cases
from backend.domain.bazi_rule_evaluator import evaluate_rule_result
from backend.services import chart_service

cases = load_standard_cases()
total = len(cases)
results = []

for c in cases:
    inp = c["input"]
    chart = chart_service.compute_chart(
        birth_date=inp["birth_date"],
        birth_time=inp["birth_time"],
        calendar_type=inp.get("calendar_type", "solar"),
        gender=inp.get("gender", "male"),
    )
    ra = chart.get("rule_analysis") or {}
    score = evaluate_rule_result(c, chart, ra)
    hb = score.get("hit_breakdown", {})
    s_hit = hb.get("strength", "?")
    p_hit = hb.get("pattern", "?")
    total_s = score["total_score"]
    results.append({"id": c.get("case_id", c.get("id", "?")), "pct": total_s,
                     "s": s_hit, "p": p_hit, "passed": score["passed"]})

avg = sum(r["pct"] for r in results) / len(results)

print(f"=== 标准案例评估 ({total} cases) ===")
for r in results:
    tag = "PASS" if r["passed"] else "FAIL"
    print(f"  {r['id']}: score={r['pct']:.1f}  strength={r['s']}  pattern={r['p']}  [{tag}]")
print()
passed_cnt = sum(1 for r in results if r["passed"])
strength_ok = sum(1 for r in results if r["s"] in ("primary", "accepted"))
pattern_ok = sum(1 for r in results if r["p"] in ("primary", "accepted"))
print(f"综合通过:       {passed_cnt}/{total} ({passed_cnt/total*100:.0f}%)")
print(f"身强弱判定命中: {strength_ok}/{total} ({strength_ok/total*100:.0f}%)")
print(f"格局判定命中:   {pattern_ok}/{total} ({pattern_ok/total*100:.0f}%)")
print(f"加权平均得分:   {avg:.1f}/100")
