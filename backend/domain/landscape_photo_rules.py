"""外局拍照识别的轻量规则与 fallback 文案。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


SCENE_TYPE_LABELS = {
    "yinzhai_environment": "阴宅环境",
    "tianxing_site": "天星现场方向",
    "house_landscape": "房屋外局",
    "heritage_risk": "文保风险记录",
    "manual_target": "手动目标",
}

OBJECT_LABELS = {
    "mountain": "山体/高处",
    "water": "水体",
    "road": "道路",
    "building": "建筑",
    "tree": "树木",
    "field": "田野/草地",
    "farmland": "农田",
    "grassland": "草地",
    "pole": "杆塔",
    "bridge": "桥梁",
    "gate": "门口/入口",
    "slope": "坡地",
    "open_space": "明堂/开阔地",
    "path": "小路",
    "target": "手动目标",
    "artificial_mound": "疑似人工堆土/封土样地貌",
    "stone_object": "石构件/石刻样对象",
    "inscription": "文字刻痕/铭文样痕迹",
    "surface_artifact": "地表遗物样对象",
    "recent_disturbance": "近期扰动痕迹",
}

BOUNDARY_NOTE = (
    "外局拍照识别仅用于传统文化研究、现场环境记录和资料整理。"
    "照片只能反映局部视角，不作墓地、住宅或环境吉凶强断，"
    "不提供改葬、迁坟、法事化解或诱导消费建议。"
)

HERITAGE_BOUNDARY_NOTE = (
    "本报告仅用于文物保护风险记录和环境信息整理。"
    "不得用于寻找、定位、挖掘、交易或破坏古墓葬及文物。"
    "如发现疑似文物或古墓葬痕迹，请保持现场，不要扰动，并联系当地文物主管部门。"
)

HERITAGE_FORBIDDEN_ITEMS = [
    "不提供古墓定位或位置推断。",
    "不判断古墓存在概率。",
    "不推测墓道、墓室、入口或地下结构。",
    "不提供寻找路线、挖掘建议或探测建议。",
    "不输出“这里可能有古墓”等明确结论。",
]

HERITAGE_BLOCKED_REPLY = (
    "本系统不能提供古墓定位、古墓概率判断、墓道/墓室/入口推测、寻找路线、"
    "挖掘建议或探测建议。\n\n"
    "可以协助整理为“山势地貌与文保风险记录”：记录可见山势地貌、异常地貌、"
    "人工痕迹、近期扰动和现场保护信息。\n\n"
    "本报告仅用于文物保护风险记录和环境信息整理。不得用于寻找、定位、挖掘、"
    "交易或破坏古墓葬及文物。如发现疑似文物或古墓葬痕迹，请保持现场，"
    "不要扰动，并联系当地文物主管部门。"
)

HERITAGE_REQUEST_FORBIDDEN_KEYWORDS = [
    "找古墓",
    "古墓在哪里",
    "哪里有古墓",
    "定位古墓",
    "古墓位置",
    "古墓概率",
    "墓道",
    "墓室",
    "入口在哪",
    "入口位置",
    "哪里能挖",
    "能不能挖",
    "怎么挖",
    "挖掘建议",
    "探测建议",
    "怎么探测",
    "寻找路线",
]

HERITAGE_ALLOWED_OBJECT_NAMES = {
    "mountain",
    "slope",
    "artificial_mound",
    "stone_object",
    "inscription",
    "surface_artifact",
    "recent_disturbance",
    "water",
    "road",
    "tree",
    "field",
    "farmland",
    "grassland",
    "building",
    "open_space",
    "path",
    "target",
}

LANDSCAPE_ALLOWED_OBJECT_NAMES = {
    "mountain",
    "slope",
    "water",
    "road",
    "building",
    "tree",
    "field",
    "farmland",
    "grassland",
    "pole",
    "bridge",
    "gate",
    "open_space",
    "path",
    "target",
}

HERITAGE_ONLY_OBJECT_NAMES = {
    "artificial_mound",
    "stone_object",
    "inscription",
    "surface_artifact",
    "recent_disturbance",
}

MIN_VISIBLE_OBJECT_CONFIDENCE = 0.35
MIN_UNKNOWN_POSITION_CONFIDENCE = 0.55
STRICT_OBJECT_MIN_CONFIDENCE = {
    "water": 0.75,
    "road": 0.70,
    "path": 0.70,
    "building": 0.75,
    "pole": 0.70,
    "bridge": 0.75,
    "gate": 0.70,
}

LANDSCAPE_OBJECT_CANONICAL = {
    "field": ("field", "田野/草地"),
    "farmland": ("field", "田野/草地"),
    "grassland": ("field", "田野/草地"),
    "open_space": ("field", "田野/草地"),
}

HERITAGE_FORBIDDEN_ANALYSIS_TERMS = [
    "tomb",
    "grave",
    "burial",
    "mausoleum",
    "probability",
    "entrance",
    "route",
    "dig",
    "excavate",
    "detect",
    "古墓",
    "墓葬",
    "墓道",
    "墓室",
    "入口",
    "概率",
    "路线",
    "挖",
    "探测",
]


def scene_label(scene_type: str | None) -> str:
    return SCENE_TYPE_LABELS.get(scene_type or "", scene_type or "未标注")


def normalize_scene_type(scene_type: str | None) -> str:
    value = (scene_type or "house_landscape").strip()
    if value not in SCENE_TYPE_LABELS:
        return "manual_target"
    return value


def is_heritage_scene(scene_type: str | None) -> bool:
    return normalize_scene_type(scene_type) == "heritage_risk"


def report_type_for_scene(scene_type: str | None) -> str:
    return "heritage_risk_record_report" if is_heritage_scene(scene_type) else "landscape_photo_report"


def required_sections_for_scene(scene_type: str | None) -> List[str]:
    if is_heritage_scene(scene_type):
        return [
            "结论",
            "拍照场景",
            "地貌要素",
            "人工痕迹",
            "文保风险等级",
            "不确定性说明",
            "禁止事项",
            "建议处理方式",
            "上报信息整理",
        ]
    return [
        "结论",
        "场景与目标",
        "图片识别结果",
        "用户校正信息",
        "罗盘与天星资料",
        "外局形势观察",
        "传统资料解释",
        "现代环境建议",
        "风险提醒",
    ]


def mock_analysis(scene_type: str | None, target_label: str | None = None) -> Dict[str, Any]:
    scene_type = normalize_scene_type(scene_type)
    if scene_type == "yinzhai_environment":
        objects = [
            {"name": "mountain", "label": "山体/高处", "position": "back-wall", "confidence": 0.66},
            {"name": "open_space", "label": "明堂/开阔地", "position": "center", "confidence": 0.62},
            {"name": "road", "label": "道路/小路", "position": "front-left", "confidence": 0.58},
            {"name": "tree", "label": "树木", "position": "side", "confidence": 0.55},
        ]
    elif scene_type == "tianxing_site":
        objects = [
            {"name": "target", "label": target_label or "现场目标", "position": "center", "confidence": 0.64},
            {"name": "mountain", "label": "远处山线/高处", "position": "back-wall", "confidence": 0.58},
            {"name": "road", "label": "道路/参照线", "position": "front", "confidence": 0.52},
        ]
    elif scene_type == "house_landscape":
        objects = [
            {"name": "building", "label": "建筑", "position": "center", "confidence": 0.7},
            {"name": "road", "label": "道路", "position": "front", "confidence": 0.62},
            {"name": "tree", "label": "树木", "position": "side", "confidence": 0.58},
            {"name": "pole", "label": "杆塔/立柱", "position": "side-wall", "confidence": 0.48},
        ]
    elif scene_type == "heritage_risk":
        objects = [
            {"name": "mountain", "label": "山势/坡面", "position": "background", "confidence": 0.58},
            {"name": "slope", "label": "坡地/地貌起伏", "position": "center", "confidence": 0.56},
            {"name": "artificial_mound", "label": "疑似人工堆土/封土样地貌", "position": "center", "confidence": 0.35},
            {"name": "stone_object", "label": "石构件/石刻样对象", "position": "side", "confidence": 0.32},
            {"name": "recent_disturbance", "label": "近期扰动痕迹", "position": "front", "confidence": 0.3},
        ]
    else:
        objects = [
            {"name": "target", "label": target_label or "手动目标", "position": "center", "confidence": 0.62},
            {"name": "open_space", "label": "周边开阔处", "position": "front", "confidence": 0.5},
        ]

    return {
        "scene_type": scene_type,
        "scene_label": scene_label(scene_type),
        "target_label": target_label,
        "objects": objects,
        "possible_issues": [],
        "need_user_confirm": True,
        "source": "mock",
        "note": "当前 LLM 图片识别能力尚未接入，已返回可校正的外局识别占位结果。",
        "boundary_note": HERITAGE_BOUNDARY_NOTE if scene_type == "heritage_risk" else BOUNDARY_NOTE,
    }


def summarize_objects(analysis: Dict[str, Any] | None) -> str:
    objects = (analysis or {}).get("objects") or []
    if not objects:
        return "暂无可用识别对象。"
    lines = []
    for obj in objects:
        conf = obj.get("confidence")
        conf_text = f"，置信度 {conf:.2f}" if isinstance(conf, (int, float)) else ""
        label = obj.get("label") or OBJECT_LABELS.get(obj.get("name"), obj.get("name") or "对象")
        lines.append(f"- {label}：{obj.get('position') or '未标注位置'}{conf_text}")
    return "\n".join(lines)


def summarize_correction(correction: Dict[str, Any] | None) -> str:
    if not correction:
        return "用户尚未提交校正信息。"
    bool_labels = [
        ("has_mountain", "可见山体/高处"),
        ("has_water", "可见水体"),
        ("has_road", "可见道路"),
        ("has_building", "可见建筑"),
        ("has_tree", "可见树木"),
        ("has_pole", "可见杆塔/立柱"),
        ("is_open_bright", "前方较开阔明亮"),
        ("has_pressure_object", "存在压迫性遮挡物"),
        ("has_artificial_mound", "存在人工堆土/封土样地貌"),
        ("has_stone_object", "存在石构件/石刻样对象"),
        ("has_inscription", "存在文字刻痕/铭文样痕迹"),
        ("has_surface_artifact", "存在地表遗物样对象"),
        ("has_recent_disturbance", "存在近期扰动痕迹"),
    ]
    parts = []
    for key, label in bool_labels:
        if key in correction:
            parts.append(f"- {label}：{'是' if correction.get(key) else '否'}")
    for key, label in [
        ("target_direction", "目标方向"),
        ("water_direction", "水体方向"),
        ("road_direction", "道路方向"),
        ("tianxing_mountain", "天星/二十四山校正"),
        ("heritage_risk_level", "文保风险等级"),
        ("protection_note", "现场保护/上报备注"),
    ]:
        if correction.get(key):
            parts.append(f"- {label}：{correction[key]}")
    if correction.get("note"):
        parts.append(f"- 补充说明：{correction['note']}")
    return "\n".join(parts) if parts else "用户未填写有效校正项。"


def infer_focus_points(analysis: Dict[str, Any] | None, correction: Dict[str, Any] | None) -> List[str]:
    correction = correction or {}
    points: List[str] = []
    if correction.get("has_pressure_object"):
        points.append("照片中或用户校正中存在压迫性遮挡物，应先确认其距离、尺度和是否影响采光通风。")
    if correction.get("has_road"):
        points.append("道路形态需要结合车流、人流、噪音与安全距离观察，不宜只凭照片下判断。")
    if correction.get("has_water"):
        points.append("水体资料应进一步记录方位、距离、水质、流向和现实安全边界。")
    if correction.get("has_mountain"):
        points.append("山体或高处只作为形势观察线索，需结合现场坡度、距离和周边建筑关系。")
    if correction.get("has_artificial_mound") or correction.get("has_stone_object"):
        points.append("存在人工堆土、石构件或类似痕迹时，只能作为文保风险记录线索，不得据此判断古墓位置或概率。")
    if correction.get("has_inscription") or correction.get("has_surface_artifact"):
        points.append("如发现文字刻痕、铭文样痕迹或地表遗物样对象，应保持现场原状，不捡拾、不移动、不清洗。")
    if correction.get("has_recent_disturbance"):
        points.append("近期扰动痕迹需要记录照片、时间和位置环境，必要时联系当地文物主管部门核实。")
    possible = (analysis or {}).get("possible_issues") or []
    for item in possible:
        text = item if isinstance(item, str) else item.get("text") if isinstance(item, dict) else None
        if text and text not in points:
            points.append(text)
    if not points:
        points.append("暂未发现明确外局问题，建议补充多角度照片、罗盘测点和现场备注后再分析。")
    return points


def summarize_heritage_elements(analysis: Dict[str, Any] | None, correction: Dict[str, Any] | None) -> str:
    correction = correction or {}
    parts = []
    objects = (analysis or {}).get("objects") or []
    labels = [obj.get("label") or OBJECT_LABELS.get(obj.get("name"), obj.get("name")) for obj in objects]
    if labels:
        parts.append("- 图片识别要素：" + "、".join(str(x) for x in labels if x))
    for key, label in [
        ("has_artificial_mound", "人工堆土/封土样地貌"),
        ("has_stone_object", "石构件/石刻样对象"),
        ("has_inscription", "文字刻痕/铭文样痕迹"),
        ("has_surface_artifact", "地表遗物样对象"),
        ("has_recent_disturbance", "近期扰动痕迹"),
    ]:
        if key in correction:
            parts.append(f"- {label}：{'有' if correction.get(key) else '未确认'}")
    risk_level = correction.get("heritage_risk_level") or "未评估"
    parts.append(f"- 用户标注文保风险等级：{risk_level}")
    if correction.get("protection_note"):
        parts.append(f"- 现场保护/上报备注：{correction['protection_note']}")
    return "\n".join(parts)


def heritage_mandatory_notice() -> str:
    forbidden = "\n".join(f"- {item}" for item in HERITAGE_FORBIDDEN_ITEMS)
    return f"""{HERITAGE_BOUNDARY_NOTE}

