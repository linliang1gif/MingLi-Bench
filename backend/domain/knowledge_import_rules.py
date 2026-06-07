"""Rules and validation helpers for standard knowledge book imports."""

from __future__ import annotations

from typing import Any, Dict, List


DUPLICATE_STRATEGIES = {"skip", "overwrite", "append"}
RELIABILITY_LEVELS = {"A", "B", "C"}
RISK_LEVELS = {"low", "medium", "high"}


SAMPLE_BOOK_FORMAT: Dict[str, Any] = {
    "title": "葬经",
    "alias": "葬书",
    "category_code": "13",
    "author": "郭璞",
    "dynasty": "晋",
    "version": "公版整理文本",
    "source": "本地整理",
    "copyright_status": "public_domain_or_self整理",
    "reliability_level": "A",
    "risk_level": "medium",
    "description": "风水堪舆经典之一。",
    "chunks": [
        {
            "chapter": "气感篇",
            "section": "第一段",
            "original_text": "葬者，乘生气也。",
            "explanation": "此句强调传统堪舆中对生气的重视。",
            "tags": ["阴宅", "生气", "葬法", "堪舆基础"],
            "applicable_modules": [
                "yinzhai_study_report",
                "fengshui_basic_report",
                "knowledge",
            ],
            "source_ref": "葬经·气感篇",
        }
    ],
}


def validate_duplicate_strategy(value: str) -> str:
    strategy = (value or "skip").strip().lower()
    if strategy not in DUPLICATE_STRATEGIES:
        raise ValueError("duplicate_strategy must be one of: skip, overwrite, append")
    return strategy


def _ensure_list(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value
        for sep in ("，", "、", ";", "；"):
            text = text.replace(sep, ",")
        return [item.strip() for item in text.split(",") if item.strip()]
    raise ValueError(f"{field_name} must be an array or comma-separated string")


def normalize_book_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("book JSON root must be an object")
    if not str(payload.get("title") or "").strip():
        raise ValueError("book.title is required")
    if not str(payload.get("category_code") or "").strip():
        raise ValueError("book.category_code is required")

    reliability = str(payload.get("reliability_level") or "C").strip().upper()
    if reliability not in RELIABILITY_LEVELS:
        raise ValueError("book.reliability_level must be A, B, or C")
    risk = str(payload.get("risk_level") or "medium").strip().lower()
    if risk not in RISK_LEVELS:
        raise ValueError("book.risk_level must be low, medium, or high")

    chunks = payload.get("chunks") or []
    if not isinstance(chunks, list):
        raise ValueError("book.chunks must be an array")

    normalized_chunks: List[Dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            raise ValueError(f"chunk #{index} must be an object")
        original_text = str(chunk.get("original_text") or "").strip()
        if not original_text:
            raise ValueError(f"chunk #{index}.original_text is required")
        normalized_chunks.append(
            {
                "chapter": (str(chunk.get("chapter")).strip() if chunk.get("chapter") else None),
                "section": (str(chunk.get("section")).strip() if chunk.get("section") else None),
                "original_text": original_text,
                "explanation": (
                    str(chunk.get("explanation")).strip() if chunk.get("explanation") else None
                ),
                "tags": _ensure_list(chunk.get("tags"), f"chunk #{index}.tags"),
                "applicable_modules": _ensure_list(
                    chunk.get("applicable_modules"), f"chunk #{index}.applicable_modules"
                ),
                "source_ref": (
                    str(chunk.get("source_ref")).strip() if chunk.get("source_ref") else None
                ),
            }
        )

    return {
        "title": str(payload["title"]).strip(),
        "alias": str(payload.get("alias")).strip() if payload.get("alias") else None,
        "category_code": str(payload["category_code"]).strip(),
        "author": str(payload.get("author")).strip() if payload.get("author") else None,
        "dynasty": str(payload.get("dynasty")).strip() if payload.get("dynasty") else None,
        "version": str(payload.get("version")).strip() if payload.get("version") else None,
        "source": str(payload.get("source")).strip() if payload.get("source") else None,
        "copyright_status": (
            str(payload.get("copyright_status")).strip()
            if payload.get("copyright_status")
            else None
        ),
        "reliability_level": reliability,
        "risk_level": risk,
        "description": (
            str(payload.get("description")).strip() if payload.get("description") else None
        ),
        "chunks": normalized_chunks,
    }
