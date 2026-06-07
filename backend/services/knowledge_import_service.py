"""Standard JSON import service for the knowledge base."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..db.models import KnowledgeBook, KnowledgeChunk, KnowledgeImportLog
from ..domain import knowledge_import_rules
from . import knowledge_service


def _serialize_log(row: KnowledgeImportLog) -> Dict[str, Any]:
    return {
        "id": row.id,
        "import_type": row.import_type,
        "file_path": row.file_path,
        "folder_path": row.folder_path,
        "duplicate_strategy": row.duplicate_strategy,
        "books_total": row.books_total,
        "books_inserted": row.books_inserted,
        "books_skipped": row.books_skipped,
        "chunks_inserted": row.chunks_inserted,
        "status": row.status,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _resolve_local_path(raw_path: str) -> Path:
    if not raw_path or not str(raw_path).strip():
        raise ValueError("path is required")
    path = Path(str(raw_path).strip())
    if not path.is_absolute():
        path = settings.project_root / path
    return path.resolve()


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ValueError(f"file not found: {path}")
    if not path.is_file():
        raise ValueError(f"path is not a file: {path}")
    if path.suffix.lower() != ".json":
        raise ValueError("only .json files are supported")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path} ({exc})") from exc


def _add_log(
    db: Session,
    *,
    import_type: str,
    duplicate_strategy: str,
    file_path: Optional[str] = None,
    folder_path: Optional[str] = None,
    books_total: int = 0,
    books_inserted: int = 0,
    books_skipped: int = 0,
    chunks_inserted: int = 0,
    status: str = "success",
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    row = KnowledgeImportLog(
        import_type=import_type,
        file_path=file_path,
        folder_path=folder_path,
        duplicate_strategy=duplicate_strategy,
        books_total=books_total,
        books_inserted=books_inserted,
        books_skipped=books_skipped,
        chunks_inserted=chunks_inserted,
        status=status,
        error_message=error_message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_log(row)


def _find_existing_book(db: Session, title: str) -> Optional[KnowledgeBook]:
    return db.scalars(
        select(KnowledgeBook).where(KnowledgeBook.title == title).order_by(KnowledgeBook.id.asc())
    ).first()


def _apply_book_metadata(row: KnowledgeBook, payload: Dict[str, Any]) -> None:
    for key in (
        "title",
        "alias",
        "category_code",
        "author",
        "dynasty",
        "version",
        "source",
        "copyright_status",
        "reliability_level",
        "risk_level",
        "description",
    ):
        setattr(row, key, payload.get(key))


def _insert_chunks(db: Session, book_id: int, chunks: Iterable[Dict[str, Any]]) -> int:
    inserted = 0
    for chunk in chunks:
        db.add(
            KnowledgeChunk(
                book_id=book_id,
                chapter=chunk.get("chapter"),
                section=chunk.get("section"),
                original_text=chunk["original_text"],
                explanation=chunk.get("explanation"),
                tags=knowledge_service.normalize_list_field(chunk.get("tags")),
                applicable_modules=knowledge_service.normalize_list_field(
                    chunk.get("applicable_modules")
                ),
                source_ref=chunk.get("source_ref"),
            )
        )
        inserted += 1
    return inserted


def _import_book_payload(
    db: Session,
    payload: Dict[str, Any],
    duplicate_strategy: str,
) -> Dict[str, int]:
    book_data = knowledge_import_rules.normalize_book_payload(payload)
    existing = _find_existing_book(db, book_data["title"])
    if existing and duplicate_strategy == "skip":
        return {"books_inserted": 0, "books_skipped": 1, "chunks_inserted": 0}

    if existing:
        book = existing
        if duplicate_strategy == "overwrite":
            _apply_book_metadata(book, book_data)
            db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.book_id == book.id))
        elif duplicate_strategy == "append":
            _apply_book_metadata(book, book_data)
    else:
        book = KnowledgeBook()
        _apply_book_metadata(book, book_data)
        db.add(book)
        db.flush()

    chunks_inserted = _insert_chunks(db, book.id, book_data.get("chunks") or [])
    return {
        "books_inserted": 0 if existing else 1,
        "books_skipped": 0,
        "chunks_inserted": chunks_inserted,
    }


def import_book_json(
    db: Session,
    *,
    file_path: str,
    duplicate_strategy: str = "skip",
) -> Dict[str, Any]:
    strategy = knowledge_import_rules.validate_duplicate_strategy(duplicate_strategy)
    path = _resolve_local_path(file_path)
    try:
        payload = _load_json_file(path)
        result = _import_book_payload(db, payload, strategy)
        db.commit()
        log = _add_log(
            db,
            import_type="single_book",
            file_path=str(path),
            duplicate_strategy=strategy,
            books_total=1,
            books_inserted=result["books_inserted"],
            books_skipped=result["books_skipped"],
            chunks_inserted=result["chunks_inserted"],
            status="success",
        )
        return {"ok": True, **result, "books_total": 1, "log": log}
    except Exception as exc:
        db.rollback()
        log = _add_log(
            db,
            import_type="single_book",
            file_path=str(path),
            duplicate_strategy=strategy,
            books_total=1,
            status="failed",
            error_message=str(exc),
        )
        raise ValueError(str(exc)) from exc


def import_folder(
    db: Session,
    *,
    folder_path: str,
    duplicate_strategy: str = "skip",
) -> Dict[str, Any]:
    strategy = knowledge_import_rules.validate_duplicate_strategy(duplicate_strategy)
    folder = _resolve_local_path(folder_path)
    if not folder.exists():
        log = _add_log(
            db,
            import_type="folder",
            folder_path=str(folder),
            duplicate_strategy=strategy,
            status="failed",
            error_message=f"folder not found: {folder}",
        )
        raise ValueError(log["error_message"])
    if not folder.is_dir():
        log = _add_log(
            db,
            import_type="folder",
            folder_path=str(folder),
            duplicate_strategy=strategy,
            status="failed",
            error_message=f"path is not a folder: {folder}",
        )
        raise ValueError(log["error_message"])

    files = sorted(path for path in folder.glob("*.json") if path.is_file())
    totals = {
        "books_total": len(files),
        "books_inserted": 0,
        "books_skipped": 0,
        "chunks_inserted": 0,
    }
    errors: List[str] = []
    try:
        for path in files:
            try:
                payload = _load_json_file(path)
                result = _import_book_payload(db, payload, strategy)
                totals["books_inserted"] += result["books_inserted"]
                totals["books_skipped"] += result["books_skipped"]
                totals["chunks_inserted"] += result["chunks_inserted"]
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        status = "partial_success" if errors else "success"
        db.commit()
        log = _add_log(
            db,
            import_type="folder",
            folder_path=str(folder),
            duplicate_strategy=strategy,
            status=status,
            error_message="\n".join(errors) if errors else None,
            **totals,
        )
        return {"ok": not errors, **totals, "errors": errors, "log": log}
    except Exception as exc:
        db.rollback()
        log = _add_log(
            db,
            import_type="folder",
            folder_path=str(folder),
            duplicate_strategy=strategy,
            status="failed",
            error_message=str(exc),
            **totals,
        )
        raise ValueError(str(exc)) from exc


def list_import_logs(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 50), 200))
    rows = db.scalars(
        select(KnowledgeImportLog).order_by(KnowledgeImportLog.id.desc()).limit(safe_limit)
    ).all()
    return [_serialize_log(row) for row in rows]


def sample_format() -> Dict[str, Any]:
    return knowledge_import_rules.SAMPLE_BOOK_FORMAT
