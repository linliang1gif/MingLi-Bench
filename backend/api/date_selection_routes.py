from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import date_selection_service

router = APIRouter(prefix="/api", tags=["date-selection"])


class DateSelectionIn(BaseModel):
    start_date: str
    end_date: str
    city: Optional[str] = None
    male_birth: Optional[str] = None
    female_birth: Optional[str] = None
    available_dates: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    notes: Optional[str] = None
    analysis_mode: str = "safe"


def _generate(event_type: str, payload: DateSelectionIn, db: Session) -> Dict[str, Any]:
    try:
        return date_selection_service.generate(db, event_type, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/date-selection/wedding")
def wedding(payload: DateSelectionIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("wedding", payload, db)


@router.post("/date-selection/move-in")
def move_in(payload: DateSelectionIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("move-in", payload, db)


@router.post("/date-selection/opening")
def opening(payload: DateSelectionIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("opening", payload, db)


@router.post("/date-selection/renovation")
def renovation(payload: DateSelectionIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("renovation", payload, db)


@router.post("/date-selection/bed")
def bed(payload: DateSelectionIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return _generate("bed", payload, db)
