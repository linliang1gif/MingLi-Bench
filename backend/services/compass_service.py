"""罗盘测向服务。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import CompassRecord
from ..domain.compass import convert_degree


def convert(degree: float) -> Dict[str, Any]:
    return convert_degree(degree)


def _record(row: CompassRecord) -> Dict[str, Any]:
    return {
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


def create_record(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    converted = convert_degree(payload["degree"])
    row = CompassRecord(
        house_id=payload.get("house_id"),
        scene_type=payload.get("scene_type") or "indoor",
        object_type=payload.get("object_type") or "main_door",
        degree=converted["degree"],
        direction_8=converted["direction_8"],
        direction_24=converted["direction_24"],
        stability_score=payload.get("stability_score"),
        note=payload.get("note"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _record(row)


def list_records(db: Session, house_id: Optional[int] = None) -> List[Dict[str, Any]]:
    stmt = select(CompassRecord).order_by(CompassRecord.id.desc())
    if house_id is not None:
        stmt = stmt.where(CompassRecord.house_id == house_id)
    return [_record(row) for row in db.scalars(stmt).all()]


def get_record(db: Session, record_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(CompassRecord, record_id)
    return _record(row) if row else None


def delete_record(db: Session, record_id: int) -> bool:
    row = db.get(CompassRecord, record_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
