from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import house_service

router = APIRouter(prefix="/api", tags=["houses"])


class HouseIn(BaseModel):
    name: str = Field(..., min_length=1)
    address_note: Optional[str] = None
    house_type: Optional[str] = None
    build_year: Optional[int] = None
    move_in_date: Optional[str] = None
    main_door_degree: Optional[float] = None
    main_door_direction_8: Optional[str] = None
    main_door_direction_24: Optional[str] = None
    floorplan_note: Optional[str] = None


@router.get("/houses")
def list_houses(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return house_service.list_houses(db)


@router.post("/houses")
def create_house(payload: HouseIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return house_service.create_house(db, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/houses/{house_id}")
def get_house(house_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = house_service.get_house(db, house_id)
    if not row:
        raise HTTPException(status_code=404, detail="house not found")
    return row


@router.get("/houses/{house_id}/compass-records")
def list_house_compass_records(house_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = house_service.list_compass_records(db, house_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="house not found")
    return rows


@router.post("/houses/{house_id}/set-main-door-from-record/{record_id}")
def set_main_door_from_record(
    house_id: int,
    record_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    row = house_service.set_main_door_from_record(db, house_id, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="house or compass record not found")
    return row
