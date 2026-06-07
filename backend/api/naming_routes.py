from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import naming_service

router = APIRouter(prefix="/api", tags=["naming"])


class NamingIn(BaseModel):
    industry: Optional[str] = None
    style: Optional[str] = None
    keywords: Optional[List[str]] = None
    avoid_words: Optional[List[str]] = None
    count: int = 20
    family_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    notes: Optional[str] = None
    analysis_mode: str = "safe"


def _generate(naming_type: str, payload: NamingIn, db: Session) -> Dict[str, Any]:
    return naming_service.generate(db, naming_type, payload.model_dump())


@router.post("/naming/baby")
def baby(payload: NamingIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("baby", payload, db)


@router.post("/naming/company")
def company(payload: NamingIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("company", payload, db)


@router.post("/naming/shop")
def shop(payload: NamingIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("shop", payload, db)


@router.post("/naming/brand")
def brand(payload: NamingIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("brand", payload, db)
