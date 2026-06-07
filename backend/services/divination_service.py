"""测字与灵签 MVP 服务。"""

from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from ..db.models import DivinationRecord
from ..domain.divination_rules import draw_sign
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service


def word_divination(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.normalize_mode_from_input(payload)
    payload = {**payload, "analysis_mode": analysis_mode}
    word = payload["word"]
    markdown = f"""### 1. 字形观察
    「{word}」字先看结构与动势，可作为观察问题的象征入口。

### 2. 字义解释
字义取其常见含义，结合提问语境作文化联想。

### 3. 传统文化联想
测字重在启发，不作确定预言。

### 4. 对当前问题的启发
围绕「{payload.get('question') or '当前问题'}」，建议看清资源、节奏与可持续性。

### 5. 现实建议
先做小范围验证，再逐步扩大投入。

### 6. 风险提醒
    本结果仅作娱乐和传统文化参考。"""
    references = report_reference_service.collect_references(
        db,
        report_type="word_divination_report",
        input_json=payload,
    )
    tpl = prompt_service.get_db_template(db, "word_divination")
    llm = None
    if tpl:
        rendered = prompt_service.render_db_template(
            tpl,
            {
                "input_json": json.dumps(payload, ensure_ascii=False),
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
            max_tokens=1800,
            temperature=0.5,
        )
        if llm["ok"]:
            markdown = llm["content"]
    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    result = {
        "word": word,
        "summary": "测字结果已生成",
        "analysis_mode": analysis_mode,
        "analysis": markdown,
        "advice": "将结果作为启发，结合现实数据继续判断。",
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
    row = DivinationRecord(
        divination_type="word",
        input_json=json.dumps(payload, ensure_ascii=False),
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    result["record_id"] = row.id
    return result


def lottery(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.normalize_mode_from_input(payload)
    payload = {**payload, "analysis_mode": analysis_mode}
    sign = draw_sign(payload.get("sign_no"))
    llm_input = {**payload, **sign}
    references = report_reference_service.collect_references(
        db,
        report_type="lottery_report",
        input_json=llm_input,
    )
    markdown = f"""### 灵签结果
第 {sign['sign_no']} 签，签等：{sign['level']}。

### 解读
此签只作娱乐和传统文化参考。当前问题宜稳中求进，先验证方向，再增加投入。

### 建议
保留现实计划、预算和复盘机制，避免把签文当成确定性结论。"""
    tpl = prompt_service.get_db_template(db, "lottery")
    llm = None
    if tpl:
        rendered = prompt_service.render_db_template(
            tpl,
            {
                "input_json": json.dumps(llm_input, ensure_ascii=False),
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
            max_tokens=1600,
            temperature=0.5,
        )
        if llm["ok"]:
            markdown = llm["content"]
    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    result = {
        **sign,
        "summary": "灵签结果已生成",
        "analysis_mode": analysis_mode,
        "explanation": markdown,
        "advice": "仅作娱乐和传统文化参考，不作强断。",
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
    row = DivinationRecord(
        divination_type="lottery",
        input_json=json.dumps(payload, ensure_ascii=False),
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    result["record_id"] = row.id
    return result
