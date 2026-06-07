"""择日黄历 MVP 服务。"""

from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from ..db.models import DateSelectionRecord
from ..domain.date_rules import choose_candidate_dates
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service


_EVENT_LABELS = {
    "wedding": "婚期择日",
    "move-in": "搬家入宅",
    "opening": "开业择日",
    "renovation": "装修开工",
    "bed": "安床择日",
}


def _fallback_markdown(event_type: str, payload: Dict[str, Any], candidates: Dict[str, Any]) -> str:
    label = _EVENT_LABELS.get(event_type, event_type)
    rec = "、".join(candidates["recommended_dates"]) or "暂无"
    bak = "、".join(candidates["backup_dates"]) or "暂无"
    avoid = "、".join(candidates["avoid_dates"]) or "暂无"
    return f"""### 1. 结论
本次为「{label}」第一版择日参考，优先结合可执行日期、现实约束与传统文化习惯综合判断。

### 2. 推荐日期
{rec}

### 3. 备选日期
{bak}

### 4. 不建议日期
{avoid}

### 5. 传统择日参考
第一版暂不做复杂神煞推演，建议避开明显冲突的家庭安排、天气风险和交通压力。

### 6. 现实执行建议
提前确认场地、人员、交通、物料与当地习俗，重要事项以现实可执行性优先。

### 7. 当日流程建议
将关键流程安排在精力最稳定的时段，预留缓冲时间。

### 8. 注意事项
日期仅作传统文化参考，不宜替代合同、天气、预算等现实判断。

### 9. 风险提醒
避免用绝对吉凶做重大决策。"""


def generate(db: Session, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.normalize_mode_from_input(payload)
    payload = {**payload, "analysis_mode": analysis_mode}
    candidates = choose_candidate_dates(
        payload["start_date"], payload["end_date"], payload.get("available_dates")
    )
    input_json = json.dumps(payload, ensure_ascii=False)
    references = report_reference_service.collect_references(
        db,
        report_type="date_selection_report",
        input_json={"event_type": event_type, **payload, **candidates},
    )
    tpl = prompt_service.get_db_template(db, "date_selection")
    llm = None
    markdown = ""
    if tpl:
        rendered = prompt_service.render_db_template(
            tpl,
            {
                "input_json": input_json,
                "analysis_mode": analysis_mode,
                **report_reference_service.build_prompt_context(references),
            },
        )
        user_prompt = report_reference_service.append_reference_block(
            rendered["user_prompt"],
            references,
        )
        llm = llm_service.chat_complete(
            system_prompt=rendered["system_prompt"],
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=2500,
            temperature=0.4,
        )
        markdown = llm["content"] if llm["ok"] else ""
    if not markdown:
        markdown = _fallback_markdown(event_type, payload, candidates)
    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    result = {
        "event_type": event_type,
        **candidates,
        "summary": f"{_EVENT_LABELS.get(event_type, event_type)}已生成",
        "analysis_mode": analysis_mode,
        "markdown": markdown,
        "risk_check_result": risk,
        "model_used": llm.get("model") if llm else None,
        "references_json": references,
        "reference_note": (
            "已保存系统检索到的古籍引用。"
            if references
            else "暂无古籍引用来源"
        ),
    }
    row = DateSelectionRecord(
        event_type=event_type,
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        city=payload.get("city"),
        input_json=input_json,
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    result["record_id"] = row.id
    return result
