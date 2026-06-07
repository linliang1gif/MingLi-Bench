"""古籍知识库：书籍、分片与 LIKE 搜索。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..db.models import KnowledgeBook, KnowledgeChunk


SEED_PATH: Path = settings.project_root / "backend" / "data" / "knowledge_seed.json"


def _book(row: KnowledgeBook) -> Dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "alias": row.alias,
        "category_code": row.category_code,
        "author": row.author,
        "dynasty": row.dynasty,
        "version": row.version,
        "source": row.source,
        "copyright_status": row.copyright_status,
        "reliability_level": row.reliability_level,
        "risk_level": row.risk_level,
        "description": row.description,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


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


def normalize_list_field(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        items = _parse_list_field(str(value))
    if not items:
        return None
    return json.dumps(items, ensure_ascii=False)


def _chunk(row: KnowledgeChunk) -> Dict[str, Any]:
    book = row.book
    return {
        "id": row.id,
        "chunk_id": row.id,
        "book_id": row.book_id,
        "book_title": book.title if book else None,
        "category_code": book.category_code if book else None,
        "chapter": row.chapter,
        "section": row.section,
        "original_text": row.original_text,
        "explanation": row.explanation,
        "tags": _parse_list_field(row.tags),
        "applicable_modules": _parse_list_field(row.applicable_modules),
        "source_ref": row.source_ref,
        "reliability_level": book.reliability_level if book else None,
        "risk_level": book.risk_level if book else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return _parse_list_field(str(value))


def _like_any(column: Any, values: Iterable[str]) -> List[Any]:
    return [column.like(f"%{value}%") for value in values if value]


def list_books(
    db: Session,
    query: Optional[str] = None,
    category_code: Optional[str] = None,
    reliability_level: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> List[Dict[str, Any]]:
    stmt = select(KnowledgeBook).order_by(KnowledgeBook.id.desc())
    if category_code:
        stmt = stmt.where(KnowledgeBook.category_code == category_code)
    if reliability_level:
        stmt = stmt.where(KnowledgeBook.reliability_level == reliability_level)
    if risk_level:
        stmt = stmt.where(KnowledgeBook.risk_level == risk_level)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(
            or_(
                KnowledgeBook.title.like(like),
                KnowledgeBook.alias.like(like),
                KnowledgeBook.description.like(like),
            )
        )
    return [_book(row) for row in db.scalars(stmt).all()]


def create_book(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = KnowledgeBook(
        title=payload["title"],
        alias=payload.get("alias"),
        category_code=payload["category_code"],
        author=payload.get("author"),
        dynasty=payload.get("dynasty"),
        version=payload.get("version"),
        source=payload.get("source"),
        copyright_status=payload.get("copyright_status"),
        reliability_level=payload.get("reliability_level") or "C",
        risk_level=payload.get("risk_level") or "medium",
        description=payload.get("description"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _book(row)


def get_book(db: Session, book_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(KnowledgeBook, book_id)
    return _book(row) if row else None


def create_chunk(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = KnowledgeChunk(
        book_id=payload["book_id"],
        chapter=payload.get("chapter"),
        section=payload.get("section"),
        original_text=payload["original_text"],
        explanation=payload.get("explanation"),
        tags=normalize_list_field(payload.get("tags")),
        applicable_modules=normalize_list_field(payload.get("applicable_modules")),
        source_ref=payload.get("source_ref"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _chunk(row)


def list_chunks(db: Session, book_id: int) -> List[Dict[str, Any]]:
    rows = db.scalars(
        select(KnowledgeChunk).where(KnowledgeChunk.book_id == book_id).order_by(KnowledgeChunk.id.desc())
    ).all()
    return [_chunk(row) for row in rows]


def search(
    db: Session,
    query: Optional[str] = None,
    category_code: Optional[str] = None,
    book_id: Optional[int] = None,
    tags: Optional[Sequence[str] | str] = None,
    applicable_module: Optional[str] = None,
    reliability_level: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    terms = [t for t in (query or "").split() if t]
    if not terms:
        terms = [query] if query else []
    stmt = select(KnowledgeChunk).join(KnowledgeBook)
    if book_id:
        stmt = stmt.where(KnowledgeChunk.book_id == int(book_id))
    if category_code:
        stmt = stmt.where(KnowledgeBook.category_code == category_code)
    if reliability_level:
        stmt = stmt.where(KnowledgeBook.reliability_level == reliability_level)
    if risk_level:
        stmt = stmt.where(KnowledgeBook.risk_level == risk_level)
    tag_values = _as_list(tags)
    if tag_values:
        stmt = stmt.where(or_(*_like_any(KnowledgeChunk.tags, tag_values)))
    if applicable_module:
        stmt = stmt.where(KnowledgeChunk.applicable_modules.like(f"%{applicable_module}%"))

    keyword_filters = []
    for term in terms:
        if not term:
            continue
        like = f"%{term}%"
        keyword_filters.extend(
            [
                KnowledgeChunk.chapter.like(like),
                KnowledgeChunk.section.like(like),
                KnowledgeChunk.original_text.like(like),
                KnowledgeChunk.explanation.like(like),
                KnowledgeChunk.tags.like(like),
                KnowledgeChunk.applicable_modules.like(like),
                KnowledgeChunk.source_ref.like(like),
                KnowledgeBook.title.like(like),
                KnowledgeBook.alias.like(like),
                KnowledgeBook.description.like(like),
            ]
        )
    if keyword_filters:
        stmt = stmt.where(or_(*keyword_filters))
    safe_limit = max(1, min(int(limit or 50), 100))
    stmt = stmt.order_by(KnowledgeChunk.id.desc()).limit(safe_limit)
    rows = [_chunk(row) for row in db.scalars(stmt).all()]
    return {"results": rows, "total": len(rows)}


def init_seed(db: Session) -> Dict[str, int]:
    items = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    existing_titles = set(db.scalars(select(KnowledgeBook.title)).all())
    inserted_books = 0
    inserted_chunks = 0
    for item in items:
        if item["title"] in existing_titles:
            continue
        book = KnowledgeBook(
            title=item["title"],
            alias=item.get("alias"),
            category_code=item["category_code"],
            author=item.get("author"),
            dynasty=item.get("dynasty"),
            version=item.get("version"),
            source=item.get("source"),
            copyright_status=item.get("copyright_status"),
            reliability_level=item.get("reliability_level") or "C",
            risk_level=item.get("risk_level") or "medium",
            description=item.get("description"),
        )
        db.add(book)
        db.flush()
        inserted_books += 1
        for chunk in item.get("chunks") or []:
            db.add(
                KnowledgeChunk(
                    book_id=book.id,
                    chapter=chunk.get("chapter"),
                    section=chunk.get("section"),
                    original_text=chunk["original_text"],
                    explanation=chunk.get("explanation"),
                    tags=normalize_list_field(chunk.get("tags")),
                    applicable_modules=normalize_list_field(chunk.get("applicable_modules")),
                    source_ref=chunk.get("source_ref"),
                )
            )
            inserted_chunks += 1
    db.commit()
    return {
        "inserted_books": inserted_books,
        "inserted_chunks": inserted_chunks,
        "total_books": db.query(KnowledgeBook).count(),
        "total_chunks": db.query(KnowledgeChunk).count(),
    }
