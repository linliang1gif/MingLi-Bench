"""导出反馈数据 + 需修正案例清单，供命理师线下审核。

用法：
    python scripts/export_feedback.py                     # 打印到终端
    python scripts/export_feedback.py --out feedback.json  # 导出 JSON
"""
import sys, json, argparse
sys.path.insert(0, ".")

from backend.db.session import SessionLocal
from backend.db.models import CaseFeedback
from backend.domain.bazi_case_loader import load_standard_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="输出 JSON 文件路径")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(CaseFeedback).order_by(CaseFeedback.id.desc()).all()
    finally:
        db.close()

    cases = load_standard_cases()
    case_map = {c["case_id"]: c for c in cases}

    feedbacks = []
    disagree_cases = {}
    for r in rows:
        fb = {
            "id": r.id,
            "case_id": r.case_id,
            "reviewer": r.reviewer,
            "reviewer_role": r.reviewer_role,
            "strength_agree": r.strength_agree,
            "strength_suggestion": r.strength_suggestion,
            "pattern_agree": r.pattern_agree,
            "pattern_suggestion": r.pattern_suggestion,
            "useful_gods_agree": r.useful_gods_agree,
            "useful_gods_note": r.useful_gods_note,
            "overall_score": r.overall_score,
            "comment": r.comment,
            "status": r.status,
            "created_at": str(r.created_at),
        }
        feedbacks.append(fb)

        if r.strength_agree == "disagree" or r.pattern_agree == "disagree":
            if r.case_id not in disagree_cases:
                disagree_cases[r.case_id] = {
                    "case": case_map.get(r.case_id, {}),
                    "corrections": [],
                }
            disagree_cases[r.case_id]["corrections"].append({
                "reviewer": r.reviewer,
                "role": r.reviewer_role,
                "strength_suggestion": r.strength_suggestion,
                "pattern_suggestion": r.pattern_suggestion,
                "comment": r.comment,
            })

    report = {
        "total_feedbacks": len(feedbacks),
        "total_cases": len(cases),
        "cases_needing_correction": len(disagree_cases),
        "feedbacks": feedbacks,
        "correction_details": disagree_cases,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"已导出到 {args.out}")
    else:
        print(f"反馈总数: {len(feedbacks)}")
        print(f"案例总数: {len(cases)}")
        print(f"需修正案例: {len(disagree_cases)}")
        if disagree_cases:
            print("\n--- 需修正的案例 ---")
            for cid, info in disagree_cases.items():
                title = info["case"].get("title", "?")
                n = len(info["corrections"])
                print(f"  {cid}: {title} ({n} 条不同意)")
        else:
            print("暂无需修正的案例。")


if __name__ == "__main__":
    main()
