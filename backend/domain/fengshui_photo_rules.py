"""拍照风水识别的轻量规则与 fallback 文案。"""

from __future__ import annotations

from typing import Any, Dict, List


ROOM_TYPE_LABELS = {
    "bedroom": "卧室",
    "living_room": "客厅",
    "kitchen": "厨房",
    "entrance": "大门/玄关",
}

OBJECT_LABELS = {
    "bed": "床",
    "door": "门",
    "window": "窗",
    "mirror": "镜子",
    "beam": "横梁",
    "sofa": "沙发",
    "stove": "灶台",
    "desk": "书桌",
    "cabinet": "柜体",
}


def room_label(room_type: str | None) -> str:
    return ROOM_TYPE_LABELS.get(room_type or "", room_type or "未标注")


def mock_analysis(room_type: str | None) -> Dict[str, Any]:
    room_type = room_type or "bedroom"
    objects: List[Dict[str, Any]]
    if room_type == "kitchen":
        objects = [
            {"name": "stove", "label": "灶台", "position": "center", "confidence": 0.72},
            {"name": "window", "label": "窗", "position": "back-wall", "confidence": 0.64},
            {"name": "cabinet", "label": "柜体", "position": "side-wall", "confidence": 0.62},
        ]
    elif room_type == "living_room":
        objects = [
            {"name": "sofa", "label": "沙发", "position": "center-left", "confidence": 0.7},
            {"name": "window", "label": "窗", "position": "back-wall", "confidence": 0.66},
            {"name": "door", "label": "门", "position": "front-right", "confidence": 0.61},
        ]
    elif room_type == "entrance":
        objects = [
            {"name": "door", "label": "门", "position": "front", "confidence": 0.76},
            {"name": "cabinet", "label": "柜体", "position": "side-wall", "confidence": 0.58},
        ]
    else:
        objects = [
            {"name": "bed", "label": "床", "position": "center-left", "confidence": 0.74},
            {"name": "door", "label": "门", "position": "front-right", "confidence": 0.62},
            {"name": "window", "label": "窗", "position": "back-wall", "confidence": 0.6},
        ]

    return {
        "room_type": room_type,
        "objects": objects,
        "possible_issues": [],
        "need_user_confirm": True,
        "source": "mock",
        "note": "当前 LLM 图片识别能力尚未接入，已返回可校正的占位识别结果。",
    }


def summarize_objects(analysis: Dict[str, Any] | None) -> str:
    objects = (analysis or {}).get("objects") or []
    if not objects:
        return "暂无可用识别对象。"
    lines = []
    for obj in objects:
        conf = obj.get("confidence")
        conf_text = f"，置信度 {conf:.2f}" if isinstance(conf, (int, float)) else ""
        lines.append(
            f"- {obj.get('label') or OBJECT_LABELS.get(obj.get('name'), obj.get('name') or '对象')}："
            f"{obj.get('position') or '未标注位置'}{conf_text}"
        )
    return "\n".join(lines)


def summarize_correction(correction: Dict[str, Any] | None) -> str:
    if not correction:
        return "用户尚未提交校正信息。"
    bool_labels = [
        ("has_bed", "有床"),
        ("has_door", "有门"),
        ("has_window", "有窗"),
        ("has_mirror", "有镜子"),
        ("has_beam", "有横梁"),
    ]
    parts = []
    for key, label in bool_labels:
        if key in correction:
            parts.append(f"- {label}：{'是' if correction.get(key) else '否'}")
    if correction.get("bed_head_direction"):
        parts.append(f"- 床头方向：{correction['bed_head_direction']}")
    if correction.get("note"):
        parts.append(f"- 补充说明：{correction['note']}")
    return "\n".join(parts) if parts else "用户未填写有效校正项。"


def infer_issues(analysis: Dict[str, Any] | None, correction: Dict[str, Any] | None) -> List[str]:
    correction = correction or {}
    issues: List[str] = []
    if correction.get("has_mirror") and correction.get("has_bed"):
        issues.append("镜子与床同处一室时，建议确认镜面是否直对睡眠区。")
    if correction.get("has_beam") and correction.get("has_bed"):
        issues.append("横梁靠近床位时，建议确认是否压在床头或主要睡眠区域上方。")
    if correction.get("has_door") and correction.get("has_bed"):
        issues.append("床位与门的相对关系需要结合实际动线确认。")
    possible = (analysis or {}).get("possible_issues") or []
    for item in possible:
        text = item if isinstance(item, str) else item.get("text") if isinstance(item, dict) else None
        if text and text not in issues:
            issues.append(text)
    return issues


def fallback_markdown(
    *,
    house: Dict[str, Any] | None,
    analysis: Dict[str, Any] | None,
    correction: Dict[str, Any] | None,
    compass_records: List[Dict[str, Any]],
) -> str:
    room_type = room_label((analysis or {}).get("room_type") or (correction or {}).get("room_type"))
    objects = summarize_objects(analysis)
    correction_text = summarize_correction(correction)
    issues = infer_issues(analysis, correction)
    issues_text = "\n".join(f"- {item}" for item in issues) if issues else "- 暂未发现明确布局问题，建议结合现场动线继续观察。"
    compass_text = "\n".join(
        f"- {row.get('object_type') or '测点'}：{row.get('degree')}°，{row.get('direction_8')} / {row.get('direction_24')}"
        for row in compass_records[:8]
    ) or "暂无关联罗盘测点。"
    house_name = (house or {}).get("name") or "未关联房屋"

    return f"""### 1. 结论
本报告基于「{house_name}」的房间照片、AI 识别结果和用户校正信息生成。图片只能反映局部视角，建议以现场实际布局为准。

### 2. 房间类型
{room_type}

### 3. 图片识别结果
{objects}

### 4. 用户校正信息
{correction_text}

### 5. 结合罗盘的方位判断
{compass_text}

### 6. 主要布局问题
{issues_text}

### 7. 优先调整建议
- 先确认床、门、窗、镜子、横梁等关键对象的真实位置。
- 优先处理影响睡眠、通风、采光、潮湿、遮挡和动线的现实问题。
- 若需要做方位细分，应补充主门、床头、窗户等罗盘测点。

### 8. 传统阳宅解释
本版以图片可见信息和用户校正为基础，只做传统文化解释，不作绝对吉凶判断。

### 9. 现代居住环境建议
建议同步检查自然光、空气流通、噪音、收纳压力、消防通道和家具边角安全。

### 10. 风险提醒
拍照风水报告仅作传统文化与空间观察参考，不构成建筑、消防、医疗、法律、投资或重大决策建议。"""
