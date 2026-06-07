from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import xuankong_service

router = APIRouter(prefix="/api/xuankong", tags=["xuankong"])


class XuanKongCalculateIn(BaseModel):
    house_id: Optional[int] = None
    build_year: Optional[int] = None
    move_in_year: Optional[int] = None
    annual_year: Optional[int] = None
    facing_degree: Optional[float] = Field(default=None, ge=0, le=360)
    use_house_main_door: bool = False


class XuanKongReportIn(BaseModel):
    house_id: int
    build_year: Optional[int] = None
    move_in_year: Optional[int] = None
    annual_year: Optional[int] = None
    facing_degree: Optional[float] = Field(default=None, ge=0, le=360)
    use_house_main_door: bool = True
    analysis_mode: str = "safe"


@router.get("/period")
def period(year: int) -> Dict[str, Any]:
    return xuankong_service.period(year)


@router.post("/calculate")
def calculate(payload: XuanKongCalculateIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return xuankong_service.calculate_for_request(db, payload.model_dump())
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/report")
def report(payload: XuanKongReportIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return xuankong_service.generate_report(db, payload.model_dump())
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/records")
def records(house_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return xuankong_service.list_records(db, house_id=house_id)
