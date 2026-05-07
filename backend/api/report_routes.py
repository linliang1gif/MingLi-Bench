from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import report_service

router = APIRouter(prefix="/api", tags=["reports"])


class ReportGenRequest(BaseModel):
    subject_id: int
    report_type: str = Field(default="general")
    question: Optional[str] = None


@router.post("/reports/generate")
def generate(payload: ReportGenRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return report_service.generate_report(
            db,
            subject_id=payload.subject_id,
            report_type=payload.report_type,
            question=payload.question,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/reports")
def list_reports(
    subject_id: Optional[int] = None, db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    return report_service.list_reports(db, subject_id=subject_id)


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    r = report_service.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="report not found")
    return r
