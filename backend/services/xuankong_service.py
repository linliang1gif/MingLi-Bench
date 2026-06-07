"""玄空飞星基础盘服务。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import HouseProfile, Report, ReportVersion, Subject, XuanKongRecord
from ..domain import xuankong
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service
from .house_service import get_house


REPORT_TYPE = "fengshui_xuankong_report"
SYSTEM_SUBJECT_NAME = "系统 · 玄空飞星报告"


def _system_subject_id(db: Session) -> int:
    subject = db.scalars(
        select(Subject).where(Subject.nickname == SYSTEM_SUBJECT_NAME).order_by(Subject.id.asc())
    ).first()
    if not subject:
        subject = Subject(
            nickname=SYSTEM_SUBJECT_NAME,
            gender="其他",
            calendar_type="solar",
            notes="系统自动创建，用于兼容 reports.subject_id 必填约束；玄空报告以 house_id 为真实关联。",
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


def _serialize_record(row: XuanKongRecord) -> Dict[str, Any]:
    return {
        "id": row.id,
        "house_id": row.house_id,
        "build_year": row.build_year,
        "move_in_year": row.move_in_year,
        "period": row.period,
        "period_number": row.period_number,
        "facing_degree": row.facing_degree,
        "facing_direction_24": row.facing_direction_24,
        "sitting_direction_24": row.sitting_direction_24,
        "base_star_json": _loads(row.base_star_json),
        "annual_star_json": _loads(row.annual_star_json),
        "result_json": _loads(row.result_json),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _resolve_input(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    house_id = payload.get("house_id")
    house: Optional[HouseProfile] = db.get(HouseProfile, int(house_id)) if house_id else None
    if house_id and not house:
        raise ValueError(f"house {house_id} not found")

    build_year = payload.get("build_year")
    if build_year is None and house:
        build_year = house.build_year
    if build_year is None:
        raise ValueError("build_year is required")

    move_in_year = payload.get("move_in_year")
    if move_in_year is None and house and house.move_in_date:
        try:
            move_in_year = int(str(house.move_in_date)[:4])
        except Exception:
            move_in_year = None

    facing_degree = payload.get("facing_degree")
    if payload.get("use_house_main_door") and house:
        facing_degree = house.main_door_degree
    if facing_degree is None and house and house.main_door_degree is not None:
        facing_degree = house.main_door_degree
    if facing_degree is None:
        raise ValueError("facing_degree is required")

    return {
        "house": house,
        "house_id": house.id if house else None,
        "build_year": int(build_year),
        "move_in_year": int(move_in_year) if move_in_year else None,
        "facing_degree": float(facing_degree),
        "annual_year": int(payload["annual_year"]) if payload.get("annual_year") else None,
    }


def period(year: int) -> Dict[str, Any]:
    return xuankong.period_for_year(year)


def calculate(payload: Dict[str, Any]) -> Dict[str, Any]:
    return xuankong.build_basic_chart(
        build_year=payload["build_year"],
        move_in_year=payload.get("move_in_year"),
        facing_degree=payload["facing_degree"],
        annual_year=payload.get("annual_year"),
    )


def save_record(db: Session, *, house_id: Optional[int], result: Dict[str, Any]) -> Dict[str, Any]:
    period_data = result["period"]
    facing = result["facing"]
    row = XuanKongRecord(
        house_id=house_id,
        build_year=result["build_year"],
        move_in_year=result.get("move_in_year"),
        period=period_data["period"],
        period_number=period_data["period_number"],
        facing_degree=facing["degree"],
        facing_direction_24=facing["facing_direction_24"],
        sitting_direction_24=facing["sitting_direction_24"],
        base_star_json=json.dumps(result["base_star"], ensure_ascii=False),
        annual_star_json=json.dumps(result["annual_star"], ensure_ascii=False),
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_record(row)


def calculate_for_request(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    resolved = _resolve_input(db, payload)
    result = calculate(resolved)
    response = {"result": result, "record": None}
    if resolved["house_id"]:
        response["record"] = save_record(db, house_id=resolved["house_id"], result=result)
    return response


def list_records(db: Session, house_id: Optional[int] = None) -> List[Dict[str, Any]]:
    stmt = select(XuanKongRecord).order_by(XuanKongRecord.id.desc())
    if house_id is not None:
        stmt = stmt.where(XuanKongRecord.house_id == house_id)
    return [_serialize_record(row) for row in db.scalars(stmt).all()]


def _fallback_markdown(house: Dict[str, Any], result: Dict[str, Any]) -> str:
    facing = result["facing"]
    period_data = result["period"]
    rows = []
    for cell in result["grid"]:
        rows.append(
            f"- {cell['name']}（{cell['direction']}）：运星 {cell['base_star']}，年星 {cell['annual_star']}"
        )
    grid_block = "\n".join(rows)
    return f"""### 一、结论
