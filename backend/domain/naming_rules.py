"""起名 MVP 规则。"""

from __future__ import annotations

from typing import Iterable, List


RISKY_NAME_WORDS = {"改命", "消灾", "必灵", "神", "仙"}


def is_name_safe(name: str, avoid_words: Iterable[str] | None = None) -> bool:
    bad = set(avoid_words or []) | RISKY_NAME_WORDS
    return not any(word and word in name for word in bad)


def build_name_candidates(keywords: Iterable[str] | None, count: int, suffix: str = "") -> List[str]:
    words = [w.strip() for w in (keywords or []) if str(w).strip()]
    if not words:
        words = ["易", "象", "知", "明", "和", "观", "衡", "序"]
    candidates = []
    for a in words:
        for b in words:
            if a == b:
                continue
            name = f"{a}{b}{suffix}".strip()
            if name not in candidates:
                candidates.append(name)
            if len(candidates) >= max(1, min(count, 50)):
                return candidates
    return candidates[: max(1, min(count, 50))]