禁止事项：
{forbidden}

不确定信息必须标注“需要专业人员现场核实”。
"""


def _has_forbidden_heritage_term(value: Any) -> bool:
    text = str(value or "").lower()
    return any(term.lower() in text for term in HERITAGE_FORBIDDEN_ANALYSIS_TERMS)


def _object_confidence(obj: Dict[str, Any]) -> float | None:
    confidence = obj.get("confidence")
    if isinstance(confidence, (int, float)):
        return max(0.0, min(float(confidence), 1.0))
    return None


def clean_landscape_analysis(analysis: Dict[str, Any] | None, scene_type: str | None) -> Dict[str, Any]:
    """Remove low-confidence or scene-incompatible objects before showing them to users."""
    source = dict(analysis or {})
    objects = source.get("objects") if isinstance(source.get("objects"), list) else []
    kept: List[Dict[str, Any]] = []
    review_notes: List[str] = []

    for obj in objects[:30]:
        if not isinstance(obj, dict):
            continue
        name = str(obj.get("name") or "").strip()
        label = str(obj.get("label") or OBJECT_LABELS.get(name, name or "对象")).strip()
        position = str(obj.get("position") or "unknown").strip()
        confidence = _object_confidence(obj)

        if not name:
            continue
        if name in HERITAGE_ONLY_OBJECT_NAMES and not is_heritage_scene(scene_type):
            review_notes.append(f"{label} 属于文保风险核对项，当前场景未展示为普通外局对象。")
            continue
        if name not in LANDSCAPE_ALLOWED_OBJECT_NAMES:
            review_notes.append(f"{label} 不属于当前外局识别展示范围，已转为人工核对项。")
            continue
        strict_confidence = STRICT_OBJECT_MIN_CONFIDENCE.get(name)
        if strict_confidence is not None and (confidence is None or confidence < strict_confidence):
            shown = f"{confidence:.2f}" if confidence is not None else "未提供"
            review_notes.append(f"{label} 需要清楚可见才展示，当前置信度为 {shown}，请按照片人工核对。")
            continue
        if confidence is not None and confidence < MIN_VISIBLE_OBJECT_CONFIDENCE:
            review_notes.append(f"{label} 置信度较低（{confidence:.2f}），请按照片人工核对。")
            continue
        if position == "unknown" and confidence is not None and confidence < MIN_UNKNOWN_POSITION_CONFIDENCE:
            review_notes.append(f"{label} 位置不明确且置信度偏低（{confidence:.2f}），请按照片人工核对。")
            continue

        canonical_name, canonical_label = LANDSCAPE_OBJECT_CANONICAL.get(
            name,
            (name, label or OBJECT_LABELS.get(name, name)),
        )
        item: Dict[str, Any] = {
            "name": canonical_name,
            "label": canonical_label,
            "position": position or "unknown",
        }
        if confidence is not None:
            item["confidence"] = confidence
        existing_index = next((idx for idx, kept_item in enumerate(kept) if kept_item.get("name") == canonical_name), None)
        if existing_index is None:
            kept.append(item)
        else:
            existing = kept[existing_index]
            existing_confidence = existing.get("confidence")
            if confidence is not None and (not isinstance(existing_confidence, (int, float)) or confidence > existing_confidence):
                kept[existing_index] = item

    existing_issues = source.get("possible_issues") if isinstance(source.get("possible_issues"), list) else []
    possible_issues: List[Any] = list(existing_issues)
    for note in review_notes:
        if note not in possible_issues:
            possible_issues.append(note)

    source["objects"] = kept
    source["possible_issues"] = possible_issues
    if review_notes:
        source["filtered_object_count"] = len(review_notes)
    return source


def _safe_heritage_text(value: Any, max_len: int = 500) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or _has_forbidden_heritage_term(text):
        return None
    return text[:max_len]


def _safe_heritage_text_items(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    items: List[str] = []
    for item in values[:10]:
        text = item if isinstance(item, str) else item.get("text") if isinstance(item, dict) else None
        safe = _safe_heritage_text(text, max_len=180)
        if safe and safe not in items:
            items.append(safe)
    return items


def _safe_heritage_objects(objects: Any) -> List[Dict[str, Any]]:
    safe_objects: List[Dict[str, Any]] = []
    if not isinstance(objects, list):
        return safe_objects
    for obj in objects[:20]:
        if not isinstance(obj, dict):
            continue
        name = str(obj.get("name") or "target")
        label = str(obj.get("label") or OBJECT_LABELS.get(name, "需核实对象"))
        if _has_forbidden_heritage_term(name) or _has_forbidden_heritage_term(label):
            continue
        if name not in HERITAGE_ALLOWED_OBJECT_NAMES:
            name = "target"
            label = label if label and label != "None" else "需核实对象"
        item: Dict[str, Any] = {
            "name": name,
            "label": label,
            "position": obj.get("position") or "未标注位置",
        }
        confidence = obj.get("confidence")
        if isinstance(confidence, (int, float)):
            item["confidence"] = max(0, min(float(confidence), 1))
        safe_objects.append(item)
    return safe_objects


def sanitize_heritage_analysis(analysis: Dict[str, Any] | None) -> Dict[str, Any]:
    source = analysis or {}
    objects = _safe_heritage_objects(source.get("objects") if isinstance(source, dict) else None)
    if not objects:
        objects = mock_analysis(
            "heritage_risk",
            source.get("target_label") if isinstance(source, dict) else None,
        )["objects"]
    source_note = _safe_heritage_text(source.get("note")) if isinstance(source, dict) else None
    source_issues = _safe_heritage_text_items(source.get("possible_issues")) if isinstance(source, dict) else []
    default_issues = [
        "仅记录可见山势地貌、人工痕迹、近期扰动和文保风险线索。",
        "不输出古墓定位、概率判断、入口推测、寻找路线、挖掘或探测建议。",
        "疑似信息需要专业人员现场核实。",
    ]
    data: Dict[str, Any] = {
        "scene_type": "heritage_risk",
        "scene_label": scene_label("heritage_risk"),
        "target_label": source.get("target_label") if isinstance(source, dict) else None,
        "objects": objects,
        "need_user_confirm": True,
        "source": source.get("source") if isinstance(source, dict) else "mock",
        "note": (source_note + " " if source_note else "") + "已按文保风险记录边界净化识别结果，仅保留客观环境与人工痕迹字段。",
        "boundary_note": HERITAGE_BOUNDARY_NOTE,
        "possible_issues": source_issues + [item for item in default_issues if item not in source_issues],
        "heritage_safety": {
            "no_tomb_location": True,
            "no_probability": True,
            "no_entrance_or_structure_guess": True,
            "no_route_or_digging_advice": True,
            "required_note": HERITAGE_BOUNDARY_NOTE,
        },
    }
    if isinstance(source, dict) and source.get("vision_provider"):
        data["vision_provider"] = source.get("vision_provider")
    if isinstance(source, dict) and source.get("vision_model"):
        data["vision_model"] = source.get("vision_model")
    if isinstance(source, dict) and source.get("vision_empty_objects"):
        data["vision_empty_objects"] = True
    if isinstance(source, dict) and source.get("llm_error"):
        data["llm_error"] = source.get("llm_error")
    return data


def ensure_heritage_notice(markdown: str) -> str:
    required = [
        "本报告仅用于文物保护风险记录和环境信息整理。",
        "不得用于寻找、定位、挖掘、交易或破坏古墓葬及文物。",
        "请保持现场，不要扰动，并联系当地文物主管部门。",
    ]
    if all(item in markdown for item in required):
        return markdown
    return markdown.rstrip() + "\n\n### 文保边界与禁止事项\n" + heritage_mandatory_notice()


def has_forbidden_heritage_output(markdown: str) -> bool:
    text = markdown or ""
    forbidden_patterns = [
        "这里可能有古墓",
        "此处可能有古墓",
        "古墓概率",
        "古墓可能性",
        "墓道",
        "墓室",
        "入口位于",
        "入口在",
        "寻找路线",
        "探测建议",
        "建议探测",
        "可以探测",
        "建议挖掘",
        "可以挖掘",
        "适合挖掘",
        "哪里能挖",
        "定位古墓",
        "古墓位置",
    ]
    return any(pattern in text for pattern in forbidden_patterns)


def is_forbidden_heritage_request(text: str | None) -> bool:
    source = text or ""
    return any(keyword in source for keyword in HERITAGE_REQUEST_FORBIDDEN_KEYWORDS)


def heritage_fallback_markdown(
    *,
    house: Dict[str, Any] | None,
    record: Dict[str, Any],
    analysis: Dict[str, Any] | None,
    correction: Dict[str, Any] | None,
    references: List[Dict[str, Any]],
) -> str:
    scene = scene_label(record.get("scene_type"))
    house_name = (house or {}).get("name") or "未关联房屋"
    target = record.get("target_label") or "未标注"
    objects = summarize_objects(analysis)
    correction_text = summarize_correction(correction)
    heritage_elements = summarize_heritage_elements(analysis, correction)
    risk_level = (correction or {}).get("heritage_risk_level") or "未评估"
    protection_note = (correction or {}).get("protection_note") or "未填写"
    ref_titles = summarize_references(references)

    return f"""### 1. 结论
