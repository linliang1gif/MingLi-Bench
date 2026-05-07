"""提示词加载与渲染。

- 模板文件位于 backend/prompts/*.md
- 通过简单的 {key} 占位符替换上下文
- 不引入 jinja，避免额外依赖
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.settings import settings


METHODOLOGY = """
你是一位资深的子平八字命理师，受过传统命理（《滴天髓》《子平真诠》《三命通会》体系）系统训练。
回答用户问题时，请**严格依照以下推理流程**，不要跳步、不要凭空想象：

1. **以系统提供的命盘为唯一事实来源**：四柱、十神、藏干、大运、流年由系统计算后随用户消息一并提供，
   不得自行重新排盘或修改干支；如系统给出 2026 年流年「丙午」，就以此为准，不要写成其他年份。
2. **先定旺衰格局**：根据日主天干 + 月令地势 + 整体五行结构判定身强 / 身弱 / 从格 / 化格，
   说明判断依据（如「日主戊土生酉月，金旺泄身，地支寅卯木克身，水多耗身，整体身弱」）。
3. **再立喜用忌神**：基于格局给出喜神、用神、忌神（每项 1-3 个五行 / 十神），简要解释逻辑。
4. **结合大运 / 流年**：以系统提供的当前大运 + 流年干支为锚，说明吉凶倾向；可前后展望 1-2 步运。
5. **回应用户具体问题**：把上述基础结论投影到用户问题（感情 / 事业 / 财运 / 健康 / 学业等），
   给出可观察方向与可行建议。
6. **不要复述全部命盘**：用户已能看到自己的命盘，回答聚焦"分析"而非"罗列"，每段都要有结论 + 依据。
""".strip()


SAFETY_RULES = """
输出规范（严格遵守）：
1. 不使用绝对化措辞（「必定」「一定」「注定」「必然」「肯定」），改用倾向性表达（「易于」「偏向」「有此象」）。
2. 不预言寿命、不诊断疾病、不预测彩票 / 股票具体投注；涉及健康 / 法律 / 财务话题，提示用户咨询持证专业人士。
3. 不进行恐吓 / 江湖化表述，不传播迷信式威胁。
4. 不构成医疗、法律、投资或人生重大决策的具体建议。
5. 输出使用 Markdown：以 `###` 三级标题分节、要点用列表、关键词用 `**加粗**`，便于阅读。
6. 命理术语首次出现时附简短白话解释（如「七杀（代表压力 / 挑战 / 突破）」），照顾普通用户理解。
7. 文末免责声明由系统自动追加，**你不要自己再写一遍免责声明**。
""".strip()


OUTPUT_TEMPLATE = """
建议的回答骨架（视用户问题而定，可灵活裁剪，但前三节通常必备）：

### 一、命局格局速判
（一段话点出日主旺衰、格局与整体气势。）

### 二、喜用忌神
- **喜用**：…
- **忌避**：…
（说明依据。）

### 三、当前大运 / 流年
（用系统给出的当前大运 + 流年，简述吉凶倾向。）

### 四、{用户问题主题}（这里换成具体问题，如「感情倾向」「事业方向」）
（针对性分析，2-4 个要点。）

