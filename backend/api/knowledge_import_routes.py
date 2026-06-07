from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import knowledge_import_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge-import"])


class ImportBookJsonIn(BaseModel):
    file_path: str = Field(..., min_length=1)
    duplicate_strategy: str = "skip"


class ImportFolderIn(BaseModel):
    folder_path: str = Field(..., min_length=1)
    duplicate_strategy: str = "skip"


@router.post("/import-book-json")
def import_book_json(payload: ImportBookJsonIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return knowledge_import_service.import_book_json(
            db,
            file_path=payload.file_path,
            duplicate_strategy=payload.duplicate_strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/import-folder")
def import_folder(payload: ImportFolderIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return knowledge_import_service.import_folder(
            db,
            folder_path=payload.folder_path,
            duplicate_strategy=payload.duplicate_strategy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/import-logs")
def import_logs(limit: int = 50, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return knowledge_import_service.list_import_logs(db, limit=limit)


@router.get("/import-sample-format")
def import_sample_format() -> Dict[str, Any]:
    return knowledge_import_service.sample_format()
