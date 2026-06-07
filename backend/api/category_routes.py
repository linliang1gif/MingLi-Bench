from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import category_service

router = APIRouter(prefix="/api", tags=["categories"])


@router.post("/categories/init")
def init_categories(db: Session = Depends(get_db)) -> Dict[str, int]:
    return category_service.init_categories(db)


@router.get("/categories")
def list_categories(enabled_only: bool = False, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return category_service.list_categories(db, enabled_only=enabled_only)
