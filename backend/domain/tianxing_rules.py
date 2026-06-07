"""Tianxing fengshui lookup rules.

V1.4 provides a conservative research mapping for the 24 mountains. The names
follow a common Lai Wenjun / Cuiguanpian-style terminology set, while the API
explicitly marks that other compass lineages may use variant names.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .compass import MOUNTAINS_24, convert_degree


REPORT_BOUNDARY = (
    "天星风水功能仅用于传统文化研究、罗盘资料整理与古籍引用说明；"
    "不作墓地吉凶强断，不提供改葬、迁坟、法事化解或诱导消费建议。"
)

VARIANT_NOTE = (
    "二十四山天星名称在不同罗盘、师承与文献中存在差异。V1.4 采用一套常见研究映射，"
    "用于资料整理与检索，不作为唯一标准。"
)


_TIANXING_NAMES = {
    "壬": {"star": "天帝星", "aliases": ["天辅星", "阴灌星"], "group": "北方三山"},
    "子": {"star": "阳光星", "aliases": ["天圣星", "太阴星"], "group": "北方三山"},
    "癸": {"star": "天道星", "aliases": ["阴光星", "遥光星", "北道星"], "group": "北方三山"},
    "丑": {"star": "天厨星", "aliases": ["牵牛星", "牛金星"], "group": "东北三山"},
    "艮": {"star": "天市星", "aliases": ["阳枢星", "天枢星"], "group": "天星四贵"},
    "寅": {"star": "天棓星", "aliases": ["功曹星"], "group": "东北三山"},
    "甲": {"star": "天死星", "aliases": ["天怨星", "天统星", "阴机星"], "group": "东方三山"},
    "卯": {"star": "天命星", "aliases": ["阳衡星", "阿香星", "天理星"], "group": "东方三山"},
    "乙": {"star": "天官星", "aliases": ["骑马星", "驿马星"], "group": "东方三山"},
    "辰": {"star": "天罡星", "aliases": ["亢星"], "group": "东南三山"},
    "巽": {"star": "太乙星", "aliases": ["阳旋星"], "group": "天星四贵"},
    "巳": {"star": "天屏星", "aliases": ["明堂星", "天堂星", "赤蛇星"], "group": "东南三山"},
    "丙": {"star": "天微星", "aliases": ["天贵星", "太微星", "阴枢星"], "group": "六秀"},
    "午": {"star": "天马星", "aliases": ["阳灌星", "天广星", "炎精星"], "group": "南方三山"},
    "丁": {"star": "天柱星", "aliases": ["南极星", "寿星"], "group": "六秀"},
    "未": {"star": "天帝星", "aliases": ["太常星"], "group": "西南三山"},
    "坤": {"star": "天钱星", "aliases": ["阴玄星", "玄戈星", "老阴星"], "group": "西南三山"},
    "申": {"star": "天关星", "aliases": ["传送星", "天开星"], "group": "西南三山"},
    "庚": {"star": "天汉星", "aliases": ["阴衡星", "天潢星"], "group": "三吉"},
    "酉": {"star": "少微星", "aliases": ["阳豆星"], "group": "天星四贵"},
    "辛": {"star": "天乙星", "aliases": ["阴旋星"], "group": "六秀"},
    "戌": {"star": "天魁星", "aliases": ["类金星", "鼓盆星"], "group": "西北三山"},
    "乾": {"star": "天厩星", "aliases": ["阳机星", "亢阳星"], "group": "西北三山"},
    "亥": {"star": "天皇星", "aliases": ["紫微星", "天门星"], "group": "天星四贵"},
}

_ELEMENT_BY_MOUNTAIN = {
    "壬": "水", "子": "水", "癸": "水",
    "丑": "土", "艮": "土", "寅": "木",
    "甲": "木", "卯": "木", "乙": "木",
    "辰": "土", "巽": "木", "巳": "火",
    "丙": "火", "午": "火", "丁": "火",
    "未": "土", "坤": "土", "申": "金",
    "庚": "金", "酉": "金", "辛": "金",
    "戌": "土", "乾": "金", "亥": "水",
}

_TRIGRAM_BY_INDEX = (
    "坎", "坎", "艮", "艮", "艮", "震",
    "震", "震", "巽", "巽", "巽", "离",
    "离", "离", "坤", "坤", "坤", "兑",
    "兑", "兑", "乾", "乾", "乾", "坎",
)


def all_mappings() -> List[Dict[str, Any]]:
    rows = []
    for index, mountain in enumerate(MOUNTAINS_24):
        rows.append(lookup_by_mountain(mountain, index_hint=index))
    return rows


def lookup_by_mountain(mountain: str, *, index_hint: int | None = None) -> Dict[str, Any]:
    mountain = str(mountain or "").strip()
    if mountain not in MOUNTAINS_24:
        raise ValueError("mountain_24 must be one of the 24 mountains")
    index = index_hint if index_hint is not None else list(MOUNTAINS_24).index(mountain)
    data = _TIANXING_NAMES.get(mountain) or {}
    start_degree = (index * 15 - 7.5) % 360
    center_degree = index * 15
    end_degree = (index * 15 + 7.5) % 360
    return {
        "mountain_24": mountain,
        "index": index,
        "degree_range": {
            "start": round(start_degree, 2),
            "center": round(center_degree, 2),
            "end": round(end_degree, 2),
        },
        "tianxing": data.get("star") or "未标注",
        "aliases": data.get("aliases") or [],
        "group": data.get("group") or "基础山向",
        "element": _ELEMENT_BY_MOUNTAIN.get(mountain),
        "trigram": _TRIGRAM_BY_INDEX[index],
        "variant_note": VARIANT_NOTE,
        "boundary_note": REPORT_BOUNDARY,
    }


def lookup_by_degree(degree: float) -> Dict[str, Any]:
    converted = convert_degree(degree)
    data = lookup_by_mountain(str(converted["direction_24"]))
    data["degree"] = converted["degree"]
    data["direction_8"] = converted["direction_8"]
    return data


def build_query_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    degree = payload.get("degree")
    mountain = payload.get("mountain_24")
    if degree is not None:
        result = lookup_by_degree(float(degree))
    elif mountain:
        result = lookup_by_mountain(str(mountain))
    else:
        raise ValueError("degree or mountain_24 is required")
    return {
        "query_type": "degree" if degree is not None else "mountain",
        "input": {"degree": degree, "mountain_24": mountain},
        "mapping": result,
        "method_note": VARIANT_NOTE,
        "boundary_note": REPORT_BOUNDARY,
    }


def summarize_references(references: Iterable[Dict[str, Any]]) -> str:
    refs = list(references or [])
    titles = sorted({ref.get("book_title") for ref in refs if ref.get("book_title")})
    return "、".join(titles) if titles else "暂无古籍引用来源"


def fallback_markdown(
    *,
    result: Dict[str, Any],
    house: Dict[str, Any] | None,
    references: List[Dict[str, Any]],
    note: str | None = None,
) -> str:
    mapping = result.get("mapping") or {}
    house_name = (house or {}).get("name") or "未关联房屋"
    ref_titles = summarize_references(references)
    aliases = "、".join(mapping.get("aliases") or []) or "未记录"
    degree_range = mapping.get("degree_range") or {}
    return f"""### 1. 结论
本报告为「{house_name}」的天星风水资料查询说明。当前山向为 **{mapping.get('mountain_24')}**，V1.4 映射为 **{mapping.get('tianxing')}**，用于文化研究和报告引用，不作绝对吉凶判断。

### 2. 查询信息
- 二十四山：{mapping.get('mountain_24')}
- 八方：{mapping.get('direction_8') or '未按角度查询'}
- 输入角度：{mapping.get('degree', '未填写')}
- 山向角度范围：{degree_range.get('start')}° - {degree_range.get('end')}°，中心约 {degree_range.get('center')}°

### 3. 天星映射
- 天星名：{mapping.get('tianxing')}
- 别名：{aliases}
- 分组：{mapping.get('group')}
- 五行参考：{mapping.get('element') or '未标注'}
- 八卦宫位：{mapping.get('trigram') or '未标注'}

### 4. 古籍引用线索
本次可参考来源：{ref_titles}。引用必须来自系统提供的 references_json，不应虚构书名、章节或出处。

### 5. 研究说明
{VARIANT_NOTE}

### 6. 记录备注
{note or '未填写'}

### 7. 风险提醒
{REPORT_BOUNDARY} 本报告不构成建筑、法律、医疗、投资或重大人生决策建议。
"""
