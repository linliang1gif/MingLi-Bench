"""Yinzhai study record and report service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import HouseProfile, Report, ReportVersion, Subject, YinzhaiStudyRecord
from ..domain import compass, yinzhai_rules
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service
from .house_service import get_house, list_compass_records


REPORT_TYPE = "yinzhai_study_report"
SYSTEM_SUBJECT_NAME = "系统 · 阴宅研究报告"


def _system_subject_id(db: Session) -> int:
    subject = db.scalars(
        select(Subject).where(Subject.nickname == SYSTEM_SUBJECT_NAME).order_by(Subject.id.asc())
    ).first()
    if not subject:
        subject = Subject(
            nickname=SYSTEM_SUBJECT_NAME,
            gender="其他",
            calendar_type="solar",
            notes="系统自动创建，用于兼容 reports.subject_id 必填约束；阴宅研究报告以记录与 house_id 为真实关联。",
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


def _dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _orientation(degree: Optional[float]) -> Optional[Dict[str, Any]]:
    if degree is None:
        return None
    return compass.convert_degree(float(degree))


def _serialize_record(row: YinzhaiStudyRecord) -> Dict[str, Any]:
    return {
        "id": row.id,
        "house_id": row.house_id,
        "title": row.title,
        "site_type": row.site_type,
        "site_type_label": yinzhai_rules.site_type_label(row.site_type),
        "location_note": row.location_note,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "mountain_degree": row.mountain_degree,
        "mountain_direction_24": row.mountain_direction_24,
        "facing_degree": row.facing_degree,
        "facing_direction_24": row.facing_direction_24,
        "dragon": _loads(row.dragon_json) or {},
        "cave": _loads(row.cave_json) or {},
        "sand": _loads(row.sand_json) or {},
        "water": _loads(row.water_json) or {},
        "direction": _loads(row.direction_json) or {},
        "environment": _loads(row.environment_json) or {},
        "research_note": row.research_note,
        "result_json": _loads(row.result_json) or {},
        "report_id": row.report_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def create_record(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    house_id = payload.get("house_id")
    if house_id is not None and not db.get(HouseProfile, int(house_id)):
        raise ValueError(f"house {house_id} not found")

    mountain = _orientation(payload.get("mountain_degree"))
    facing = _orientation(payload.get("facing_degree"))
    result = yinzhai_rules.build_result(payload, mountain=mountain, facing=facing)
    row = YinzhaiStudyRecord(
        house_id=int(house_id) if house_id is not None else None,
        title=payload.get("title") or "阴宅研究记录",
        site_type=payload.get("site_type") or "study_case",
        location_note=payload.get("location_note"),
        latitude=float(payload["latitude"]) if payload.get("latitude") is not None else None,
        longitude=float(payload["longitude"]) if payload.get("longitude") is not None else None,
        mountain_degree=mountain["degree"] if mountain else None,
        mountain_direction_24=mountain["direction_24"] if mountain else None,
        facing_degree=facing["degree"] if facing else None,
        facing_direction_24=facing["direction_24"] if facing else None,
        dragon_json=_dumps(payload.get("dragon") or {}),
        cave_json=_dumps(payload.get("cave") or {}),
        sand_json=_dumps(payload.get("sand") or {}),
        water_json=_dumps(payload.get("water") or {}),
        direction_json=_dumps(payload.get("direction") or {}),
        environment_json=_dumps(payload.get("environment") or {}),
        research_note=payload.get("research_note"),
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_record(row)


def get_record(db: Session, record_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(YinzhaiStudyRecord, int(record_id))
    return _serialize_record(row) if row else None


def list_records(db: Session, house_id: Optional[int] = None) -> List[Dict[str, Any]]:
    stmt = select(YinzhaiStudyRecord).order_by(YinzhaiStudyRecord.id.desc())
    if house_id is not None:
        stmt = stmt.where(YinzhaiStudyRecord.house_id == int(house_id))
    return [_serialize_record(row) for row in db.scalars(stmt).all()]


def delete_record(db: Session, record_id: int) -> bool:
    row = db.get(YinzhaiStudyRecord, int(record_id))
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def _record_input(db: Session, row: YinzhaiStudyRecord) -> Dict[str, Any]:
    record = _serialize_record(row)
    house = get_house(db, row.house_id) if row.house_id is not None else None
    compass_records = list_compass_records(db, row.house_id) if row.house_id is not None else []
    return {
        "record_id": row.id,
        "house_id": row.house_id,
        "house": house,
        "record": record,
        "result": record.get("result_json") or {},
        "compass_records": compass_records or [],
        "boundary_note": yinzhai_rules.BOUNDARY_NOTE,
    }


def generate_report(
    db: Session,
    record_id: int,
    analysis_mode: str = analysis_mode_service.SAFE_MODE,
) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.validate_analysis_mode(analysis_mode)
    row = db.get(YinzhaiStudyRecord, int(record_id))
    if not row:
        raise ValueError("yinzhai study record not found")

    reference_input = {
        **_record_input(db, row),
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
            "研究对象与边界",
            "龙穴砂水向记录",
            "坐向与罗盘资料",
            "形势观察",
            "古籍引用线索",
            "后续整理建议",
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
        markdown = yinzhai_rules.fallback_markdown(
            record=_serialize_record(row),
            result=_loads(row.result_json) or {},
            references=references,
        )

    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    subject_id = _system_subject_id(db)
    house_id = row.house_id
    title = f"阴宅研究报告 · {row.title}"
    report = Report(
        subject_id=subject_id,
        house_id=house_id,
        report_type=REPORT_TYPE,
        title=title,
        content=markdown,
    )
    db.add(report)
    db.flush()
    row.report_id = report.id
    db.commit()
    db.refresh(report)
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
                "yinzhai_study_record_id": row.id,
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
        "record": _serialize_record(row),
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