本报告基于「{house_name}」的现场照片、识别结果与用户校正信息生成，场景为 **{scene}**，目标为 **{target}**。本报告仅用于文物保护风险记录和环境信息整理，不用于寻找、定位、挖掘、交易或破坏古墓葬及文物。照片只能反映局部视角，所有不确定信息均需要专业人员现场核实。

### 2. 拍照场景
- 场景类型：{scene}
- 目标名称：{target}
- 图片路径：{record.get('image_path')}

### 3. 地貌要素
{objects}

### 4. 人工痕迹
{heritage_elements}

### 5. 文保风险等级
用户标注风险等级：**{risk_level}**。该等级仅为资料整理标签，不代表古墓或文物存在概率，不构成专业鉴定结论。

### 6. 不确定性说明
- 图片识别和人工校正只能记录可见地貌、石构件样对象、文字刻痕样痕迹、地表遗物样对象或近期扰动痕迹。
- 不输出古墓定位结论，不输出古墓概率，不推测墓道、墓室、入口或地下结构。
- 所有疑似信息均需要专业人员现场核实。

### 7. 禁止事项
{chr(10).join(f"- {item}" for item in HERITAGE_FORBIDDEN_ITEMS)}

### 8. 建议处理方式
- 如发现疑似文物或古墓葬痕迹，请保持现场，不要扰动，并联系当地文物主管部门。
- 不捡拾、不移动、不清洗疑似遗物，不进行挖掘、探测或交易。
- 可整理照片、拍摄时间、公开可描述的周边环境、可见扰动情况和保护备注，供主管部门或专业人员判断。

