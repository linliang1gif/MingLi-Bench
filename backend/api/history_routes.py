"""历史聚合：把对话与报告拉到统一时间轴。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ChatSession, Report, Subject
from ..db.session import get_db

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
def aggregated_history(
    subject_id: Optional[int] = None, db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    sess_stmt = select(ChatSession)
    if subject_id is not None:
        sess_stmt = sess_stmt.where(ChatSession.subject_id == subject_id)
    for s in db.scalars(sess_stmt).all():
        items.append(
            {
                "kind": "chat",
                "id": s.id,
                "subject_id": s.subject_id,
                "title": s.title or "未命名对话",
                "timestamp": (s.updated_at or s.created_at).isoformat()
                if (s.updated_at or s.created_at)
                else None,
            }
        )

    rep_stmt = select(Report)
    if subject_id is not None:
        rep_stmt = rep_stmt.where(Report.subject_id == subject_id)
    for r in db.scalars(rep_stmt).all():
        items.append(
            {
                "kind": "report",
                "id": r.id,
                "subject_id": r.subject_id,
                "title": r.title,
                "report_type": r.report_type,
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            }
        )

    items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return items
