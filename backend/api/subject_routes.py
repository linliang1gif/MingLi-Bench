from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.models import Chart
from ..db.session import get_db
from ..services import chart_service, subject_service

router = APIRouter(prefix="/api", tags=["subjects"])


class SubjectCreate(BaseModel):
    nickname: str = Field(..., max_length=64)
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    birth_place: Optional[str] = None
    calendar_type: str = "solar"
    longitude: Optional[float] = None  # 真太阳时所需经度（°E）
    focus_topics: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return subject_service.list_subjects(db)


@router.post("/subjects", status_code=201)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return subject_service.create_subject(db, payload.model_dump())


@router.get("/subjects/{subject_id}")
def get_subject(subject_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    s = subject_service.get_subject(db, subject_id)
    if not s:
        raise HTTPException(status_code=404, detail="subject not found")
    return s


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: Session = Depends(get_db)) -> None:
    ok = subject_service.delete_subject(db, subject_id)
    if not ok:
        raise HTTPException(status_code=404, detail="subject not found")


# ----- 命盘相关 -----

@router.post("/subjects/{subject_id}/chart")
def generate_chart(subject_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    s = subject_service.get_subject(db, subject_id)
    if not s:
        raise HTTPException(status_code=404, detail="subject not found")
    bazi = chart_service.compute_chart(
        birth_date=s.get("birth_date"),
        birth_time=s.get("birth_time"),
        calendar_type=s.get("calendar_type") or "solar",
        longitude=s.get("longitude"),
    )
    if not bazi.get("available"):
        raise HTTPException(status_code=400, detail=bazi.get("reason") or "cannot compute chart")

    chart = Chart(
        subject_id=subject_id,
        bazi_json=json.dumps(
            {"pillars": bazi["pillars"], "input": bazi["input"], "lunar": bazi.get("lunar")},
            ensure_ascii=False,
        ),
        wuxing_json=json.dumps(bazi["wuxing"], ensure_ascii=False),
        summary=bazi["summary"],
    )
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return {
        "id": chart.id,
        "subject_id": subject_id,
        "pillars": bazi["pillars"],
        "wuxing": bazi["wuxing"],
        "summary": bazi["summary"],
        "lunar": bazi.get("lunar"),
        "created_at": chart.created_at.isoformat() if chart.created_at else None,
    }


@router.get("/subjects/{subject_id}/chart")
def get_chart(subject_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    s = subject_service.get_subject(db, subject_id)
    if not s:
        raise HTTPException(status_code=404, detail="subject not found")
    chart = (
        db.query(Chart)
        .filter(Chart.subject_id == subject_id)
        .order_by(Chart.id.desc())
        .first()
    )
    if not chart:
        # 不存在则现算一个临时结果（不入库）
        bazi = chart_service.compute_chart(
            birth_date=s.get("birth_date"),
            birth_time=s.get("birth_time"),
            calendar_type=s.get("calendar_type") or "solar",
            longitude=s.get("longitude"),
        )
        return {
            "id": None,
            "subject_id": subject_id,
            "persisted": False,
            "available": bazi.get("available", False),
            "reason": bazi.get("reason"),
            "pillars": bazi.get("pillars"),
            "wuxing": bazi.get("wuxing"),
            "lunar": bazi.get("lunar"),
            "summary": bazi.get("summary"),
            "created_at": None,
        }
    bazi_doc = json.loads(chart.bazi_json or "{}")
    return {
        "id": chart.id,
        "subject_id": subject_id,
        "persisted": True,
        "available": True,
        "pillars": bazi_doc.get("pillars"),
        "lunar": bazi_doc.get("lunar"),
        "wuxing": json.loads(chart.wuxing_json or "{}"),
        "summary": chart.summary,
        "created_at": chart.created_at.isoformat() if chart.created_at else None,
    }
