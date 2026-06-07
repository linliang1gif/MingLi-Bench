from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import risk_service

router = APIRouter(prefix="/api", tags=["risk"])


class RiskCheckRequest(BaseModel):
    text: str
    analysis_mode: str = "safe"


@router.post("/risk-terms/init")
def init_risk_terms(db: Session = Depends(get_db)) -> Dict[str, int]:
    return risk_service.init_risk_terms(db)


@router.get("/risk-terms")
def list_risk_terms(
    enabled_only: bool = False,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return risk_service.list_risk_terms(
        db,
        enabled_only=enabled_only,
        category=category,
        severity=severity,
    )


@router.post("/risk/check")
def check_risk(payload: RiskCheckRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return risk_service.check_text(db, payload.text, analysis_mode=payload.analysis_mode)
