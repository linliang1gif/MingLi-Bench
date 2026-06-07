"""Prompt 模板初始化与管理。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..db.models import PromptTemplate


DATA_PATH: Path = settings.project_root / "backend" / "data" / "prompt_templates.json"


def serialize(row: PromptTemplate) -> Dict[str, Any]:
    return {
        "id": row.id,
        "module": row.module,
        "name": row.name,
        "system_prompt": row.system_prompt,
        "user_prompt_template": row.user_prompt_template,
        "output_schema": row.output_schema,
        "version": row.version,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def init_templates(db: Session) -> Dict[str, int]:
    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing = {
        (row.module, row.name, row.version)
        for row in db.scalars(select(PromptTemplate)).all()
    }
    inserted = 0
    for item in items:
        key = (item["module"], item["name"], item.get("version") or "1.0.0")
        if key in existing:
            continue
        db.add(
            PromptTemplate(
                module=item["module"],
                name=item["name"],
                system_prompt=item["system_prompt"],
                user_prompt_template=item["user_prompt_template"],
                output_schema=item.get("output_schema"),
                version=item.get("version") or "1.0.0",
                enabled=item.get("enabled", True),
            )
        )
        inserted += 1
    db.commit()
    return {"inserted": inserted, "total": db.query(PromptTemplate).count()}


def list_templates(db: Session, module: Optional[str] = None) -> List[Dict[str, Any]]:
    stmt = select(PromptTemplate).order_by(PromptTemplate.module.asc(), PromptTemplate.id.desc())
    if module:
        stmt = stmt.where(PromptTemplate.module == module)
    return [serialize(row) for row in db.scalars(stmt).all()]


def create_template(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = PromptTemplate(
        module=payload["module"],
        name=payload["name"],
        system_prompt=payload["system_prompt"],
        user_prompt_template=payload["user_prompt_template"],
        output_schema=payload.get("output_schema"),
        version=payload.get("version") or "1.0.0",
        enabled=payload.get("enabled", True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


def update_template(db: Session, template_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row = db.get(PromptTemplate, template_id)
    if not row:
        return None
    for key in (
        "module",
        "name",
        "system_prompt",
        "user_prompt_template",
        "output_schema",
        "version",
        "enabled",
    ):
        if key in payload:
            setattr(row, key, payload[key])
    db.commit()
    db.refresh(row)
    return serialize(row)


def get_enabled_template(db: Session, module: str) -> Optional[PromptTemplate]:
    return db.scalars(
        select(PromptTemplate)
        .where(PromptTemplate.module == module, PromptTemplate.enabled.is_(True))
        .order_by(PromptTemplate.id.desc())
    ).first()


def test_template(db: Session, template_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row = db.get(PromptTemplate, template_id)
    if not row:
        return None

    from . import analysis_mode_service, llm_service, prompt_service, risk_service

    input_json = payload.get("input_json")
    if isinstance(input_json, str):
        try:
            input_json = json.loads(input_json)
        except Exception:
            input_json = {"text": input_json}
    if input_json is None:
        input_json = {}

    input_text = payload.get("input_text") or ""
    analysis_mode = analysis_mode_service.validate_analysis_mode(payload.get("analysis_mode"))
    context: Dict[str, Any] = {}
    if isinstance(input_json, dict):
        context.update(input_json)
        context["analysis_mode"] = analysis_mode
    context.update(
        {
            "input_text": input_text,
            "message": input_text,
            "question": input_text,
            "subject_block": input_text or "测试命主资料：此处为 Prompt 测试占位，不保存正式报告。",
            "input_json": json.dumps(input_json, ensure_ascii=False, indent=2),
            "references": "暂无古籍引用来源",
            "reference_count": 0,
            "reference_notes": "Prompt 测试未执行知识库检索，不得虚构书名、章节或出处。",
        }
    )

    rendered = prompt_service.render_db_template(row, context)
    llm = llm_service.chat_complete(
        system_prompt=rendered["system_prompt"],
        messages=[{"role": "user", "content": rendered["user_prompt"]}],
        max_tokens=2048,
        temperature=0.4,
    )
    raw_output = llm["content"] if llm["ok"] else f"Prompt 测试调用失败：{llm.get('error') or 'unknown_error'}"
    raw_output = prompt_service.append_mode_warning(raw_output, analysis_mode)
    risk = risk_service.check_text(db, raw_output, analysis_mode=analysis_mode)
    return {
        "template": serialize(row),
        "raw_output": raw_output,
        "risk_check": risk,
        "safe_output": risk.get("safe_text") or raw_output,
        "provider": llm.get("provider"),
        "model": llm.get("model"),
        "analysis_mode": analysis_mode,
        "ok": llm.get("ok", False),
    }
