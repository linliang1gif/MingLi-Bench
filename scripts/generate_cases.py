"""批量生成标准案例，补齐覆盖盲区。

策略：遍历大量出生日期，按 日主×月支×旺衰×格局 矩阵挑选，
自动用规则引擎标注 primary/accepted/rejected，confidence 全部标 auto-low。

用法：
    python scripts/generate_cases.py            # 预览
    python scripts/generate_cases.py --write    # 写入 standard_cases.json
"""
import sys, json, copy, random, itertools
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, ".")

from backend.services import chart_service
from backend.domain.bazi_rules import GAN_WUXING, TIAN_GAN, DI_ZHI

# ========================== 配置 ==========================

CASES_PATH = Path("backend/domain/fixtures/bazi_cases/standard_cases.json")

# 目标：每个日主至少 10 例，总计 100+
TARGET_PER_DM = 10
# 每个月支至少 6 例
TARGET_PER_MONTH = 6
# 每种旺衰至少 8 例
TARGET_PER_STRENGTH = 8
# 每种格局至少 4 例
TARGET_PER_PATTERN = 4

# 旺衰级别邻接映射（用于生成 accepted/rejected）
STRENGTH_ORDER = ["身强", "偏强", "中和", "偏弱", "身弱"]
SPECIAL_STRENGTHS = ["疑似从强", "疑似从弱"]

ALL_PATTERNS = [
    "建禄格", "月劫格", "正官格", "七杀格", "食神格",
    "伤官格", "正财格", "偏财格", "正印格", "偏印格",
]

# ========================== 工具 ==========================

def adjacent_strengths(level):
    """返回相邻 ±1 的旺衰级别作为 accepted。"""
    if level in SPECIAL_STRENGTHS:
        return [level]
    try:
        idx = STRENGTH_ORDER.index(level)
    except ValueError:
        return [level]
    acc = [level]
    if idx > 0:
        acc.append(STRENGTH_ORDER[idx - 1])
    if idx < len(STRENGTH_ORDER) - 1:
        acc.append(STRENGTH_ORDER[idx + 1])
    return acc


def rejected_strengths(level):
    """返回距离 ≥2 的旺衰级别作为 rejected。"""
    acc = set(adjacent_strengths(level))
    all_set = set(STRENGTH_ORDER + SPECIAL_STRENGTHS)
    return sorted(all_set - acc)


def rejected_patterns(pattern):
    """返回与当前格局明显冲突的格局。"""
    rej = []
    for p in ALL_PATTERNS:
        if p != pattern:
            # 建禄/月劫 互相不排斥
            if {p, pattern} <= {"建禄格", "月劫格"}:
                continue
            rej.append(p)
    # 只排斥差距大的，保留 3-4 个
    return rej[:4]


def make_case(case_id, chart, inp, gender):
    """从 chart + rule_analysis 构建一个标准案例。"""
    ra = chart.get("rule_analysis") or {}
    pillars = chart.get("pillars") or {}

    # 四柱字符串
    pdict = {}
    for k in ("year", "month", "day", "hour"):
        cell = pillars.get(k, {})
        pdict[k] = (cell.get("stem", "") + cell.get("branch", ""))

    day_master = pillars.get("day", {}).get("stem", "?")
    strength_level = ra.get("strength", {}).get("strength_level", "uncertain")
    pattern = ra.get("pattern", {}).get("pattern", "uncertain")
    month_branch = pillars.get("month", {}).get("branch", "?")

    # 映射 uncertain → 中和
    if strength_level == "uncertain":
        strength_level = "中和"

    acc_str = adjacent_strengths(strength_level)
    rej_str = rejected_strengths(strength_level)

    # 喜用神
    ug = ra.get("useful_gods", {})
    final = ug.get("final_suggestion", {})
    use_elements = final.get("useful", [])
    avoid_elements = final.get("avoid", [])

    # 格局 rejected
    rej_pat = rejected_patterns(pattern) if pattern not in ("uncertain",) else []
    acc_pat = [pattern] if pattern not in ("uncertain",) else []

    title_dm = f"{day_master}{'日主' if day_master != '?' else ''}"
    title_month = f"生{month_branch}月" if month_branch != "?" else ""
    title_str = strength_level
    title_pat = pattern if pattern not in ("uncertain",) else "待定格局"

    return {
        "case_id": case_id,
        "title": f"{title_dm}{title_month} — {title_pat}，{title_str}",
        "source": "auto_generated",
        "source_note": "由 generate_cases.py 脚本自动生成，规则引擎 v3 自动标注，未经命理师审核。",
        "confidence": "auto-low",
        "input": {
            "gender": gender,
            "calendar_type": "solar",
            "birth_date": inp["birth_date"],
            "birth_time": inp["birth_time"],
            "birth_place": "未指定",
            "longitude": None,
        },
        "expected": {
            "pillars": pdict,
            "day_master": day_master,
            "primary_strength_level": strength_level,
            "accepted_strength_levels": acc_str,
            "rejected_strength_levels": rej_str,
            "primary_pattern": pattern,
            "accepted_patterns": acc_pat,
            "rejected_patterns": rej_pat,
            "accepted_useful_elements": use_elements[:4],
            "accepted_avoid_elements": avoid_elements[:3],
            "allow_conflict": True,
            "dispute_notes": [
                "此案例由规则引擎自动标注，需命理师审核 primary_strength_level 和 primary_pattern。"
            ],
        },
        "notes": f"自动生成案例。日主{day_master}，月支{month_branch}，规则引擎判定：{strength_level}/{pattern}。",
    }


