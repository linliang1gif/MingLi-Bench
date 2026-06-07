"""房屋档案服务。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import CompassRecord, HouseProfile
from ..domain.compass import convert_degree


def _house(row: HouseProfile) -> Dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "address_note": row.address_note,
        "house_type": row.house_type,
        "build_year": row.build_year,
        "move_in_date": row.move_in_date,
        "main_door_degree": row.main_door_degree,
        "main_door_direction_8": row.main_door_direction_8,
        "main_door_direction_24": row.main_door_direction_24,
        "floorplan_note": row.floorplan_note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_houses(db: Session) -> List[Dict[str, Any]]:
    rows = db.scalars(select(HouseProfile).order_by(HouseProfile.id.desc())).all()
    return [_house(row) for row in rows]


def create_house(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    degree = payload.get("main_door_degree")
    direction_8 = payload.get("main_door_direction_8")
    direction_24 = payload.get("main_door_direction_24")
    if degree is not None:
        converted = convert_degree(degree)
        degree = converted["degree"]
        direction_8 = converted["direction_8"]
        direction_24 = converted["direction_24"]
    row = HouseProfile(
        name=payload["name"],
        address_note=payload.get("address_note"),
        house_type=payload.get("house_type"),
        build_year=payload.get("build_year"),
        move_in_date=payload.get("move_in_date"),
        main_door_degree=degree,
        main_door_direction_8=direction_8,
        main_door_direction_24=direction_24,
        floorplan_note=payload.get("floorplan_note"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _house(row)


def get_house(db: Session, house_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(HouseProfile, house_id)
    return _house(row) if row else None


def list_compass_records(db: Session, house_id: int) -> Optional[List[Dict[str, Any]]]:
    if not db.get(HouseProfile, house_id):
        return None
    rows = db.scalars(
        select(CompassRecord)
        .where(CompassRecord.house_id == house_id)
        .order_by(CompassRecord.id.desc())
    ).all()
    return [
        {
            "id": row.id,
            "house_id": row.house_id,
            "scene_type": row.scene_type,
            "object_type": row.object_type,
            "degree": row.degree,
            "direction_8": row.direction_8,
            "direction_24": row.direction_24,
            "stability_score": row.stability_score,
            "note": row.note,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def set_main_door_from_record(db: Session, house_id: int, record_id: int) -> Optional[Dict[str, Any]]:
    house = db.get(HouseProfile, house_id)
    record = db.get(CompassRecord, record_id)
    if not house or not record or record.house_id != house_id:
        return None
    house.main_door_degree = record.degree
    house.main_door_direction_8 = record.direction_8
    house.main_door_direction_24 = record.direction_24
    db.commit()
    db.refresh(house)
    return _house(house)
