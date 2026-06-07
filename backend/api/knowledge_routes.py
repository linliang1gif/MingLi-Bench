from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import knowledge_quality_service, knowledge_service

router = APIRouter(prefix="/api", tags=["knowledge"])


class BookIn(BaseModel):
    title: str = Field(..., min_length=1)
    alias: Optional[str] = None
    category_code: str = Field(..., min_length=1)
    author: Optional[str] = None
    dynasty: Optional[str] = None
    version: Optional[str] = None
    source: Optional[str] = None
    copyright_status: Optional[str] = None
    reliability_level: str = "C"
    risk_level: str = "medium"
    description: Optional[str] = None


class ChunkIn(BaseModel):
    book_id: int
    chapter: Optional[str] = None
    section: Optional[str] = None
    original_text: str = Field(..., min_length=1)
    explanation: Optional[str] = None
    tags: Optional[str | List[str]] = None
    applicable_modules: Optional[str | List[str]] = None
    source_ref: Optional[str] = None


class SearchIn(BaseModel):
    query: Optional[str] = None
    category_code: Optional[str] = None
    book_id: Optional[int] = None
    tags: Optional[str | List[str]] = None
    applicable_module: Optional[str] = None
    reliability_level: Optional[str] = None
    risk_level: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=100)


@router.post("/knowledge/init")
def init_knowledge(db: Session = Depends(get_db)) -> Dict[str, int]:
    return knowledge_service.init_seed(db)


@router.get("/knowledge/books")
def list_books(
    query: Optional[str] = None,
    category_code: Optional[str] = None,
    reliability_level: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return knowledge_service.list_books(
        db,
        query=query,
        category_code=category_code,
        reliability_level=reliability_level,
        risk_level=risk_level,
    )


@router.post("/knowledge/books")
def create_book(payload: BookIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return knowledge_service.create_book(db, payload.model_dump())


@router.get("/knowledge/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = knowledge_service.get_book(db, book_id)
    if not row:
        raise HTTPException(status_code=404, detail="knowledge book not found")
    return row


@router.post("/knowledge/chunks")
def create_chunk(payload: ChunkIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return knowledge_service.create_chunk(db, payload.model_dump())


@router.get("/knowledge/books/{book_id}/chunks")
def list_chunks(book_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return knowledge_service.list_chunks(db, book_id)


@router.post("/knowledge/search")
def search(payload: SearchIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return knowledge_service.search(
        db,
        query=payload.query,
        category_code=payload.category_code,
        book_id=payload.book_id,
        tags=payload.tags,
        applicable_module=payload.applicable_module,
        reliability_level=payload.reliability_level,
        risk_level=payload.risk_level,
        limit=payload.limit,
    )


@router.get("/knowledge/quality-check")
def quality_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return knowledge_quality_service.quality_check(db)
