from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import landscape_photo_service


router = APIRouter(prefix="/api/landscape-photo", tags=["landscape-photo"])


class AnalyzeIn(BaseModel):
    record_id: int


class ReportIn(BaseModel):
    record_id: int
    user_correction: Dict[str, Any] = {}
    analysis_mode: str = "safe"


@router.post("/upload")
def upload_photo(
    house_id: Optional[int] = Form(default=None),
    scene_type: str = Form(default="house_landscape"),
    target_label: Optional[str] = Form(default=None),
    degree: Optional[float] = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        record = landscape_photo_service.upload_photo(
            db,
            house_id=house_id,
            scene_type=scene_type,
            target_label=target_label,
            degree=degree,
            filename=file.filename or "",
            content_type=file.content_type,
            fileobj=file.file,
        )
        return {
            "record_id": record["id"],
            "image_path": record["image_path"],
            "scene_type": record["scene_type"],
            "record": record,
        }
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/analyze")
def analyze(payload: AnalyzeIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return landscape_photo_service.analyze_photo(db, payload.record_id)
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/report")
def report(payload: ReportIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return landscape_photo_service.generate_report(
            db,
            payload.record_id,
            payload.user_correction,
            analysis_mode=payload.analysis_mode,
        )
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/records")
def records(
    house_id: Optional[int] = None,
    scene_type: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return landscape_photo_service.list_records(db, house_id=house_id, scene_type=scene_type)


@router.get("/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    row = landscape_photo_service.get_record(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="landscape photo record not found")
    return row


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not landscape_photo_service.delete_record(db, record_id):
        raise HTTPException(status_code=404, detail="landscape photo record not found")
    return {"ok": True}
