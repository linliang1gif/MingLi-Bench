"""Knowledge base coverage and quality checks."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import KnowledgeBook, KnowledgeChunk
from . import knowledge_service, report_reference_service


REQUIRED_REPORT_TYPES = [
    "bazi_report",
    "fengshui_basic_report",
    "fengshui_xuankong_report",
    "fengshui_photo_report",
    "landscape_photo_report",
    "heritage_risk_record_report",
    "date_selection_report",
    "naming_report",
    "word_divination_report",
    "lottery_report",
    "yinzhai_study_report",
    "tianxing_fengshui_report",
]

LOW_CATEGORY_CHUNK_THRESHOLD = 5
LOW_REPORT_CHUNK_THRESHOLD = 5


def _parse_list_field(value: Optional[str]) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    for sep in ("，", "、", ";", "；"):
        text = text.replace(sep, ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _book_label(row: KnowledgeBook) -> Dict[str, Any]:
    return {
        "book_id": row.id,
        "title": row.title,
        "category_code": row.category_code,
        "reliability_level": row.reliability_level,
        "risk_level": row.risk_level,
    }


def quality_check(db: Session) -> Dict[str, Any]:
    books = db.scalars(select(KnowledgeBook).order_by(KnowledgeBook.id.asc())).all()
    chunks = db.scalars(select(KnowledgeChunk).order_by(KnowledgeChunk.id.asc())).all()

    books_by_id = {book.id: book for book in books}
    category_chunks: Dict[str, Set[int]] = defaultdict(set)
    category_books: Dict[str, Set[int]] = defaultdict(set)
    module_chunks: Dict[str, Set[int]] = defaultdict(set)
    module_books: Dict[str, Set[int]] = defaultdict(set)

    empty_chunks: List[Dict[str, Any]] = []
    incomplete_chunks: List[Dict[str, Any]] = []

    for chunk in chunks:
        book = books_by_id.get(chunk.book_id)
        category = book.category_code if book else "unknown"
        category_chunks[category].add(chunk.id)
        category_books[category].add(chunk.book_id)

        tags = _parse_list_field(chunk.tags)
        modules = _parse_list_field(chunk.applicable_modules)
        if not (chunk.original_text or "").strip():
            empty_chunks.append({"chunk_id": chunk.id, "book_id": chunk.book_id})
        missing_fields = []
        for field_name, value in (
            ("original_text", chunk.original_text),
            ("explanation", chunk.explanation),
            ("tags", tags),
            ("applicable_modules", modules),
            ("source_ref", chunk.source_ref),
        ):
            if not value:
                missing_fields.append(field_name)
        if missing_fields:
            incomplete_chunks.append(
                {
                    "chunk_id": chunk.id,
                    "book_id": chunk.book_id,
                    "book_title": book.title if book else None,
                    "missing_fields": missing_fields,
                }
            )

        for module in modules:
            module_chunks[module].add(chunk.id)
            module_books[module].add(chunk.book_id)

    by_category = []
    for category_code in sorted(category_chunks.keys()):
        book_ids = category_books[category_code]
        by_category.append(
            {
                "category_code": category_code,
                "books_count": len(book_ids),
                "chunks_count": len(category_chunks[category_code]),
                "sample_books": [
                    _book_label(books_by_id[book_id])
                    for book_id in sorted(book_ids)
                    if book_id in books_by_id
                ][:5],
            }
        )

    by_report_type: Dict[str, Dict[str, Any]] = {}
    missing_report_types: List[str] = []
    for report_type in REQUIRED_REPORT_TYPES:
        mapped_categories = report_reference_service.REPORT_TYPE_CATEGORY_MAP.get(report_type, [])
        exact_chunk_ids = set(module_chunks.get(report_type, set()))
        category_chunk_ids: Set[int] = set()
        category_book_ids: Set[int] = set()
        for category_code in mapped_categories:
            category_chunk_ids.update(category_chunks.get(category_code, set()))
            category_book_ids.update(category_books.get(category_code, set()))
        combined_chunk_ids = exact_chunk_ids | category_chunk_ids
        combined_book_ids = set(module_books.get(report_type, set())) | category_book_ids
        entry = {
            "report_type": report_type,
            "chunks_count": len(combined_chunk_ids),
            "exact_module_chunks_count": len(exact_chunk_ids),
            "mapped_category_chunks_count": len(category_chunk_ids),
            "books_count": len(combined_book_ids),
            "mapped_categories": mapped_categories,
            "sample_books": [
                _book_label(books_by_id[book_id])
                for book_id in sorted(combined_book_ids)
                if book_id in books_by_id
            ][:6],
        }
        by_report_type[report_type] = entry
        if entry["chunks_count"] < LOW_REPORT_CHUNK_THRESHOLD:
            missing_report_types.append(report_type)

    category_report_types: Dict[str, Set[str]] = defaultdict(set)
    for report_type in REQUIRED_REPORT_TYPES:
        for category_code in report_reference_service.REPORT_TYPE_CATEGORY_MAP.get(report_type, []):
            category_report_types[category_code].add(report_type)

    low_coverage_categories = []
    for category_code in sorted(category_report_types.keys()):
        chunks_count = len(category_chunks.get(category_code, set()))
        if chunks_count < LOW_CATEGORY_CHUNK_THRESHOLD:
            low_coverage_categories.append(
                {
                    "category_code": category_code,
                    "chunks_count": chunks_count,
                    "report_types": sorted(category_report_types[category_code]),
                }
            )

    duplicate_books = []
    title_counts = Counter((book.title or "").strip() for book in books if (book.title or "").strip())
    for title, count in sorted(title_counts.items()):
        if count <= 1:
            continue
        matched = [book for book in books if (book.title or "").strip() == title]
        duplicate_books.append(
            {
                "title": title,
                "count": count,
                "book_ids": [book.id for book in matched],
                "categories": sorted({book.category_code for book in matched if book.category_code}),
            }
        )

    return {
        "books_count": len(books),
        "chunks_count": len(chunks),
        "by_category": by_category,
        "by_report_type": by_report_type,
        "missing_report_types": missing_report_types,
        "low_coverage_categories": low_coverage_categories,
        "duplicate_books": duplicate_books,
        "empty_chunks_count": len(empty_chunks),
        "empty_chunks": empty_chunks[:50],
        "incomplete_chunks_count": len(incomplete_chunks),
        "incomplete_chunks": incomplete_chunks[:50],
        "thresholds": {
            "low_category_chunks": LOW_CATEGORY_CHUNK_THRESHOLD,
            "low_report_chunks": LOW_REPORT_CHUNK_THRESHOLD,
        },
    }
