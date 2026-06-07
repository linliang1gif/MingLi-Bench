"""报告生成与读取。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Chart, Report, ReportVersion, Subject
from . import (
    analysis_mode_service,
    chart_service,
    llm_service,
    prompt_service,
    report_reference_service,
    risk_service,
    subject_service,
)


REPORT_TYPE_TO_TEMPLATE = {
    "general": "general_analysis",
    "wealth": "wealth_analysis",
    "career": "career_analysis",
    "relationship": "relationship_analysis",
    "yearly": "yearly_fortune",
}

REPORT_TYPE_LABEL = {
    "general": "综合命理分析",
    "wealth": "财运专项分析",
    "career": "事业专项分析",
    "relationship": "感情专项分析",
    "yearly": "流年走势分析",
    "fengshui_basic": "阳宅基础报告",
    "fengshui_xuankong_report": "玄空飞星报告",
    "fengshui_photo_report": "拍照风水报告",
    "landscape_photo_report": "外局拍照研究报告",
    "heritage_risk_record_report": "文保风险记录报告",
}

REPORT_TYPE_LABEL.update(
    {
        "yinzhai_study_report": "阴宅研究报告",
        "tianxing_fengshui_report": "天星风水报告",
    }
)


def _serialize(report: Report, has_references: Optional[bool] = None) -> Dict[str, Any]:
    data = {
        "id": report.id,
        "subject_id": report.subject_id,
        "house_id": report.house_id,
        "report_type": report.report_type,
        "title": report.title,
        "content": report.content,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
    if has_references is not None:
        data["has_references"] = has_references
    return data


def _analysis_mode_from_version(row: Optional[ReportVersion]) -> str:
    if not row or not row.input_json:
        return analysis_mode_service.SAFE_MODE
    try:
        input_json = json.loads(row.input_json)
    except Exception:
        return analysis_mode_service.SAFE_MODE
    if isinstance(input_json, dict):
        return analysis_mode_service.normalize_mode_from_input(input_json)
    return analysis_mode_service.SAFE_MODE


def _serialize_version(row: ReportVersion) -> Dict[str, Any]:
    def _loads(value: Optional[str]) -> Any:
        if not value:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value

    analysis_mode = _analysis_mode_from_version(row)
    return {
        "id": row.id,
        "report_id": row.report_id,
        "version": row.version,
        "report_type": row.report_type,
        "input_json": _loads(row.input_json),
        "result_json": _loads(row.result_json),
        "markdown": row.markdown,
        "prompt_version": row.prompt_version,
        "model_used": row.model_used,
        "risk_check_result": _loads(row.risk_check_result),
        "references_json": _loads(row.references_json),
        "analysis_mode": analysis_mode,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _load_subject_chart(db: Session, subject_id: int) -> Optional[Dict[str, Any]]:
    chart = db.scalars(
        select(Chart).where(Chart.subject_id == subject_id).order_by(Chart.id.desc())
    ).first()
    if not chart:
        return None
    bazi = json.loads(chart.bazi_json) if chart.bazi_json else None
    wuxing = json.loads(chart.wuxing_json) if chart.wuxing_json else None
    return {
        "pillars": (bazi or {}).get("pillars") if isinstance(bazi, dict) else None,
        "wuxing": wuxing,
        "summary": chart.summary,
    }


def _compute_enriched_chart(subject: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """和对话场景一样，每次现算完整命盘（含十神 / 大运 / 流年）。"""
    bazi = chart_service.compute_chart(
        birth_date=subject.get("birth_date"),
        birth_time=subject.get("birth_time"),
        calendar_type=subject.get("calendar_type") or "solar",
        longitude=subject.get("longitude"),
        gender=subject.get("gender"),
    )
    return bazi if bazi.get("available") else None


def generate_report(
    db: Session,
    *,
    subject_id: int,
    report_type: str = "general",
    question: Optional[str] = None,
    analysis_mode: str = analysis_mode_service.SAFE_MODE,
) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.validate_analysis_mode(analysis_mode)
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        raise ValueError(f"subject {subject_id} not found")

    template_name = REPORT_TYPE_TO_TEMPLATE.get(report_type, "general_analysis")
    chart = _compute_enriched_chart(subject) or _load_subject_chart(db, subject_id)

    ctx = prompt_service.build_subject_context(subject, chart if isinstance(chart, dict) else None)
    ctx["question"] = question or "请生成一份较完整的综合命理分析报告。"
    ctx.update(analysis_mode_service.build_prompt_context(analysis_mode, module="bazi"))
    reference_input = {
        "subject": subject,
        "chart": chart,
        "question": question,
        "report_type": report_type,
        "analysis_mode": analysis_mode,
    }
    references = report_reference_service.collect_references(
        db,
        report_type=report_type,
        input_json=reference_input,
        limit=5,
    )
    ctx.update(report_reference_service.build_prompt_context(references))

    subject_block = prompt_service.render_subject_block(ctx)
    ctx["subject_block"] = subject_block
    db_template = prompt_service.get_db_template(db, "bazi_report")
    prompt_version = prompt_service.PROMPT_VERSION
    system_prompt = prompt_service.get_system_prompt(analysis_mode, module="bazi")
    if db_template:
        rendered = prompt_service.render_db_template(db_template, ctx)
        prompt_version = rendered["version"]
        system_prompt = rendered["system_prompt"] or system_prompt
        user_prompt = rendered["user_prompt"]
    else:
        user_prompt = subject_block + "\n" + prompt_service.render_user_prompt(template_name, ctx)
    user_prompt = report_reference_service.append_reference_block(user_prompt, references)

    llm = llm_service.chat_complete(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=4096,
        temperature=0.5,
    )

    if not llm["ok"]:
        # 写入一份「降级报告」，保证前端能展示
        content = (
            f"很抱歉，当前未能成功调用 AI 模型生成完整报告（错误：{llm.get('error')}）。\n\n"
            "请检查 .env 中的 API Key 配置（DEEPSEEK_API_KEY 或其他可用 Provider）后重试。"
        )
        content = prompt_service.append_disclaimer(content)
    else:
        content = llm["content"]

    content = prompt_service.append_mode_warning(content, analysis_mode)
    risk = risk_service.check_text(db, content, analysis_mode=analysis_mode)
    content = risk_service.final_text_for_mode(content, risk)
    title = f"{REPORT_TYPE_LABEL.get(report_type, report_type)} · {subject['nickname']}"
    report = Report(
        subject_id=subject_id,
        report_type=report_type,
        title=title,
        content=content,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    version = ReportVersion(
        report_id=report.id,
        version="1",
        report_type=report_type,
        input_json=json.dumps(
            {
                "subject_id": subject_id,
                "report_type": report_type,
                "question": question,
                "template_name": template_name,
                "references": references,
                "analysis_mode": analysis_mode,
            },
            ensure_ascii=False,
        ),
        result_json=json.dumps({"ok": llm["ok"], "provider": llm.get("provider")}, ensure_ascii=False),
        markdown=content,
        prompt_version=prompt_version,
        model_used=llm.get("model"),
        risk_check_result=json.dumps(risk, ensure_ascii=False),
        references_json=json.dumps(references, ensure_ascii=False),
    )
    db.add(version)
    db.commit()
    return _serialize(report, has_references=bool(references))


def list_reports(
    db: Session,
    subject_id: Optional[int] = None,
    has_references: Optional[bool] = None,
    analysis_mode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    normalized_mode = (
        analysis_mode_service.validate_analysis_mode(analysis_mode)
        if analysis_mode
        else None
    )
    stmt = select(Report).order_by(Report.id.desc())
    if subject_id is not None:
        stmt = stmt.where(Report.subject_id == subject_id)
    rows = db.scalars(stmt).all()
    items: List[Dict[str, Any]] = []
    for row in rows:
        latest = db.scalars(
            select(ReportVersion)
            .where(ReportVersion.report_id == row.id)
            .order_by(ReportVersion.id.desc())
        ).first()
        row_has_references = report_reference_service.has_real_references(
            latest.references_json if latest else None
        )
        row_analysis_mode = _analysis_mode_from_version(latest)
        if has_references is not None and row_has_references != has_references:
            continue
        if normalized_mode is not None and row_analysis_mode != normalized_mode:
            continue
        item = _serialize(row, has_references=row_has_references)
        item["analysis_mode"] = row_analysis_mode
        items.append(item)
    return items


def get_report(db: Session, report_id: int) -> Optional[Dict[str, Any]]:
    r = db.get(Report, report_id)
    if not r:
        return None
    data = _serialize(r)
    latest = db.scalars(
        select(ReportVersion).where(ReportVersion.report_id == report_id).order_by(ReportVersion.id.desc())
    ).first()
    if latest:
        data["latest_version"] = _serialize_version(latest)
        data["has_references"] = report_reference_service.has_real_references(latest.references_json)
        data["analysis_mode"] = _analysis_mode_from_version(latest)
    else:
        data["analysis_mode"] = analysis_mode_service.SAFE_MODE
    return data


def list_report_versions(db: Session, report_id: int) -> Optional[List[Dict[str, Any]]]:
    if not db.get(Report, report_id):
        return None
    rows = db.scalars(
        select(ReportVersion).where(ReportVersion.report_id == report_id).order_by(ReportVersion.id.desc())
    ).all()
    return [_serialize_version(row) for row in rows]


def get_report_version(db: Session, report_id: int, version_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(ReportVersion, version_id)
    if not row or row.report_id != report_id:
        return None
    return _serialize_version(row)
