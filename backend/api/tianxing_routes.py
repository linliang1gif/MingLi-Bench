from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import tianxing_service

router = APIRouter(prefix="/api/tianxing", tags=["tianxing"])


class TianxingQueryIn(BaseModel):
    house_id: Optional[int] = None
    degree: Optional[float] = Field(default=None, ge=0, le=360)
    mountain_24: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_note: Optional[str] = None
    note: Optional[str] = None


class TianxingReportIn(BaseModel):
    record_id: Optional[int] = None
    house_id: Optional[int] = None
    degree: Optional[float] = Field(default=None, ge=0, le=360)
    mountain_24: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_note: Optional[str] = None
    note: Optional[str] = None
    analysis_mode: str = "safe"


@router.get("/mappings")
def mappings() -> Dict[str, Any]:
    return tianxing_service.list_mappings()


@router.get("/lookup")
def lookup(
    degree: Optional[float] = None,
    mountain_24: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        return tianxing_service.query({"degree": degree, "mountain_24": mountain_24})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/query")
def query(payload: TianxingQueryIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return tianxing_service.query_and_save(db, payload.model_dump())
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/records")
def records(house_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return tianxing_service.list_records(db, house_id=house_id)


@router.get("/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = tianxing_service.get_record(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="tianxing record not found")
    return row


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not tianxing_service.delete_record(db, record_id):
        raise HTTPException(status_code=404, detail="tianxing record not found")
    return {"ok": True}


@router.post("/report")
def report(payload: TianxingReportIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return tianxing_service.generate_report(db, payload.model_dump())
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)