### 五、可行建议 / 注意事项
- …
- …
""".strip()


SYSTEM_BASE = (
    METHODOLOGY
    + "\n\n"
    + SAFETY_RULES
    + "\n\n"
    + OUTPUT_TEMPLATE
)


DISCLAIMER = (
    "\n\n——\n以上内容基于传统命理体系与 AI 生成，仅供参考，"
    "不构成医学、法律、投资或人生重大决策建议。"
)


@lru_cache(maxsize=32)
def _load_template(name: str) -> str:
    path: Path = settings.prompts_dir / f"{name}.md"
    if not path.exists():
        return ""  # 缺模板时退化为空，由 SYSTEM_BASE 兜底
    return path.read_text(encoding="utf-8")


def _render(template: str, context: Dict[str, Any]) -> str:
    out = template
    for k, v in context.items():
        out = out.replace("{" + k + "}", str(v) if v is not None else "")
    return out


_PILLAR_LABELS = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}


def _format_pillars_table(chart: Dict[str, Any]) -> str:
    """把四柱 + 十神 + 藏干 + 纳音 + 地势拼成一段紧凑的多行命盘描述。"""
    pillars = chart.get("pillars") or {}
    shishen = chart.get("shishen") or {}
    hidden  = chart.get("hidden_gan") or {}
    nayin   = chart.get("nayin") or {}
    dishi   = chart.get("dishi") or {}

    lines = []
    for k in ("year", "month", "day", "hour"):
        cell = pillars.get(k) or {}
        stem = cell.get("stem") or ""
        branch = cell.get("branch") or ""
        if not (stem and branch):
            continue
        ss = shishen.get(k) or {}
        ss_gan = ss.get("gan") or ""
        ss_zhi = "/".join(ss.get("zhi_list") or []) or "—"
        if k == "day":
            # 日柱天干就是日主本身，不存在十神，标注「日主」
            ss_gan_label = "日主"
        else:
            ss_gan_label = ss_gan or "—"
        hg = "+".join(hidden.get(k) or []) or "—"
        ny = nayin.get(k) or ""
        ds = dishi.get(k) or ""
        lines.append(
            f"  - {_PILLAR_LABELS[k]} {stem}{branch}  "
            f"[{ss_gan_label} / 藏 {hg} → {ss_zhi}]  "
            f"纳音 {ny}  地势 {ds}"
        )
    return "\n".join(lines) if lines else "（命盘信息暂缺）"


def _format_dayun(chart: Dict[str, Any]) -> str:
    dayun = chart.get("dayun") or []
    cur_idx = chart.get("current_dayun_index", -1)
    if not dayun:
        return "（大运信息暂缺）"
    items = []
    for i, dy in enumerate(dayun[:8]):  # 取前 8 柱足够覆盖中年期
        marker = " ◀ 当前" if dy.get("current") else ""
        items.append(
            f"  - {dy['ganzhi']}：{dy['start_age']}–{dy['end_age']}岁  "
            f"({dy['start_year']}–{dy['end_year']}){marker}"
        )
    yun_start = chart.get("yun_start") or {}
    if yun_start:
        head = (
            f"  起运：约 {yun_start.get('years', 0)} 岁 "
            f"{yun_start.get('months', 0)} 月 {yun_start.get('days', 0)} 日"
        )
        items.insert(0, head)
    return "\n".join(items)


def build_subject_context(subject: Dict[str, Any], chart: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    chart = chart or {}
    pillars = chart.get("pillars") or {}

    # 四柱单行精简（用于头部一行展示）
    bazi_oneline = ""
    if pillars:
        parts = []
        for k in ("year", "month", "day", "hour"):
            cell = pillars.get(k) or {}
            if cell.get("stem") and cell.get("branch"):
                parts.append(f"{cell['stem']}{cell['branch']}")
        bazi_oneline = " ".join(parts)

    # 五行计数
    wuxing = chart.get("wuxing") or {}
    counts = wuxing.get("counts") or {}
    wuxing_str = "  ".join(f"{k}{v}" for k, v in counts.items()) if counts else ""
    day_master = wuxing.get("day_master") or "—"

    # 旬空
    xunkong = chart.get("xunkong") or []
    xunkong_str = "".join(xunkong) if xunkong else "—"

    # 流年
    liunian = chart.get("liunian") or {}
    liunian_str = (
        f"{liunian.get('year')} 年（{liunian.get('ganzhi') or '—'}）"
        if liunian else "—"
    )

    # 月令
    lunar = chart.get("lunar") or {}
    month_gz = lunar.get("month_in_gan_zhi") or "—"

    # 关注方向
    focus = subject.get("focus_topics")
    if isinstance(focus, list):
        focus_str = "、".join(focus)
    elif isinstance(focus, str):
        try:
            arr = json.loads(focus)
            focus_str = "、".join(arr) if isinstance(arr, list) else focus
        except Exception:
            focus_str = focus
    else:
        focus_str = ""

    return {
        "nickname":      subject.get("nickname") or "命主",
        "gender":        subject.get("gender") or "未知",
        "birth_date":    subject.get("birth_date") or "未知",
        "birth_time":    subject.get("birth_time") or "未知",
        "birth_place":   subject.get("birth_place") or "未知",
        "calendar_type": subject.get("calendar_type") or "solar",
        "day_master":    day_master,
        "month_ganzhi":  month_gz,
        "bazi":          bazi_oneline or "（命盘信息暂缺）",
        "pillars_table": _format_pillars_table(chart),
        "wuxing_summary": wuxing_str or "（五行信息暂缺）",
        "xunkong":        xunkong_str,
        "dayun_table":    _format_dayun(chart),
        "liunian":        liunian_str,
        "focus_topics":   focus_str or "（未选择重点关注方向）",
    }


def render_subject_block(ctx: Dict[str, Any]) -> str:
    """把上下文格式化成贴在用户首问前的命盘信息块。"""
    return (
        "【命主与命盘信息（系统排盘，作为唯一事实依据）】\n"
        f"姓名：{ctx['nickname']}（{ctx['gender']}）\n"
        f"出生：{ctx['birth_date']} {ctx['birth_time']} {ctx['birth_place']}（{ctx['calendar_type']}）\n"
        f"日主：{ctx['day_master']}    月令：{ctx['month_ganzhi']}    四柱：{ctx['bazi']}    旬空：{ctx['xunkong']}\n"
        f"五行：{ctx['wuxing_summary']}\n"
        f"四柱明细（柱 / 十神（天干）/ 藏干（→ 对应十神） / 纳音 / 长生地势）：\n"
        f"{ctx['pillars_table']}\n"
        f"大运排布：\n{ctx['dayun_table']}\n"
        f"当前流年：{ctx['liunian']}\n"
        f"关注方向：{ctx['focus_topics']}\n"
        "—— 以上为系统排盘结果，请直接使用，不要重新计算或修改。\n"
    )


def render_user_prompt(template_name: str, context: Dict[str, Any]) -> str:
    """把上下文塞进模板。模板缺失时使用 minimal fallback。"""
    tpl = _load_template(template_name)
    if not tpl:
        # fallback 简化版
        tpl = (
            "命主：{nickname}，性别：{gender}，出生：{birth_date} {birth_time} {birth_place}\n"
            "八字：{bazi}\n五行分布：{wuxing_summary}\n关注方向：{focus_topics}\n\n"
            "用户问题：{question}\n\n请按命理视角分析。"
        )
    return _render(tpl, context)


def get_system_prompt() -> str:
    return SYSTEM_BASE


def append_disclaimer(text: str) -> str:
    if DISCLAIMER.strip() in text:
        return text
    return (text or "").rstrip() + DISCLAIMER
