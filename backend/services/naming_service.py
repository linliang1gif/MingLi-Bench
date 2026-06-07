"""起名工具 MVP 服务。"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..db.models import NamingRecord
from ..domain.naming_rules import build_name_candidates, is_name_safe
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service


def _fallback(payload: Dict[str, Any], naming_type: str) -> Dict[str, Any]:
    count = int(payload.get("count") or 20)
    suffix = "AI" if naming_type in {"company", "brand"} else ""
    raw_names = build_name_candidates(payload.get("keywords"), count * 2, suffix=suffix)
    names: List[Dict[str, Any]] = []
    avoid_words = payload.get("avoid_words") or []
    for name in raw_names:
        if not is_name_safe(name, avoid_words):
            continue
        score = max(70, 96 - len(names) * 2)
        names.append(
            {
                "name": name,
                "score": score,
                "meaning": "取其简洁、易记、具有传统文化气息。",
                "style_match": payload.get("style") or "稳重、清晰",
                "risk_note": "未发现明显迷信承诺或低俗表达。",
            }
        )
        if len(names) >= count:
            break
    markdown = "### 起名结果\n" + "\n".join(
        f"- **{item['name']}**（{item['score']}）：{item['meaning']} {item['risk_note']}"
        for item in names
    )
    return {"names": names, "markdown": markdown}


def generate(db: Session, naming_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.normalize_mode_from_input(payload)
    payload = {**payload, "analysis_mode": analysis_mode}
    base = _fallback(payload, naming_type)
    references = report_reference_service.collect_references(
        db,
        report_type="naming_report",
        input_json={"naming_type": naming_type, **payload},
    )
    tpl = prompt_service.get_db_template(db, "naming")
    llm = None
    if tpl:
        rendered = prompt_service.render_db_template(
            tpl,
            {
                "input_json": json.dumps({"naming_type": naming_type, **payload}, ensure_ascii=False),
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
            temperature=0.6,
        )
        if llm["ok"] and llm.get("content"):
            base["markdown"] = llm["content"]
    base["markdown"] = prompt_service.append_mode_warning(base["markdown"], analysis_mode)
    risk = risk_service.check_text(db, base["markdown"], analysis_mode=analysis_mode)
    base["markdown"] = risk_service.final_text_for_mode(base["markdown"], risk)
    base.update(
        {
            "naming_type": naming_type,
            "analysis_mode": analysis_mode,
            "risk_check_result": risk,
            "model_used": llm.get("model") if llm else None,
            "references_json": references,
            "reference_note": (
                "已保存系统检索到的古籍引用。"
                if references
                else "暂无古籍引用来源"
            ),
        }
    )
    row = NamingRecord(
        naming_type=naming_type,
        input_json=json.dumps(payload, ensure_ascii=False),
        result_json=json.dumps(base, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    base["record_id"] = row.id
    return base
