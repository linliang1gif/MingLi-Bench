"""Tianxing fengshui lookup and report service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import HouseProfile, Report, ReportVersion, Subject, TianxingFengshuiRecord
from ..domain import tianxing_rules
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service
from .house_service import get_house, list_compass_records


REPORT_TYPE = "tianxing_fengshui_report"
SYSTEM_SUBJECT_NAME = "系统 · 天星风水报告"


def _system_subject_id(db: Session) -> int:
    subject = db.scalars(
        select(Subject).where(Subject.nickname == SYSTEM_SUBJECT_NAME).order_by(Subject.id.asc())
    ).first()
    if not subject:
        subject = Subject(
            nickname=SYSTEM_SUBJECT_NAME,
            gender="其他",
            calendar_type="solar",
            notes="系统自动创建，用于兼容 reports.subject_id 必填约束；天星风水报告以记录与 house_id 为真实关联。",
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
    return subject.id


def _loads(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _serialize_record(row: TianxingFengshuiRecord) -> Dict[str, Any]:
    return {
        "id": row.id,
        "house_id": row.house_id,
        "query_type": row.query_type,
        "degree": row.degree,
        "mountain_24": row.mountain_24,
        "tianxing": _loads(row.tianxing_json) or {},
        "input_json": _loads(row.input_json) or {},
        "report_id": row.report_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_mappings() -> Dict[str, Any]:
    return {
        "mappings": tianxing_rules.all_mappings(),
        "variant_note": tianxing_rules.VARIANT_NOTE,
        "boundary_note": tianxing_rules.REPORT_BOUNDARY,
    }


def query(payload: Dict[str, Any]) -> Dict[str, Any]:
    return tianxing_rules.build_query_result(payload)


def save_record(db: Session, payload: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    house_id = payload.get("house_id")
    if house_id is not None and not db.get(HouseProfile, int(house_id)):
        raise ValueError(f"house {house_id} not found")
    mapping = result["mapping"]
    row = TianxingFengshuiRecord(
        house_id=int(house_id) if house_id is not None else None,
        query_type=result.get("query_type") or "mountain",
        degree=mapping.get("degree"),
        mountain_24=mapping["mountain_24"],
        tianxing_json=json.dumps(mapping, ensure_ascii=False),
        input_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_record(row)


def query_and_save(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = query(payload)
    record = save_record(db, payload, result)
    return {"result": result, "record": record}


def list_records(db: Session, house_id: Optional[int] = None) -> List[Dict[str, Any]]:
    stmt = select(TianxingFengshuiRecord).order_by(TianxingFengshuiRecord.id.desc())
    if house_id is not None:
        stmt = stmt.where(TianxingFengshuiRecord.house_id == int(house_id))
    return [_serialize_record(row) for row in db.scalars(stmt).all()]


def get_record(db: Session, record_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(TianxingFengshuiRecord, int(record_id))
    return _serialize_record(row) if row else None


def delete_record(db: Session, record_id: int) -> bool:
    row = db.get(TianxingFengshuiRecord, int(record_id))
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def _resolve_report_input(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    record_id = payload.get("record_id")
    if record_id:
        row = db.get(TianxingFengshuiRecord, int(record_id))
        if not row:
            raise ValueError("tianxing record not found")
        record = _serialize_record(row)
        result = {
            "query_type": row.query_type,
            "input": _loads(row.input_json) or {},
            "mapping": record["tianxing"],
            "method_note": tianxing_rules.VARIANT_NOTE,
            "boundary_note": tianxing_rules.REPORT_BOUNDARY,
        }
        house_id = row.house_id
    else:
        result = query(payload)
        record = save_record(db, payload, result)
        row = db.get(TianxingFengshuiRecord, int(record["id"]))
        house_id = row.house_id if row else payload.get("house_id")
    house = get_house(db, house_id) if house_id is not None else None
    compass_records = list_compass_records(db, house_id) if house_id is not None else []
    return {
        "record": _serialize_record(row) if row else record,
        "result": result,
        "house_id": house_id,
        "house": house,
        "compass_records": compass_records or [],
        "note": payload.get("note"),
    }


def generate_report(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.normalize_mode_from_input(payload)
    payload = {**payload, "analysis_mode": analysis_mode}
    resolved = _resolve_report_input(db, payload)
    record = resolved["record"]
    result = resolved["result"]
    reference_input = {
        "record_id": record["id"],
        "house_id": resolved["house_id"],
        "house": resolved["house"],
        "tianxing": result,
        "compass_records": resolved["compass_records"],
        "note": resolved.get("note"),
        "boundary_note": tianxing_rules.REPORT_BOUNDARY,
        "analysis_mode": analysis_mode,
    }
    references = report_reference_service.collect_references(
        db,
        report_type=REPORT_TYPE,
        input_json=reference_input,
        limit=5,
    )
    input_payload = {
        **reference_input,
        "references": references,
        "analysis_mode": analysis_mode,
        "required_sections": [
            "结论",
            "查询信息",
            "天星映射",
            "古籍引用线索",
            "研究说明",
            "记录备注",
            "风险提醒",
        ],
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, indent=2)
    template = prompt_service.get_db_template(db, REPORT_TYPE)
    prompt_version = prompt_service.PROMPT_VERSION
    llm: Dict[str, Any] = {"ok": False, "provider": None, "model": None, "error": "no_template"}
    markdown = ""
    if template:
        rendered = prompt_service.render_db_template(
            template,
            {
                "input_json": input_json,
                "analysis_mode": analysis_mode,
                **report_reference_service.build_prompt_context(references),
            },
        )
        prompt_version = rendered["version"]
        user_prompt = report_reference_service.append_reference_block(
            rendered["user_prompt"],
            references,
        )
        llm = llm_service.chat_complete(
            system_prompt=rendered["system_prompt"],
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=3500,
            temperature=0.35,
        )
        markdown = llm["content"] if llm.get("ok") else ""

    if not markdown:
        markdown = tianxing_rules.fallback_markdown(
            result=result,
            house=resolved["house"],
            references=references,
            note=resolved.get("note"),
        )

    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    subject_id = _system_subject_id(db)
    house_id = resolved["house_id"]
    mapping = result["mapping"]
    title = f"天星风水报告 · {mapping.get('mountain_24')} · {mapping.get('tianxing')}"
    report = Report(
        subject_id=subject_id,
        house_id=house_id,
        report_type=REPORT_TYPE,
        title=title,
        content=markdown,
    )
    db.add(report)
    db.flush()
    row = db.get(TianxingFengshuiRecord, int(record["id"]))
    if row:
        row.report_id = report.id
    db.commit()
    db.refresh(report)
    if row:
        db.refresh(row)

    version = ReportVersion(
        report_id=report.id,
        version="1",
        report_type=REPORT_TYPE,
        input_json=input_json,
        result_json=json.dumps(
            {
                "ok": llm.get("ok", False),
                "provider": llm.get("provider"),
                "tianxing_record_id": record["id"],
                "house_id": house_id,
                "analysis_mode": analysis_mode,
            },
            ensure_ascii=False,
        ),
        markdown=markdown,
        prompt_version=prompt_version,
        model_used=llm.get("model"),
        risk_check_result=json.dumps(risk, ensure_ascii=False),
        references_json=json.dumps(references, ensure_ascii=False),
    )
    db.add(version)
    db.commit()
    return {
        "id": report.id,
        "report_id": report.id,
        "subject_id": report.subject_id,
        "house_id": report.house_id,
        "report_type": report.report_type,
        "analysis_mode": analysis_mode,
        "title": report.title,
        "content": report.content,
        "record": _serialize_record(row) if row else record,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
