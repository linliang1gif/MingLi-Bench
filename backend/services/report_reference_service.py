"""Knowledge reference retrieval for generated reports."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from . import knowledge_service


REPORT_TYPE_CATEGORY_MAP: Dict[str, List[str]] = {
    "bazi_report": ["02", "31", "52"],
    "general": ["02", "31", "52"],
    "wealth": ["02", "31", "52"],
    "career": ["02", "31", "52"],
    "relationship": ["02", "31", "52"],
    "yearly": ["02", "31", "52"],
    "fengshui_basic": ["09", "12", "15", "21", "22", "60"],
    "fengshui_basic_report": ["09", "12", "15", "21", "22", "60"],
    "fengshui_xuankong_report": ["11", "14", "17", "21"],
    "fengshui_photo_report": ["12", "21", "22", "25", "60"],
    "landscape_photo_report": ["09", "10", "12", "13", "18", "21", "22", "60"],
    "heritage_risk_record_report": ["09", "10", "13", "18", "21", "60"],
    "date_selection_report": ["26", "27", "51", "52"],
    "naming_report": ["28", "31", "58"],
    "word_divination_report": ["01", "44", "53"],
    "lottery_report": ["45", "53"],
    "yinzhai_study_report": ["09", "10", "13", "19", "20", "21"],
    "tianxing_fengshui_report": ["18", "21", "30", "35"],
}


REPORT_TYPE_QUERY_HINTS: Dict[str, List[str]] = {
    "bazi_report": ["八字", "命理", "五行", "十神", "大运", "流年"],
    "general": ["八字", "命理", "五行", "十神", "大运", "流年"],
    "wealth": ["八字", "财运", "财星", "五行", "大运"],
    "career": ["八字", "事业", "官杀", "格局", "大运"],
    "relationship": ["八字", "感情", "婚恋", "夫妻", "五行"],
    "yearly": ["八字", "流年", "大运", "岁运", "神煞"],
    "fengshui_basic": ["阳宅", "大门", "门", "主", "灶", "罗盘", "二十四山"],
    "fengshui_xuankong_report": ["玄空", "飞星", "三元九运", "九宫", "二十四山"],
    "fengshui_photo_report": ["阳宅", "卧室", "床", "门", "窗", "镜", "横梁", "装修"],
    "landscape_photo_report": ["外局", "形势", "砂水", "道路", "水口", "明堂", "二十四山", "天星", "阴宅", "阳宅"],
    "heritage_risk_record_report": ["文物保护", "文保风险", "山势", "地貌", "人工痕迹", "扰动", "现场保护", "上报"],
    "date_selection_report": ["择日", "通书", "入宅", "开业", "婚嫁", "动工"],
    "naming_report": ["起名", "姓名", "五行", "字义", "数理"],
    "word_divination_report": ["测字", "字形", "字义", "易象"],
    "lottery_report": ["灵签", "签诗", "解签"],
}

REPORT_TYPE_QUERY_HINTS.update(
    {
        "yinzhai_study_report": ["阴宅", "葬经", "龙穴砂水向", "来龙", "穴场", "砂水", "罗盘", "二十四山"],
        "tianxing_fengshui_report": ["天星风水", "天星", "二十四山", "罗盘", "玉尺", "星宿", "天文历法"],
    }
)


def _flatten_text(value: Any, parts: List[str], depth: int = 0) -> None:
    if value is None or depth > 4 or len(parts) >= 80:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).startswith("_"):
                continue
            _flatten_text(item, parts, depth + 1)
    elif isinstance(value, (list, tuple, set)):
        items = value[:20] if isinstance(value, list) else list(value)[:20]
        for item in items:
            _flatten_text(item, parts, depth + 1)
    elif isinstance(value, (str, int, float)):
        text = str(value).strip()
        if text and len(text) <= 120:
            parts.append(text)


def build_query(report_type: str, input_json: Any) -> str:
    hints = REPORT_TYPE_QUERY_HINTS.get(report_type) or REPORT_TYPE_QUERY_HINTS.get("bazi_report", [])
    parts: List[str] = list(hints)
    _flatten_text(input_json, parts)
    text = " ".join(parts)
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_/-]{2,}", text)
    seen = set()
    deduped = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
        if len(deduped) >= 20:
            break
    return " ".join(deduped)


def _reference_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "chunk_id": row.get("chunk_id") or row.get("id"),
        "book_id": row.get("book_id"),
        "book_title": row.get("book_title"),
        "chapter": row.get("chapter"),
        "section": row.get("section"),
        "source_ref": row.get("source_ref"),
        "original_text": row.get("original_text"),
        "explanation": row.get("explanation"),
        "tags": row.get("tags") or [],
        "applicable_modules": row.get("applicable_modules") or [],
        "reliability_level": row.get("reliability_level"),
        "risk_level": row.get("risk_level"),
    }


def collect_references(
    db: Session,
    *,
    report_type: str,
    input_json: Any,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    categories = REPORT_TYPE_CATEGORY_MAP.get(report_type) or REPORT_TYPE_CATEGORY_MAP.get("bazi_report", [])
    query = build_query(report_type, input_json)
    refs: List[Dict[str, Any]] = []
    seen = set()
    for category_code in categories:
        try:
            result = knowledge_service.search(
                db,
                query=query,
                category_code=category_code,
                applicable_module=report_type,
                limit=limit,
            )
            rows = result.get("results") or []
            if not rows:
                result = knowledge_service.search(
                    db,
                    query=query,
                    category_code=category_code,
                    limit=limit,
                )
                rows = result.get("results") or []
        except Exception:
            rows = []
        for row in rows:
            key = row.get("chunk_id") or row.get("id")
            if not key or key in seen:
                continue
            seen.add(key)
            refs.append(_reference_from_row(row))
            if len(refs) >= limit:
                return refs
    return refs


def format_references(references: Iterable[Dict[str, Any]]) -> str:
    refs = list(references or [])
    if not refs:
        return "暂无古籍引用来源"
    lines = []
    for index, ref in enumerate(refs, start=1):
        source = ref.get("source_ref") or ref.get("chapter") or "未标注出处"
        original = (ref.get("original_text") or "").strip()
        explanation = (ref.get("explanation") or "").strip()
        if len(original) > 90:
            original = original[:90] + "..."
        if len(explanation) > 120:
            explanation = explanation[:120] + "..."
        lines.append(
            "\n".join(
                [
                    f"{index}. chunk #{ref.get('chunk_id')} | {ref.get('book_title') or '未命名古籍'} | {source}",
                    f"   原文：{original or '未提供'}",
                    f"   解释：{explanation or '未提供'}",
                ]
            )
        )
    return "\n".join(lines)


def reference_notes(references: Iterable[Dict[str, Any]]) -> str:
    refs = list(references or [])
    if not refs:
        return "暂无古籍引用来源。报告不得虚构书名、章节或出处；如需引用，请明确说明当前系统未提供。"
    return (
        "只能引用上方系统提供的 references。不得虚构书名、章节、作者或出处；"
        "references_json 由系统保存，不由 AI 自行生成。"
    )


def build_prompt_context(references: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    refs = list(references or [])
    return {
        "references": format_references(refs),
        "reference_count": len(refs),
        "reference_notes": reference_notes(refs),
    }


def append_reference_block(user_prompt: str, references: Iterable[Dict[str, Any]]) -> str:
    if "【系统提供的古籍引用】" in (user_prompt or ""):
        return user_prompt or ""
    context = build_prompt_context(references)
    return (
        (user_prompt or "").rstrip()
        + "\n\n【系统提供的古籍引用】\n"
        + context["references"]
        + f"\n\n引用数量：{context['reference_count']}\n"
        + "【引用约束】\n"
        + context["reference_notes"]
    )


def has_real_references(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        parsed = json.loads(value)
    except Exception:
        return bool(str(value).strip())
    if isinstance(parsed, list):
        return len(parsed) > 0
    return False
