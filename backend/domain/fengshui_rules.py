"""阳宅基础报告的轻量规则与格式化辅助。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


MAIN_DOOR_TYPES = {"main_door", "大门", "门", "入户门", "front_door"}


def pick_main_door_record(records: Iterable[Dict[str, Any]]) -> Dict[str, Any] | None:
    rows = list(records)
    for row in rows:
        if str(row.get("object_type") or "").strip() in MAIN_DOOR_TYPES:
            return row
    return rows[0] if rows else None


def summarize_records(records: Iterable[Dict[str, Any]]) -> str:
    rows: List[Dict[str, Any]] = list(records)
    if not rows:
        return "暂无罗盘测点。"
    lines = []
    for row in rows:
        note = f"，备注：{row.get('note')}" if row.get("note") else ""
        lines.append(
            f"- {row.get('object_type') or '测点'}：{row.get('degree')}°，"
            f"{row.get('direction_8')} / {row.get('direction_24')}（{row.get('scene_type') or '未标注场景'}{note}）"
        )
    return "\n".join(lines)


def fallback_markdown(
    house: Dict[str, Any],
    records: List[Dict[str, Any]],
    references: List[Dict[str, Any]],
) -> str:
    main_door = pick_main_door_record(records)
    if house.get("main_door_degree") is not None:
        door = (
            f"{house.get('main_door_degree')}°，"
            f"{house.get('main_door_direction_8')} / {house.get('main_door_direction_24')}"
        )
    elif main_door:
        door = f"{main_door.get('degree')}°，{main_door.get('direction_8')} / {main_door.get('direction_24')}"
    else:
        door = "暂未记录"

    ref_titles = "、".join(sorted({r.get("book_title") for r in references if r.get("book_title")})) or "暂无古籍引用"
    records_block = summarize_records(records)
    return f"""### 1. 结论
本报告为「{house.get('name')}」的基础阳宅参考。当前资料以房屋档案、主门朝向和已保存罗盘测点为核心，适合作为自用排查清单。

### 2. 房屋基础信息
- 类型：{house.get('house_type') or '未填写'}
- 建成年份：{house.get('build_year') or '未填写'}
- 入住日期：{house.get('move_in_date') or '未填写'}
- 地址备注：{house.get('address_note') or '未填写'}
- 户型备注：{house.get('floorplan_note') or '未填写'}

### 3. 大门朝向
{door}

### 4. 已测点位
{records_block}

### 5. 当前主要问题
- 若主门朝向为空，应优先完成大门测点，并同步到房屋档案。
- 若测点数量较少，建议补充卧室、厨房、书桌、床头、窗户等关键点位。
- 若同一位置多次测量角度差异较大，需远离金属、电器或重新校准设备。

### 6. 优先调整建议
- 先处理现实居住体验：采光、通风、噪音、动线、安全和收纳。
- 大门、卧室、厨房三类点位优先记录，后续再细化到桌位、床位和窗向。
- 对不确定的传统判断保持保守，先用可验证的居住问题做调整。

### 7. 传统阳宅解释
本次引用来源：{ref_titles}。第一版只做传统文化解释，不作绝对吉凶判断。

### 8. 现代居住建议
结合建筑科学与日常使用，优先检查空气流通、自然光、潮湿、遮挡、动线冲突与安全隐患。

### 9. 风险提醒
阳宅报告仅作传统文化与空间观察参考，不应替代建筑、消防、医疗、法律或投资等专业意见。"""