### 9. 上报信息整理
- 关联对象：{house_name}
- 拍照场景：{scene}
- 目标备注：{target}
- 文保风险等级：{risk_level}
- 现场保护/上报备注：{protection_note}
- 参考来源：{ref_titles}

### 文保边界与禁止事项
{heritage_mandatory_notice()}
"""


def summarize_references(references: Iterable[Dict[str, Any]]) -> str:
    refs = list(references or [])
    titles = sorted({ref.get("book_title") for ref in refs if ref.get("book_title")})
    return "、".join(titles) if titles else "暂无古籍引用来源"


def fallback_markdown(
    *,
    house: Dict[str, Any] | None,
    record: Dict[str, Any],
    analysis: Dict[str, Any] | None,
    correction: Dict[str, Any] | None,
    compass_records: List[Dict[str, Any]],
    tianxing: Dict[str, Any] | None,
    references: List[Dict[str, Any]],
) -> str:
    scene = scene_label(record.get("scene_type"))
    house_name = (house or {}).get("name") or "未关联房屋"
    target = record.get("target_label") or "未标注"
    objects = summarize_objects(analysis)
    correction_text = summarize_correction(correction)
    points = "\n".join(f"- {item}" for item in infer_focus_points(analysis, correction))
    ref_titles = summarize_references(references)
    compass_text = "\n".join(
        f"- {row.get('object_type') or '测点'}：{row.get('degree')}°，{row.get('direction_8')} / {row.get('direction_24')}"
        for row in compass_records[:8]
    ) or "暂无关联罗盘测点。"
    orientation_text = (
        f"- 图片目标角度：{record.get('degree')}°，{record.get('direction_8') or '未标注'} / {record.get('direction_24') or '未标注'}"
        if record.get("degree") is not None or record.get("direction_24")
        else "- 未填写图片目标角度或二十四山。"
    )
    mapping = (tianxing or {}).get("mapping") or tianxing or {}
    tianxing_text = (
        f"- 二十四山：{mapping.get('mountain_24')}\n"
        f"- 天星名：{mapping.get('tianxing')}\n"
        f"- 分组：{mapping.get('group')}\n"
        f"- 流派差异说明：{mapping.get('variant_note') or (tianxing or {}).get('method_note') or '未提供'}"
        if mapping
        else "暂无天星映射资料。"
    )

    return f"""### 1. 结论
本报告基于「{house_name}」的外局照片、识别结果与用户校正信息生成。场景为 **{scene}**，目标为 **{target}**。照片只能反映局部视角，本报告仅作传统文化研究和环境记录参考。

### 2. 场景与目标
- 场景类型：{scene}
- 目标名称：{target}
- 图片路径：{record.get('image_path')}

### 3. 图片识别结果
{objects}

### 4. 用户校正信息
{correction_text}

### 5. 罗盘与天星资料
{orientation_text}

关联罗盘测点：
{compass_text}

天星映射：
{tianxing_text}

### 6. 外局形势观察
{points}

### 7. 传统资料解释
本次可参考来源：{ref_titles}。引用必须来自系统提供的 references_json，不应虚构书名、章节或出处。

### 8. 现代环境建议
- 优先补充多角度照片，记录道路、水体、建筑、树木、杆塔等对象与目标的距离。
- 对住宅外局，应同步关注采光、通风、噪音、通行安全、排水和消防通道。
- 对阴宅或纪念空间资料，应遵守当地法律法规、地方习俗、家族沟通和专业人士意见。

### 9. 风险提醒
{BOUNDARY_NOTE} 本报告不构成建筑、消防、法律、医疗、投资或重大现实决策建议。
"""
