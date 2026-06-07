from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import compass_service

router = APIRouter(prefix="/api", tags=["compass"])


class CompassConvertIn(BaseModel):
    degree: float


class CompassRecordIn(BaseModel):
    house_id: Optional[int] = None
    scene_type: str = "indoor"
    object_type: str = "main_door"
    degree: float
    stability_score: Optional[float] = None
    note: Optional[str] = None


@router.post("/compass/convert")
def convert(payload: CompassConvertIn) -> Dict[str, Any]:
    try:
        return compass_service.convert(payload.degree)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compass/records")
def create_record(payload: CompassRecordIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return compass_service.create_record(db, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/compass/records")
def list_records(house_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return compass_service.list_records(db, house_id=house_id)


@router.delete("/compass/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not compass_service.delete_record(db, record_id):
        raise HTTPException(status_code=404, detail="compass record not found")
    return {"ok": True}
