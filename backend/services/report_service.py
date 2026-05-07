"""报告生成与读取。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Chart, Report, Subject
from . import chart_service, llm_service, prompt_service, subject_service


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
}


def _serialize(report: Report) -> Dict[str, Any]:
    return {
        "id": report.id,
        "subject_id": report.subject_id,
        "report_type": report.report_type,
        "title": report.title,
        "content": report.content,
        "created_at": report.created_at.isoformat() if report.created_at else None,
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


def generate_report(
    db: Session, *, subject_id: int, report_type: str = "general", question: Optional[str] = None
) -> Dict[str, Any]:
    subject = subject_service.get_subject(db, subject_id)
    if not subject:
        raise ValueError(f"subject {subject_id} not found")

    template_name = REPORT_TYPE_TO_TEMPLATE.get(report_type, "general_analysis")
    chart = _load_subject_chart(db, subject_id) or chart_service.compute_chart(
        birth_date=subject.get("birth_date"), birth_time=subject.get("birth_time")
    )

    ctx = prompt_service.build_subject_context(subject, chart if isinstance(chart, dict) else None)
    ctx["question"] = question or "请生成一份较完整的综合命理分析报告。"
    user_prompt = prompt_service.render_user_prompt(template_name, ctx)

    llm = llm_service.chat_complete(
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=2048,
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
    return _serialize(report)


def list_reports(db: Session, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
    stmt = select(Report).order_by(Report.id.desc())
    if subject_id is not None:
        stmt = stmt.where(Report.subject_id == subject_id)
    rows = db.scalars(stmt).all()
    return [_serialize(r) for r in rows]


def get_report(db: Session, report_id: int) -> Optional[Dict[str, Any]]:
    r = db.get(Report, report_id)
    return _serialize(r) if r else None
