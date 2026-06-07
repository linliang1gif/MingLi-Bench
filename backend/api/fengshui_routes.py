from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import fengshui_service

router = APIRouter(prefix="/api", tags=["fengshui"])


class BasicReportIn(BaseModel):
    house_id: int
    analysis_mode: str = "safe"


@router.post("/fengshui/basic-report")
def basic_report(payload: BasicReportIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        return fengshui_service.generate_basic_report(
            db,
            payload.house_id,
            analysis_mode=payload.analysis_mode,
        )
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message)
