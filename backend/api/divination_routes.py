from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import divination_service

router = APIRouter(prefix="/api", tags=["divination"])


class WordDivinationIn(BaseModel):
    word: str = Field(..., min_length=1, max_length=4)
    question: str = Field(..., min_length=1)
    context: Optional[str] = None
    analysis_mode: str = "safe"


class LotteryIn(BaseModel):
    question: str = Field(..., min_length=1)
    sign_no: Optional[int] = None
    analysis_mode: str = "safe"


@router.post("/divination/word")
def word(payload: WordDivinationIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return divination_service.word_divination(db, payload.model_dump())


@router.post("/divination/lottery")
def lottery(payload: LotteryIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return divination_service.lottery(db, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