本报告为「{house.get('name')}」的玄空飞星基础盘。当前以 {period_data['period']} 为运盘核心，向首为 **{facing['facing_direction_24']}**，坐山为 **{facing['sitting_direction_24']}**。

### 二、基础信息
- 建成年份：{result.get('build_year')}
- 入住年份：{result.get('move_in_year') or '未填写，按建成年份取运'}
- 取运年份：{result.get('effective_period_year')}
- 朝向角度：{facing.get('degree')}°
- 坐向：坐{facing['sitting_direction_24']}向{facing['facing_direction_24']}

### 三、九宫基础盘
{grid_block}

### 四、解读提示
- 本版采用「运星入中顺飞」与「年星入中顺飞」生成基础盘，适合做初步空间观察。
- 可重点观察中宫、向首相关区域，以及大门、卧室、厨房、书桌等实际活动频繁位置。
- 若房屋信息或主门角度不准确，应先补测后再生成报告。

### 五、版本边界
{result.get('method_note')}

### 六、风险提醒
玄空飞星报告仅作传统文化与空间观察参考，不构成建筑、医疗、法律、投资或重大决策建议。"""


def generate_report(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.normalize_mode_from_input(payload)
    payload = {**payload, "analysis_mode": analysis_mode}
    resolved = _resolve_input(db, {**payload, "use_house_main_door": payload.get("use_house_main_door", True)})
    if not resolved["house_id"]:
        raise ValueError("house_id is required")
    house = get_house(db, resolved["house_id"])
    if not house:
        raise ValueError(f"house {resolved['house_id']} not found")

    result = calculate(resolved)
    record = save_record(db, house_id=resolved["house_id"], result=result)
    reference_input = {
        "house_id": resolved["house_id"],
        "house": house,
        "xuankong_record_id": record["id"],
        "calculation": result,
        "analysis_mode": analysis_mode,
    }
    references = report_reference_service.collect_references(
        db,
        report_type=REPORT_TYPE,
        input_json=reference_input,
        limit=5,
    )
    input_payload = {
        "house_id": resolved["house_id"],
        "house": house,
        "xuankong_record_id": record["id"],
        "calculation": result,
        "references": references,
        "analysis_mode": analysis_mode,
        "required_sections": ["结论", "基础信息", "坐向与取运", "九宫基础盘", "空间建议", "版本边界", "风险提醒"],
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, indent=2)
    template = prompt_service.get_db_template(db, "fengshui_xuankong_report")
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
            temperature=0.45,
        )
        markdown = llm["content"] if llm.get("ok") else ""

    if not markdown:
        markdown = _fallback_markdown(house, result)

    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    subject_id = _system_subject_id(db)
    title = f"玄空飞星报告 · {house['name']}"
    report = Report(
        subject_id=subject_id,
        house_id=resolved["house_id"],
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
                "house_id": resolved["house_id"],
                "xuankong_record_id": record["id"],
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
        "subject_id": report.subject_id,
        "house_id": report.house_id,
        "report_type": report.report_type,
        "analysis_mode": analysis_mode,
        "title": report.title,
        "content": report.content,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "xuankong_record": record,
    }