# ========================== 扫描候选日期 ==========================

def scan_candidates():
    """扫描一批日期，生成候选图谱。"""
    candidates = []
    hours = ["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"]

    # 覆盖 1960-2010，每隔 3 天取一天
    start = date(1960, 1, 1)
    end = date(2010, 12, 31)
    d = start
    count = 0
    while d <= end:
        for h in hours:
            gender = "male" if count % 2 == 0 else "female"
            try:
                chart = chart_service.compute_chart(
                    birth_date=d.isoformat(),
                    birth_time=h,
                    calendar_type="solar",
                    gender=gender,
                )
            except Exception:
                continue

            if not chart.get("available"):
                continue

            pillars = chart.get("pillars", {})
            ra = chart.get("rule_analysis", {})
            dm = pillars.get("day", {}).get("stem", "?")
            mz = pillars.get("month", {}).get("branch", "?")
            sl = (ra.get("strength", {}).get("strength_level", "uncertain"))
            pat = (ra.get("pattern", {}).get("pattern", "uncertain"))

            candidates.append({
                "dm": dm, "mz": mz, "sl": sl, "pat": pat,
                "inp": {"birth_date": d.isoformat(), "birth_time": h},
                "gender": gender, "chart": chart,
            })
            count += 1

        d += timedelta(days=3)

    return candidates


