from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import yinzhai_service

router = APIRouter(prefix="/api/yinzhai", tags=["yinzhai"])


class YinzhaiRecordIn(BaseModel):
    house_id: Optional[int] = None
    title: str = Field(default="阴宅研究记录", min_length=1)
    site_type: str = "study_case"
    location_note: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    mountain_degree: Optional[float] = Field(default=None, ge=0, le=360)
    facing_degree: Optional[float] = Field(default=None, ge=0, le=360)
    dragon: Dict[str, Any] = Field(default_factory=dict)
    cave: Dict[str, Any] = Field(default_factory=dict)
    sand: Dict[str, Any] = Field(default_factory=dict)
    water: Dict[str, Any] = Field(default_factory=dict)
    direction: Dict[str, Any] = Field(default_factory=dict)
    environment: Dict[str, Any] = Field(default_factory=dict)
    research_note: Optional[str] = None


class YinzhaiReportIn(BaseModel):
    record_id: int
    analysis_mode: str = "safe"


@router.post("/records")
def create_record(payload: YinzhaiRecordIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return yinzhai_service.create_record(db, payload.model_dump())
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/records")
def records(house_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return yinzhai_service.list_records(db, house_id=house_id)


@router.get("/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = yinzhai_service.get_record(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="yinzhai study record not found")
    return row


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not yinzhai_service.delete_record(db, record_id):
        raise HTTPException(status_code=404, detail="yinzhai study record not found")
    return {"ok": True}


@router.post("/report")
def report(payload: YinzhaiReportIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return yinzhai_service.generate_report(
            db,
            payload.record_id,
            analysis_mode=payload.analysis_mode,
        )
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)
