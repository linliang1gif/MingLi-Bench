from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import system_service

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/system/check")
def check_system(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return system_service.check_system(db)


@router.post("/system/backup-db")
def backup_database() -> Dict[str, Any]:
    try:
        return system_service.backup_database()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/system/test-cases")
def test_cases() -> Dict[str, Any]:
    return system_service.load_test_cases()
