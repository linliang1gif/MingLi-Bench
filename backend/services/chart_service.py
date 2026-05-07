"""八字 / 五行 排盘服务（基于 lunar_python，支持节气、立春、农历输入与真太阳时近似）。

实现要点：
- 接受 solar / lunar 两种历法输入；lunar 通过 Lunar.fromYmd 转换为 Solar
- 节气分月、立春分年由 lunar_python 内部正确处理
- 「真太阳时」使用 *经度修正*（中国标准时间相对 120°E 子午线）：
      调整分钟数 = (longitude - 120.0) * 4
  如未提供经度则按钟表时间使用（即 120°E 平太阳时）。
  本实现不含均时差（Equation of Time，约 ±15min），
  在 summary 中明确说明，避免误导用户。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from lunar_python import Lunar, Solar


# —— 五行映射（用于扩展计算包括地支藏干在内的强弱）
STEM_WUXING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
BRANCH_WUXING = {
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
    "申": "金", "酉": "金",
    "亥": "水", "子": "水",
}
WUXING_FIVE = ("木", "火", "土", "金", "水")


# ------------------------- 工具 -------------------------

def _parse_ymd(birth_date: str) -> Tuple[int, int, int]:
    y, m, d = [int(p) for p in birth_date.split("-")]
    return y, m, d


def _parse_hm(birth_time: Optional[str]) -> Tuple[int, int]:
    if not birth_time:
        return 12, 0
    parts = birth_time.split(":")
    h = int(parts[0])
    mi = int(parts[1]) if len(parts) > 1 else 0
    return h, mi


def _to_solar(
    *,
    birth_date: str,
    birth_time: Optional[str],
    calendar_type: str,
    longitude: Optional[float],
) -> Tuple[Solar, Dict[str, Any]]:
    """根据输入构造 Solar 对象，并返回元信息。"""
    y, m, d = _parse_ymd(birth_date)
    h, mi = _parse_hm(birth_time)

    info: Dict[str, Any] = {
        "input_calendar": calendar_type,
        "input_birth_date": birth_date,
        "input_birth_time": birth_time,
        "longitude": longitude,
        "true_solar_time_applied": False,
        "true_solar_time_offset_min": 0.0,
    }

    if calendar_type == "lunar":
        # 农历→公历
        lunar = Lunar.fromYmdHms(y, m, d, h, mi, 0)
        solar = lunar.getSolar()
    else:
        solar = Solar.fromYmdHms(y, m, d, h, mi, 0)

    # 真太阳时（仅经度修正）
    if longitude is not None:
        offset_min = (float(longitude) - 120.0) * 4.0
        if abs(offset_min) >= 0.5:
            dt = datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                          solar.getHour(), solar.getMinute(), solar.getSecond())
            dt = dt + timedelta(minutes=offset_min)
            solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
            info["true_solar_time_applied"] = True
            info["true_solar_time_offset_min"] = round(offset_min, 1)

    return solar, info


def _split_pillar(pillar: str) -> Tuple[Optional[str], Optional[str]]:
    if not pillar or len(pillar) < 2:
        return None, None
    return pillar[0], pillar[1]


def _gender_to_int(gender: Optional[str]) -> int:
    """lunar_python EightChar.getYun() 约定：1=男，0=女。缺失则按男处理。"""
    if not gender:
        return 1
    g = gender.strip().lower()
    return 0 if g in ("女", "female", "f", "w") else 1


def _enrich_chart(ec, gender: Optional[str], today: Optional[date] = None) -> Dict[str, Any]:
    """补全命理高阶字段：十神 / 藏干 / 纳音 / 地势 / 旬空 / 大运 / 流年。"""
    today = today or date.today()
    pillar_keys = (
        ("year",  "Year"),
        ("month", "Month"),
        ("day",   "Day"),
        ("hour",  "Time"),  # lunar_python 用 Time 表示时柱
    )

    shishen: Dict[str, Dict[str, Any]] = {}
    hidden:  Dict[str, List[str]]      = {}
    nayin:   Dict[str, str]            = {}
    dishi:   Dict[str, str]            = {}
    for k, M in pillar_keys:
        shishen[k] = {
            "gan": getattr(ec, f"get{M}ShiShenGan")() or "",
            "zhi_list": list(getattr(ec, f"get{M}ShiShenZhi")() or []),
        }
        hidden[k] = list(getattr(ec, f"get{M}HideGan")() or [])
        nayin[k]  = getattr(ec, f"get{M}NaYin")() or ""
        dishi[k]  = getattr(ec, f"get{M}DiShi")() or ""

    xunkong_str = ec.getDayXunKong() or ""
    xunkong = list(xunkong_str)

    # —— 大运
    yun = ec.getYun(_gender_to_int(gender))
    yun_start = {
        "years":  yun.getStartYear(),
        "months": yun.getStartMonth(),
        "days":   yun.getStartDay(),
    }

    cur_year = today.year
    dayun_list: List[Dict[str, Any]] = []
    current_idx = -1
    raw_dayun = yun.getDaYun(10) or []
    for dy in raw_dayun:
        gz = dy.getGanZhi() or ""
        if not gz:  # 第 0 柱「童限」未排干支，跳过
            continue
        sy = dy.getStartYear()
        ey = dy.getEndYear()
        item = {
            "ganzhi":     gz,
            "start_age":  dy.getStartAge(),
            "end_age":    dy.getEndAge(),
            "start_year": sy,
            "end_year":   ey,
            "current":    sy <= cur_year <= ey,
        }
        if item["current"]:
            current_idx = len(dayun_list)
        dayun_list.append(item)

    # —— 当前流年
    try:
        cur_solar = Solar.fromYmd(cur_year, today.month, today.day)
        cur_lunar = cur_solar.getLunar()
        liunian_gz = cur_lunar.getYearInGanZhi()
    except Exception:
        liunian_gz = ""

    return {
        "shishen":             shishen,
        "hidden_gan":          hidden,
        "nayin":               nayin,
        "dishi":               dishi,
        "xunkong":             xunkong,
        "yun_start":           yun_start,
        "dayun":               dayun_list,
        "current_dayun_index": current_idx,
        "liunian":             {"year": cur_year, "ganzhi": liunian_gz},
    }


# ------------------------- 公开接口 -------------------------

def compute_chart(
    *,
    birth_date: Optional[str],
    birth_time: Optional[str],
    calendar_type: str = "solar",
    longitude: Optional[float] = None,
    gender: Optional[str] = None,
) -> Dict[str, Any]:
    """根据出生信息计算四柱与五行分布。

    参数
    ----
    birth_date: ISO 公历或农历日期（YYYY-MM-DD）
    birth_time: HH:MM 钟表时间，若缺失则按 12:00 估算
    calendar_type: "solar" 或 "lunar"
    longitude: 出生地经度（°E），用于真太阳时近似；可选
    gender:    "男"/"女"，用于排大运（缺失则按男）

    返回
    ----
    {available, pillars, wuxing, summary, lunar, input,
     shishen, hidden_gan, nayin, dishi, xunkong, dayun,
     current_dayun_index, liunian, yun_start}
    """
    if not birth_date:
        return {"available": False, "reason": "missing birth_date"}

    try:
        solar, info = _to_solar(
            birth_date=birth_date,
            birth_time=birth_time,
            calendar_type=calendar_type or "solar",
            longitude=longitude,
        )
    except Exception as e:
        return {"available": False, "reason": f"invalid date: {e}"}

    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    year_p, month_p, day_p, hour_p = ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()
    yg, yz = _split_pillar(year_p)
    mg, mz = _split_pillar(month_p)
    dg, dz = _split_pillar(day_p)
    hg, hz = _split_pillar(hour_p)

    pillars = {
        "year":  {"stem": yg, "branch": yz, "label": "年柱"},
        "month": {"stem": mg, "branch": mz, "label": "月柱"},
        "day":   {"stem": dg, "branch": dz, "label": "日柱"},
        "hour":  {"stem": hg, "branch": hz, "label": "时柱"},
    }

    # —— 五行分布（天干 + 地支本气）
    chars = [c for c in [yg, yz, mg, mz, dg, dz, hg, hz] if c]
    counts = {w: 0 for w in WUXING_FIVE}
    for ch in chars:
        if ch in STEM_WUXING:
            counts[STEM_WUXING[ch]] += 1
        elif ch in BRANCH_WUXING:
            counts[BRANCH_WUXING[ch]] += 1
    total = sum(counts.values()) or 1
    distribution = {w: round(c / total, 3) for w, c in counts.items()}

    # —— 简析
    sorted_w = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    strongest = sorted_w[0][0]
    weakest = sorted_w[-1][0]
    day_master = dg or "—"
    summary_lines = [
        f"日主天干「{day_master}」，五行偏「{strongest}」，较弱者为「{weakest}」。",
    ]
    if info.get("true_solar_time_applied"):
        summary_lines.append(
            f"已按经度 {longitude}°E 做真太阳时近似（偏移 {info['true_solar_time_offset_min']:+} 分），未含均时差修正。"
        )
    else:
        summary_lines.append("未提供经度，按钟表时间（120°E 平太阳时）排盘。")
    summary = " ".join(summary_lines)

    # —— 农历日期回填
    lunar_str = "%s年%s%s%s" % (
        lunar.getYearInChinese(),
        lunar.getMonthInChinese(),
        "月",
        lunar.getDayInChinese(),
    )

    # —— 高阶字段（十神 / 藏干 / 纳音 / 地势 / 旬空 / 大运 / 流年）
    try:
        enriched = _enrich_chart(ec, gender)
    except Exception as e:  # 兜底：扩展字段失败不应导致基础排盘失败
        enriched = {"_enrich_error": f"{type(e).__name__}: {e}"}

    result = {
        "available": True,
        "pillars": pillars,
        "wuxing": {
            "counts": counts,
            "distribution": distribution,
            "day_master": day_master,
        },
        "summary": summary,
        "lunar": {
            "ymd": [lunar.getYear(), lunar.getMonth(), lunar.getDay()],
            "text": lunar_str,
            "year_in_gan_zhi": lunar.getYearInGanZhi(),
            "month_in_gan_zhi": lunar.getMonthInGanZhi(),
            "day_in_gan_zhi": lunar.getDayInGanZhi(),
        },
        "input": info,
    }
    result.update(enriched)
    return result
