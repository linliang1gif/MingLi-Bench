"""阳宅基础报告服务。"""

from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Report, ReportVersion, Subject
from ..domain import fengshui_rules
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service
from .house_service import get_house, list_compass_records


SYSTEM_SUBJECT_NAME = "系统 · 阳宅报告"
REPORT_TYPE = "fengshui_basic"


def _system_subject_id(db: Session) -> int:
    subject = db.scalars(
        select(Subject).where(Subject.nickname == SYSTEM_SUBJECT_NAME).order_by(Subject.id.asc())
    ).first()
    if not subject:
        subject = Subject(
            nickname=SYSTEM_SUBJECT_NAME,
            gender="其他",
            calendar_type="solar",
            notes="系统自动创建，用于兼容 reports.subject_id 必填约束，阳宅报告以 house_id 为真实关联。",
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
    return subject.id


def _serialize_report(row: Report) -> Dict[str, Any]:
    return {
        "id": row.id,
        "subject_id": row.subject_id,
        "house_id": row.house_id,
        "report_type": row.report_type,
        "title": row.title,
        "content": row.content,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def generate_basic_report(
    db: Session,
    house_id: int,
    analysis_mode: str = analysis_mode_service.SAFE_MODE,
) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.validate_analysis_mode(analysis_mode)
    house = get_house(db, house_id)
    if not house:
        raise ValueError(f"house {house_id} not found")
    records = list_compass_records(db, house_id) or []
    reference_input = {
        "house_id": house_id,
        "house": house,
        "compass_records": records,
        "analysis_mode": analysis_mode,
    }
    references = report_reference_service.collect_references(
        db,
        report_type=REPORT_TYPE,
        input_json=reference_input,
        limit=5,
    )

    input_payload = {
        "house_id": house_id,
        "house": house,
        "compass_records": records,
        "references": references,
        "analysis_mode": analysis_mode,
        "required_sections": [
            "结论",
            "房屋基础信息",
            "大门朝向",
            "已测点位",
            "当前主要问题",
            "优先调整建议",
            "传统阳宅解释",
            "现代居住建议",
            "风险提醒",
        ],
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, indent=2)
    template = prompt_service.get_db_template(db, "fengshui_basic")
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
            messages=[
                {
                    "role": "user",
                    "content": (
                        user_prompt
                        + "\n\n请严格按以下小节输出：结论、房屋基础信息、大门朝向、已测点位、"
                        "当前主要问题、优先调整建议、传统阳宅解释、现代居住建议、风险提醒。"
                    ),
                }
            ],
            max_tokens=3500,
            temperature=0.45,
        )
        markdown = llm["content"] if llm.get("ok") else ""

    if not markdown:
        markdown = fengshui_rules.fallback_markdown(house, records, references)

    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    subject_id = _system_subject_id(db)
    title = f"阳宅基础报告 · {house['name']}"
    report = Report(
        subject_id=subject_id,
        house_id=house_id,
        report_type=REPORT_TYPE,
        title=title,
        content=markdown,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    version = ReportVersion(
        report_id=report.id,
        version="1",
        report_type=REPORT_TYPE,
        input_json=input_json,
        result_json=json.dumps(
            {
                "ok": llm.get("ok", False),
                "provider": llm.get("provider"),
                "house_id": house_id,
                "record_count": len(records),
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
    return _serialize_report(report)
