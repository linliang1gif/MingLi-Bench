"""根据反馈修正 standard_cases.json 中的 primary_* 字段。

逻辑：
1. 查询所有 disagree 反馈
2. 对每个 case_id，按 reviewer_role 权重投票：
   - master: 3 票, expert: 2 票, user: 1 票
3. 若修正票数 > 当前 primary 票数，则替换 primary
4. 输出变更清单，--apply 参数时写入文件

用法：
    python scripts/apply_corrections.py            # 预览变更
    python scripts/apply_corrections.py --apply    # 写入 standard_cases.json
"""
import sys, json, argparse
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, ".")

from backend.db.session import SessionLocal
from backend.db.models import CaseFeedback

CASES_PATH = Path("backend/domain/fixtures/bazi_cases/standard_cases.json")

ROLE_WEIGHT = {"master": 3, "expert": 2, "user": 1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写入文件")
    parser.add_argument("--min-weight", type=int, default=3,
                        help="最低权重阈值，达到此权重才考虑修正 (默认 3)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(CaseFeedback).filter(
            (CaseFeedback.strength_agree == "disagree") |
            (CaseFeedback.pattern_agree == "disagree")
        ).all()
    finally:
        db.close()

    if not rows:
        print("暂无 disagree 反馈，无需修正。")
        return

    # 按 case_id 聚合
    case_votes = defaultdict(lambda: {
        "strength": defaultdict(int),  # suggestion -> weighted_votes
        "pattern": defaultdict(int),
    })

    for r in rows:
        w = ROLE_WEIGHT.get(r.reviewer_role, 1)
        if r.strength_agree == "disagree" and r.strength_suggestion:
            case_votes[r.case_id]["strength"][r.strength_suggestion] += w
        if r.pattern_agree == "disagree" and r.pattern_suggestion:
            case_votes[r.case_id]["pattern"][r.pattern_suggestion] += w

    # 加载案例
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    case_map = {c["case_id"]: c for c in cases}

    changes = []
    for case_id, votes in case_votes.items():
        if case_id not in case_map:
            continue
        exp = case_map[case_id].get("expected", {})

        # 旺衰修正
        if votes["strength"]:
            best_sug = max(votes["strength"].items(), key=lambda x: x[1])
            sug_val, sug_weight = best_sug
            if sug_weight >= args.min_weight:
                old = exp.get("primary_strength_level")
                if old != sug_val:
                    changes.append({
                        "case_id": case_id,
                        "field": "primary_strength_level",
                        "old": old,
                        "new": sug_val,
                        "weight": sug_weight,
                    })
                    if args.apply:
                        exp["primary_strength_level"] = sug_val
                        # 确保新值在 accepted 里
                        acc = exp.get("accepted_strength_levels", [])
                        if sug_val not in acc:
                            acc.append(sug_val)
                        # 从 rejected 移除
                        rej = exp.get("rejected_strength_levels", [])
                        if sug_val in rej:
                            rej.remove(sug_val)

        # 格局修正
        if votes["pattern"]:
            best_sug = max(votes["pattern"].items(), key=lambda x: x[1])
            sug_val, sug_weight = best_sug
            if sug_weight >= args.min_weight:
                old = exp.get("primary_pattern")
                if old != sug_val:
                    changes.append({
                        "case_id": case_id,
                        "field": "primary_pattern",
                        "old": old,
                        "new": sug_val,
                        "weight": sug_weight,
                    })
                    if args.apply:
                        exp["primary_pattern"] = sug_val
                        acc = exp.get("accepted_patterns", [])
                        if sug_val not in acc:
                            acc.append(sug_val)
                        rej = exp.get("rejected_patterns", [])
                        if sug_val in rej:
                            rej.remove(sug_val)

    # 输出
    if not changes:
        print("有 disagree 反馈但权重未达阈值或建议值与现有相同，暂不修正。")
        print(f"  (阈值: {args.min_weight}, 当前反馈 {len(rows)} 条涉及 {len(case_votes)} 个案例)")
        return

    print(f"=== 修正清单 ({len(changes)} 项) ===\n")
    for ch in changes:
        arrow = f"{ch['old']} → {ch['new']}"
        print(f"  {ch['case_id']}.{ch['field']}: {arrow}  (权重: {ch['weight']})")

    if args.apply:
        CASES_PATH.write_text(
            json.dumps(cases, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ 已写入 {CASES_PATH}")
        print("   建议重新跑 python scripts/_eval_accuracy.py 查看更新后的准确率。")
    else:
        print(f"\n预览模式。加 --apply 写入文件。(--min-weight {args.min_weight})")


if __name__ == "__main__":
    main()
