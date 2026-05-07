"""命主档案 CRUD。"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Subject


def _to_dict(s: Subject) -> Dict[str, Any]:
    focus = []
    if s.focus_topics:
        try:
            v = json.loads(s.focus_topics)
            if isinstance(v, list):
                focus = v
        except Exception:
            focus = []
    return {
        "id": s.id,
        "nickname": s.nickname,
        "gender": s.gender,
        "birth_date": s.birth_date,
        "birth_time": s.birth_time,
        "birth_place": s.birth_place,
        "calendar_type": s.calendar_type,
        "longitude": s.longitude,
        "focus_topics": focus,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def list_subjects(db: Session) -> List[Dict[str, Any]]:
    rows = db.scalars(select(Subject).order_by(Subject.id.desc())).all()
    return [_to_dict(s) for s in rows]


def get_subject(db: Session, subject_id: int) -> Optional[Dict[str, Any]]:
    s = db.get(Subject, subject_id)
    return _to_dict(s) if s else None


def get_subject_orm(db: Session, subject_id: int) -> Optional[Subject]:
    return db.get(Subject, subject_id)


def create_subject(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    focus = payload.get("focus_topics") or []
    if not isinstance(focus, list):
        focus = [str(focus)]
    lon = payload.get("longitude")
    try:
        lon = float(lon) if lon not in (None, "") else None
    except Exception:
        lon = None
    s = Subject(
        nickname=str(payload.get("nickname") or "未命名").strip()[:64],
        gender=(payload.get("gender") or None),
        birth_date=payload.get("birth_date"),
        birth_time=payload.get("birth_time"),
        birth_place=(payload.get("birth_place") or "")[:128] or None,
        calendar_type=(payload.get("calendar_type") or "solar"),
        longitude=lon,
        focus_topics=json.dumps(focus, ensure_ascii=False) if focus else None,
        notes=payload.get("notes"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_dict(s)


def delete_subject(db: Session, subject_id: int) -> bool:
    s = db.get(Subject, subject_id)
    if not s:
        return False
    db.delete(s)
    db.commit()
    return True