def select_cases(candidates, existing_cases):
    """从候选中按覆盖矩阵挑选，补齐盲区。贪心：每次选最需要的一条。"""
    # 统计现有覆盖
    dm_count = {}; mz_count = {}; sl_count = {}; pat_count = {}
    for c in existing_cases:
        exp = c.get("expected", {})
        dm = exp.get("day_master", "?")
        pat = exp.get("primary_pattern", "?")
        sl = exp.get("primary_strength_level", "?")
        dm_count[dm] = dm_count.get(dm, 0) + 1
        pat_count[pat] = pat_count.get(pat, 0) + 1
        sl_count[sl] = sl_count.get(sl, 0) + 1

    for c in existing_cases:
        inp = c["input"]
        try:
            chart = chart_service.compute_chart(
                birth_date=inp["birth_date"], birth_time=inp["birth_time"],
                calendar_type=inp.get("calendar_type", "solar"),
                gender=inp.get("gender", "male"),
            )
            mz = chart.get("pillars", {}).get("month", {}).get("branch", "?")
            mz_count[mz] = mz_count.get(mz, 0) + 1
        except Exception:
            pass

    # 打乱候选顺序
    random.seed(42)
    random.shuffle(candidates)

    # 硬上限：防止单维度过度集中
    DM_CAP = 12
    MZ_CAP = 12
    SL_CAP = 25
    PAT_CAP = 15

    selected = []
    used_keys = set()  # 去重: birth_date+birth_time

    def need_score(cand):
        dm, mz, sl, pat = cand["dm"], cand["mz"], cand["sl"], cand["pat"]
        # 超上限直接排除
        if dm_count.get(dm, 0) >= DM_CAP:
            return -1
        if mz_count.get(mz, 0) >= MZ_CAP:
            return -1
        if sl_count.get(sl, 0) >= SL_CAP:
            return -1
        if pat_count.get(pat, 0) >= PAT_CAP:
            return -1

        score = 0
        # 越缺的越优先
        if dm_count.get(dm, 0) < TARGET_PER_DM:
            score += (TARGET_PER_DM - dm_count.get(dm, 0)) * 2
        if mz_count.get(mz, 0) < TARGET_PER_MONTH:
            score += (TARGET_PER_MONTH - mz_count.get(mz, 0))
        if sl_count.get(sl, 0) < TARGET_PER_STRENGTH:
            score += (TARGET_PER_STRENGTH - sl_count.get(sl, 0)) * 1.5
        if pat_count.get(pat, 0) < TARGET_PER_PATTERN:
            score += (TARGET_PER_PATTERN - pat_count.get(pat, 0))
        # 非"中和"旺衰加分（中和太多没意义）
        if sl not in ("中和", "uncertain"):
            score += 5
        # 完全缺失的日主超高优先
        if dm_count.get(dm, 0) == 0:
            score += 20
        return score

    # 贪心循环：每轮找当前最需要的
    remaining = [c for c in candidates if c["pat"] != "uncertain"]

    while len(selected) < 85 and remaining:
        best_idx = -1
        best_score = -1
        for i, cand in enumerate(remaining):
            key = f"{cand['inp']['birth_date']}_{cand['inp']['birth_time']}"
            if key in used_keys:
                continue
            s = need_score(cand)
            if s > best_score:
                best_score = s
                best_idx = i

        if best_idx < 0 or best_score <= 0:
            break

        cand = remaining.pop(best_idx)
        key = f"{cand['inp']['birth_date']}_{cand['inp']['birth_time']}"
        used_keys.add(key)
        selected.append(cand)

        dm, mz, sl, pat = cand["dm"], cand["mz"], cand["sl"], cand["pat"]
        dm_count[dm] = dm_count.get(dm, 0) + 1
        mz_count[mz] = mz_count.get(mz, 0) + 1
        sl_count[sl] = sl_count.get(sl, 0) + 1
        pat_count[pat] = pat_count.get(pat, 0) + 1

    return selected, dm_count, mz_count, sl_count, pat_count


# ========================== 主流程 ==========================

def main():
    write_mode = "--write" in sys.argv

    print("加载现有案例...")
    existing = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    existing_count = len(existing)
    max_id = max(int(c["case_id"].replace("case_", "")) for c in existing)
    print(f"  现有: {existing_count} 例, 最大 ID: case_{max_id:03d}")

    print("扫描候选日期（1960-2010, 每 3 天 × 6 时辰）...")
    candidates = scan_candidates()
    print(f"  候选: {len(candidates)} 条")

    print("按覆盖矩阵选择...")
    selected, dm_c, mz_c, sl_c, pat_c = select_cases(candidates, existing)
    print(f"  选中: {len(selected)} 条新案例\n")

    # 生成案例对象
    new_cases = []
    for i, cand in enumerate(selected):
        cid = f"case_{max_id + 1 + i:03d}"
        case = make_case(cid, cand["chart"], cand["inp"], cand["gender"])
        new_cases.append(case)

    # 打印覆盖矩阵
    print("=== 扩充后覆盖矩阵 ===")
    print("\n日主:")
    for g in "甲乙丙丁戊己庚辛壬癸":
        print(f"  {g}: {dm_c.get(g, 0)}")
    print("\n月支:")
    for z in "子丑寅卯辰巳午未申酉戌亥":
        print(f"  {z}: {mz_c.get(z, 0)}")
    print("\n旺衰:")
    for k, v in sorted(sl_c.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print("\n格局:")
    for k, v in sorted(pat_c.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    total = existing_count + len(new_cases)
    print(f"\n总计: {existing_count} (旧) + {len(new_cases)} (新) = {total} 例")

    if write_mode:
        merged = existing + new_cases
        CASES_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ 已写入 {CASES_PATH} ({total} 例)")
    else:
        print("\n预览模式。加 --write 写入文件。")
        # 打印前 5 个新案例 ID + 标题
        for c in new_cases[:5]:
            print(f"  {c['case_id']}: {c['title']}")
        if len(new_cases) > 5:
            print(f"  ... 共 {len(new_cases)} 条")


if __name__ == "__main__":
    main()
