"""知识类目初始化与查询。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..db.models import KnowledgeCategory


DATA_PATH: Path = settings.project_root / "backend" / "data" / "categories_60.json"


def _serialize(row: KnowledgeCategory) -> Dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "parent_code": row.parent_code,
        "description": row.description,
        "priority": row.priority,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def init_categories(db: Session) -> Dict[str, int]:
    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing = set(db.scalars(select(KnowledgeCategory.code)).all())
    inserted = 0
    for item in items:
        if item["code"] in existing:
            continue
        db.add(
            KnowledgeCategory(
                code=item["code"],
                name=item["name"],
                parent_code=item.get("parent_code"),
                description=item.get("description"),
                priority=item.get("priority") or "P2",
                enabled=item.get("enabled", True),
            )
        )
        inserted += 1
    db.commit()
    return {"inserted": inserted, "total": db.query(KnowledgeCategory).count()}


def list_categories(db: Session, enabled_only: bool = False) -> List[Dict[str, Any]]:
    stmt = select(KnowledgeCategory).order_by(KnowledgeCategory.code.asc())
    if enabled_only:
        stmt = stmt.where(KnowledgeCategory.enabled.is_(True))
    return [_serialize(row) for row in db.scalars(stmt).all()]
