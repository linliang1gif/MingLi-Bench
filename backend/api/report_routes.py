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
    analysis_mode: str = "safe"


@router.post("/reports/generate")
def generate(payload: ReportGenRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return report_service.generate_report(
            db,
            subject_id=payload.subject_id,
            report_type=payload.report_type,
            question=payload.question,
            analysis_mode=payload.analysis_mode,
        )
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/reports")
def list_reports(
    subject_id: Optional[int] = None,
    has_references: Optional[bool] = None,
    analysis_mode: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    try:
        return report_service.list_reports(
            db,
            subject_id=subject_id,
            has_references=has_references,
            analysis_mode=analysis_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    r = report_service.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="report not found")
    return r


@router.get("/reports/{report_id}/versions")
def list_versions(report_id: int, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = report_service.list_report_versions(db, report_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="report not found")
    return rows


@router.get("/reports/{report_id}/versions/{version_id}")
def get_version(report_id: int, version_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = report_service.get_report_version(db, report_id, version_id)
    if not row:
        raise HTTPException(status_code=404, detail="report version not found")
    return row
