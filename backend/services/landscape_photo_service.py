"""外局拍照识别服务。"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..db.models import HouseProfile, LandscapePhotoRecord, Report, ReportVersion, Subject
from ..domain import compass, landscape_photo_rules, tianxing_rules
from . import analysis_mode_service, llm_service, prompt_service, report_reference_service, risk_service
from .house_service import get_house, list_compass_records


LANDSCAPE_REPORT_TYPE = "landscape_photo_report"
HERITAGE_REPORT_TYPE = "heritage_risk_record_report"
SYSTEM_SUBJECT_NAME = "系统 · 外局拍照研究报告"
UPLOAD_DIR = settings.storage_dir / "uploads" / "landscape_photo"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _system_subject_id(db: Session) -> int:
    subject = db.scalars(
        select(Subject).where(Subject.nickname == SYSTEM_SUBJECT_NAME).order_by(Subject.id.asc())
    ).first()
    if not subject:
        subject = Subject(
            nickname=SYSTEM_SUBJECT_NAME,
            gender="其他",
            calendar_type="solar",
            notes="系统自动创建，用于兼容 reports.subject_id 必填约束；外局拍照报告以记录与 house_id 为真实关联。",
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


def _serialize_record(row: LandscapePhotoRecord) -> Dict[str, Any]:
    return {
        "id": row.id,
        "house_id": row.house_id,
        "scene_type": row.scene_type,
        "scene_label": landscape_photo_rules.scene_label(row.scene_type),
        "target_label": row.target_label,
        "image_path": row.image_path,
        "degree": row.degree,
        "direction_8": row.direction_8,
        "direction_24": row.direction_24,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "location_note": row.location_note,
        "analysis_json": _loads(row.analysis_json),
        "user_correction_json": _loads(row.user_correction_json),
        "report_id": row.report_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_image_path(relative_path: str) -> Path:
    upload_root = UPLOAD_DIR.resolve()
    path = (settings.storage_dir / relative_path).resolve()
    if upload_root != path and upload_root not in path.parents:
        raise ValueError("image path escaped upload directory")
    return path


def _make_filename(original_name: str) -> str:
    ext = Path(original_name or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("unsupported image type, allowed: jpg, jpeg, png, webp")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    token = secrets.token_hex(6)
    return f"{stamp}-{token}{ext}"


def _relative_upload_path(filename: str) -> str:
    return str(Path("uploads") / "landscape_photo" / filename).replace("\\", "/")


def _copy_limited(src: BinaryIO, dest: Path) -> int:
    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                out.close()
                try:
                    dest.unlink(missing_ok=True)
                except Exception:
                    pass
                raise ValueError("image too large, max size is 10MB")
            out.write(chunk)
    return total


def _orientation_from_degree(degree: Optional[float]) -> Dict[str, Any]:
    if degree is None:
        return {}
    return compass.convert_degree(float(degree))


def _tianxing_from_record(row: LandscapePhotoRecord) -> Optional[Dict[str, Any]]:
    try:
        if row.degree is not None:
            return tianxing_rules.build_query_result({"degree": row.degree})
        if row.direction_24:
            return tianxing_rules.build_query_result({"mountain_24": row.direction_24})
    except Exception:
        return None
    return None


def _report_type_for_record(row: LandscapePhotoRecord) -> str:
    return landscape_photo_rules.report_type_for_scene(row.scene_type)


def _boundary_note_for_record(row: LandscapePhotoRecord) -> str:
    if landscape_photo_rules.is_heritage_scene(row.scene_type):
        return landscape_photo_rules.HERITAGE_BOUNDARY_NOTE
    return landscape_photo_rules.BOUNDARY_NOTE


def upload_photo(
    db: Session,
    *,
    house_id: Optional[int],
    scene_type: str,
    target_label: Optional[str],
    degree: Optional[float],
    latitude: Optional[float],
    longitude: Optional[float],
    location_note: Optional[str],
    filename: str,
    content_type: Optional[str],
    fileobj: BinaryIO,
) -> Dict[str, Any]:
    if house_id is not None and not db.get(HouseProfile, int(house_id)):
        raise ValueError(f"house {house_id} not found")
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("unsupported content type, allowed: jpg, jpeg, png, webp")

    scene_type = landscape_photo_rules.normalize_scene_type(scene_type)
    orientation = _orientation_from_degree(degree)
    _ensure_upload_dir()
    safe_name = _make_filename(filename)
    absolute_path = UPLOAD_DIR / safe_name
    image_path = _relative_upload_path(safe_name)
    _copy_limited(fileobj, absolute_path)

    row = LandscapePhotoRecord(
        house_id=int(house_id) if house_id is not None else None,
        scene_type=scene_type,
        target_label=target_label,
        image_path=image_path,
        degree=orientation.get("degree"),
        direction_8=orientation.get("direction_8"),
        direction_24=orientation.get("direction_24"),
        latitude=float(latitude) if latitude is not None else None,
        longitude=float(longitude) if longitude is not None else None,
        location_note=location_note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_record(row)


def analyze_photo(db: Session, record_id: int) -> Dict[str, Any]:
    row = db.get(LandscapePhotoRecord, int(record_id))
    if not row:
        raise ValueError("landscape photo record not found")
    image_file = _safe_image_path(row.image_path)
    if not image_file.exists():
        raise ValueError("image file not found")

    result = llm_service.analyze_image_objects(
        image_path=str(image_file),
        room_type=row.scene_type,
    )
    if result.get("ok") and isinstance(result.get("analysis"), dict):
        analysis = result["analysis"]
        analysis.setdefault("scene_type", row.scene_type)
        analysis.setdefault("scene_label", landscape_photo_rules.scene_label(row.scene_type))
        analysis.setdefault("target_label", row.target_label)
        analysis.setdefault("need_user_confirm", True)
        analysis.setdefault("source", result.get("provider") or "llm")
        analysis.setdefault("vision_provider", result.get("provider"))
        analysis.setdefault("vision_model", result.get("model"))
        analysis.setdefault("boundary_note", _boundary_note_for_record(row))
        if not analysis.get("objects"):
            analysis["vision_empty_objects"] = True
            analysis["note"] = (
                f"视觉模型已调用成功（{result.get('provider') or 'llm'}），但未返回可展示对象；"
                "请按照片实际情况在校正表单中补充。"
            )
    else:
        analysis = landscape_photo_rules.mock_analysis(row.scene_type, row.target_label)
        analysis["llm_error"] = result.get("error")
        if result.get("error") == "vision_model_not_configured":
            analysis["note"] = "当前未配置可用视觉模型，已返回可校正的占位识别结果。"
        else:
            analysis["note"] = f"视觉模型调用失败（{result.get('error') or 'unknown'}），已返回可校正的占位识别结果。"

    if landscape_photo_rules.is_heritage_scene(row.scene_type):
        analysis = landscape_photo_rules.sanitize_heritage_analysis(analysis)
    else:
        analysis = landscape_photo_rules.clean_landscape_analysis(analysis, row.scene_type)
        tianxing = _tianxing_from_record(row)
        if tianxing:
            analysis["tianxing"] = tianxing
    row.analysis_json = json.dumps(analysis, ensure_ascii=False)
    db.commit()
    db.refresh(row)
    return {"record": _serialize_record(row), "analysis": analysis}


def list_records(
    db: Session,
    house_id: Optional[int] = None,
    scene_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    stmt = select(LandscapePhotoRecord).order_by(LandscapePhotoRecord.id.desc())
    if house_id is not None:
        stmt = stmt.where(LandscapePhotoRecord.house_id == int(house_id))
    if scene_type:
        stmt = stmt.where(LandscapePhotoRecord.scene_type == scene_type)
    return [_serialize_record(row) for row in db.scalars(stmt).all()]


def get_record(db: Session, record_id: int) -> Optional[Dict[str, Any]]:
    row = db.get(LandscapePhotoRecord, int(record_id))
    return _serialize_record(row) if row else None


def generate_report(
    db: Session,
    record_id: int,
    user_correction: Dict[str, Any],
    analysis_mode: str = analysis_mode_service.SAFE_MODE,
) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.validate_analysis_mode(analysis_mode)
    row = db.get(LandscapePhotoRecord, int(record_id))
    if not row:
        raise ValueError("landscape photo record not found")
    if row.house_id is not None and not db.get(HouseProfile, row.house_id):
        raise ValueError(f"house {row.house_id} not found")

    report_type = _report_type_for_record(row)
    is_heritage = landscape_photo_rules.is_heritage_scene(row.scene_type)
    analysis = _loads(row.analysis_json) or landscape_photo_rules.mock_analysis(row.scene_type, row.target_label)
    if is_heritage:
        analysis = landscape_photo_rules.sanitize_heritage_analysis(analysis)
    correction = {**(user_correction or {}), "scene_type": row.scene_type, "target_label": row.target_label}
    row.user_correction_json = json.dumps(correction, ensure_ascii=False)

    house = get_house(db, row.house_id) if row.house_id is not None else None
    compass_records = list_compass_records(db, row.house_id) if row.house_id is not None else []
    compass_records = compass_records or []
    tianxing = _tianxing_from_record(row)
    record = _serialize_record(row)
    reference_input = {
        "record_id": row.id,
        "house_id": row.house_id,
        "house": house,
        "record": record,
        "analysis": analysis,
        "user_correction": correction,
        "compass_records": compass_records,
        "tianxing": tianxing,
        "boundary_note": _boundary_note_for_record(row),
        "report_type": report_type,
        "analysis_mode": analysis_mode,
    }
    if is_heritage:
        reference_input["forbidden_items"] = landscape_photo_rules.HERITAGE_FORBIDDEN_ITEMS
        reference_input["heritage_required_notice"] = landscape_photo_rules.HERITAGE_BOUNDARY_NOTE
    references = report_reference_service.collect_references(
        db,
        report_type=report_type,
        input_json=reference_input,
        limit=5,
    )
    input_payload = {
        **reference_input,
        "references": references,
        "analysis_mode": analysis_mode,
        "required_sections": landscape_photo_rules.required_sections_for_scene(row.scene_type),
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, indent=2)
    template = prompt_service.get_db_template(db, report_type)
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
            temperature=0.4,
        )
        markdown = llm["content"] if llm.get("ok") else ""

    if is_heritage and landscape_photo_rules.has_forbidden_heritage_output(markdown):
        markdown = ""

    if not markdown:
        if is_heritage:
            markdown = landscape_photo_rules.heritage_fallback_markdown(
                house=house,
                record=record,
                analysis=analysis,
                correction=correction,
                references=references,
            )
        else:
            markdown = landscape_photo_rules.fallback_markdown(
                house=house,
                record=record,
                analysis=analysis,
                correction=correction,
                compass_records=compass_records,
                tianxing=tianxing,
                references=references,
            )
    if is_heritage:
        markdown = landscape_photo_rules.ensure_heritage_notice(markdown)

    markdown = prompt_service.append_mode_warning(markdown, analysis_mode)
    risk = risk_service.check_text(db, markdown, analysis_mode=analysis_mode)
    markdown = risk_service.final_text_for_mode(markdown, risk)
    subject_id = _system_subject_id(db)
    title_house = (house or {}).get("name") or "未关联房屋"
    report_label = "文保风险记录报告" if is_heritage else "外局拍照研究报告"
    title = f"{report_label} · {title_house} · {landscape_photo_rules.scene_label(row.scene_type)}"
    report = Report(
        subject_id=subject_id,
        house_id=row.house_id,
        report_type=report_type,
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
        report_type=report_type,
        input_json=input_json,
        result_json=json.dumps(
            {
                "ok": llm.get("ok", False),
                "provider": llm.get("provider"),
                "landscape_photo_record_id": row.id,
                "house_id": row.house_id,
                "report_type": report_type,
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
        "record": _serialize_record(row),
        "subject_id": report.subject_id,
        "house_id": report.house_id,
        "report_type": report.report_type,
        "analysis_mode": analysis_mode,
        "title": report.title,
        "content": report.content,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def delete_record(db: Session, record_id: int) -> bool:
    row = db.get(LandscapePhotoRecord, int(record_id))
    if not row:
        return False
    image_path = row.image_path
    db.delete(row)
    db.commit()
    if image_path:
        try:
            path = _safe_image_path(image_path)
            if path.exists():
                path.unlink()
        except Exception:
            pass
    return True
