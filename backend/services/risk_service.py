"""风险词初始化、列表与文本审核。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..db.models import RiskTerm
from ..domain.risk_rules import scan_text
from . import analysis_mode_service


DATA_PATH: Path = settings.project_root / "backend" / "data" / "risk_terms.json"


def _serialize(row: RiskTerm) -> Dict[str, Any]:
    return {
        "id": row.id,
        "term": row.term,
        "category": row.category,
        "severity": row.severity,
        "replacement_suggestion": row.replacement_suggestion,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def init_risk_terms(db: Session) -> Dict[str, int]:
    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing = {row.term: row for row in db.scalars(select(RiskTerm)).all()}
    inserted = 0
    updated = 0
    for item in items:
        row = existing.get(item["term"])
        if row:
            changed = False
            for key in ("category", "severity", "replacement_suggestion"):
                value = item.get(key)
                if getattr(row, key) != value:
                    setattr(row, key, value)
                    changed = True
            if "enabled" in item and row.enabled != item["enabled"]:
                row.enabled = item["enabled"]
                changed = True
            if changed:
                updated += 1
            continue
        db.add(
            RiskTerm(
                term=item["term"],
                category=item["category"],
                severity=item["severity"],
                replacement_suggestion=item.get("replacement_suggestion"),
                enabled=item.get("enabled", True),
            )
        )
        inserted += 1
    db.commit()
    return {"inserted": inserted, "updated": updated, "total": db.query(RiskTerm).count()}


def list_risk_terms(
    db: Session,
    enabled_only: bool = False,
    category: Optional[str] = None,
    severity: Optional[str] = None,
) -> List[Dict[str, Any]]:
    stmt = select(RiskTerm).order_by(RiskTerm.id.asc())
    if enabled_only:
        stmt = stmt.where(RiskTerm.enabled.is_(True))
    if category:
        stmt = stmt.where(RiskTerm.category == category)
    if severity:
        stmt = stmt.where(RiskTerm.severity == severity)
    return [_serialize(row) for row in db.scalars(stmt).all()]


def check_text(db: Session, text: str, analysis_mode: str = analysis_mode_service.SAFE_MODE) -> Dict[str, Any]:
    terms = list_risk_terms(db, enabled_only=True)
    risk = scan_text(text or "", terms)
    return analysis_mode_service.apply_mode_to_risk_check(risk, analysis_mode)


def final_text_for_mode(text: str, risk: Dict[str, Any]) -> str:
    """Return the text that should be shown/stored for the selected mode."""
    if (risk or {}).get("analysis_mode") == analysis_mode_service.SAFE_MODE and (risk or {}).get("hits"):
        return (risk or {}).get("safe_text") or text or ""
    return text or ""
