"""Yinzhai study rules and fallback report text.

V1.4 intentionally treats yinzhai as cultural research and environment notes.
It must not produce burial relocation, grave-moving, ritual, or fear-based advice.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


SITE_TYPE_LABELS = {
    "ancestral_grave": "祖坟资料",
    "cemetery": "墓园环境",
    "memorial_site": "纪念空间",
    "study_case": "研究案例",
    "other": "其他",
}

BOUNDARY_NOTE = (
    "本功能仅用于传统文化研究、堪舆资料整理和环境记录；不做墓地吉凶强断，"
    "不提供改葬、迁坟、法事化解或诱导消费建议。"
)


def site_type_label(value: str | None) -> str:
    return SITE_TYPE_LABELS.get(value or "", value or "未标注")


def _brief(value: Any, fallback: str = "未填写") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item not in (None, "", [], {}):
                parts.append(f"{key}: {item}")
        return "；".join(parts) if parts else fallback
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return "；".join(items) if items else fallback
    return str(value)


def normalize_observation(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dragon": payload.get("dragon") or {},
        "cave": payload.get("cave") or {},
        "sand": payload.get("sand") or {},
        "water": payload.get("water") or {},
        "direction": payload.get("direction") or {},
        "environment": payload.get("environment") or {},
    }


def build_result(payload: Dict[str, Any], *, mountain: Dict[str, Any] | None, facing: Dict[str, Any] | None) -> Dict[str, Any]:
    observations = normalize_observation(payload)
    completion = 0
    for value in observations.values():
        if _brief(value, ""):
            completion += 1
    return {
        "study_type": "yinzhai_cultural_research",
        "title": payload.get("title"),
        "site_type": payload.get("site_type"),
        "site_type_label": site_type_label(payload.get("site_type")),
        "location_note": payload.get("location_note"),
        "mountain": mountain,
        "facing": facing,
        "observations": observations,
        "research_note": payload.get("research_note"),
        "completion_score": completion,
        "method_note": BOUNDARY_NOTE,
    }


def summarize_references(references: Iterable[Dict[str, Any]]) -> str:
    refs = list(references or [])
    titles = sorted({ref.get("book_title") for ref in refs if ref.get("book_title")})
    return "、".join(titles) if titles else "暂无古籍引用来源"


def fallback_markdown(
    *,
    record: Dict[str, Any],
    result: Dict[str, Any],
    references: List[Dict[str, Any]],
) -> str:
    observations = result.get("observations") or {}
    mountain = result.get("mountain") or {}
    facing = result.get("facing") or {}
    ref_titles = summarize_references(references)
    return f"""### 1. 结论
本报告为「{record.get('title')}」的阴宅研究记录说明，定位是传统文化资料整理与环境观察，不作墓地吉凶强断。当前记录完整度约为 {result.get('completion_score', 0)} / 6，适合继续补充现场环境、罗盘数据和古籍引用。

### 2. 研究对象与边界
- 类型：{site_type_label(record.get('site_type'))}
- 位置备注：{record.get('location_note') or '未填写'}
- 边界：{BOUNDARY_NOTE}

### 3. 龙穴砂水向记录
- 龙：{_brief(observations.get('dragon'))}
- 穴：{_brief(observations.get('cave'))}
- 砂：{_brief(observations.get('sand'))}
- 水：{_brief(observations.get('water'))}
- 向：{_brief(observations.get('direction'))}

### 4. 坐向与罗盘资料
- 坐山角度：{mountain.get('degree', '未填写')}；二十四山：{mountain.get('direction_24') or '未填写'}
- 向首角度：{facing.get('degree', '未填写')}；二十四山：{facing.get('direction_24') or '未填写'}
- 说明：二十四山仅用于记录方位语言，不直接推出绝对吉凶。

### 5. 形势观察
{_brief(observations.get('environment'))}

### 6. 古籍引用线索
本次可参考来源：{ref_titles}。若引用为空，表示当前本地知识库未检索到足够匹配条目，不应虚构书名、章节或出处。

### 7. 后续整理建议
- 补充现场照片、地形备注、来龙走势、水路方向、周边道路与建筑环境。
- 补充罗盘测点时，建议记录测量位置、时间、角度稳定性和备注。
- 结论应保持研究性表达，优先描述“可观察现象”和“资料依据”。

### 8. 风险提醒
{BOUNDARY_NOTE} 本报告不构成建筑、法律、医疗、投资或重大人生决策建议。
"""
