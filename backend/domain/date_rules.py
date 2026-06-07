"""择日 MVP 规则：生成候选日期骨架，深层算法留给后续替换。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List


def date_range(start_date: str, end_date: str) -> List[str]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end_date must be after start_date")
    days = []
    cur = start
    while cur <= end and len(days) < 60:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def choose_candidate_dates(start_date: str, end_date: str, available_dates: Iterable[str] | None = None) -> dict:
    pool = [d for d in (available_dates or []) if d]
    if not pool:
        pool = date_range(start_date, end_date)
    return {
        "recommended_dates": pool[:3],
        "backup_dates": pool[3:6],
        "avoid_dates": [],
    }
