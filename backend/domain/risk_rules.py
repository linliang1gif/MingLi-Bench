"""风险词审核规则。"""

from __future__ import annotations

from typing import Dict, Iterable, List


def scan_text(text: str, terms: Iterable[Dict[str, object]]) -> Dict[str, object]:
    source = text or ""
    hits: List[Dict[str, object]] = []
    seen = set()
    for item in terms:
        term = str(item.get("term") or "")
        if not term or term in seen:
            continue
        if term in source:
            seen.add(term)
            hits.append(
                {
                    "term": term,
                    "category": item.get("category"),
                    "severity": item.get("severity"),
                    "replacement_suggestion": item.get("replacement_suggestion"),
                }
            )
    return {"passed": len(hits) == 0, "hits": hits, "safe_text": source}
