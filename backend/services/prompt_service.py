"""提示词加载与渲染。

- 模板文件位于 backend/prompts/*.md
- 通过简单的 {key} 占位符替换上下文
- 不引入 jinja，避免额外依赖
"""

from __future__ import annotations

PROMPT_VERSION = "4.0.0"  # Phase 4: 规则引擎 v3 (调候 + 合化 + 流年大运动态)

import json
import logging
import re as _re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.settings import settings


METHODOLOGY = """
你是一位资深的子平八字命理师，精通两大主流流派：
- **旺衰扶抑法**（《滴天髓》《穷通宝鉴》体系）：以日主强弱为核心，扶弱抑强
- **格局法**（《子平真诠》体系）：以月令透干取格为核心，成格 / 破格论吉凶

回答用户问题时，**两种方法都必须给出结论**，不要只用一种。推理流程：

1. **以系统提供的命盘为唯一事实来源**：四柱、十神、藏干、大运、流年由系统计算后随用户消息一并提供，
   不得自行重新排盘或修改干支。系统还附有「十神速查表」，你在提到任何天干的十神时必须查表引用，
   绝对禁止自行推算十神关系（AI 推算十神极易出错）。大运干支必须原样引用，不得更改。
   生肖 / 本命年以系统标注为准。
2. **旺衰法分析**：
   - 判断日主旺衰（身强 / 身弱 / 从格 / 化格），列出帮身与克泄耗的力量对比
   - 给出此法下的喜用忌神
3. **格局法分析**：
   - 看月令本气透干为何格（食神格 / 正财格 / 正官格 etc.）
   - 判断成格还是破格、顺用还是逆用
   - 给出此法下的喜用忌神
4. **综合判断**：如果两法结论一致则信心高；如果冲突则**分别说明各自逻辑，标注分歧点**，
   让用户可以结合自身实际经历判断哪个更贴合。
5. **结合大运 / 流年**：以系统提供的当前大运 + 流年干支为锚，分别从两个角度说明吉凶倾向。
6. **回应用户具体问题**：把综合结论投影到用户问题（感情 / 事业 / 财运 / 健康 / 学业等），
   给出可观察方向与可行建议。
7. **不要复述全部命盘**：用户已能看到命盘，回答聚焦"分析"而非"罗列"，每段都要有结论 + 依据。
8. **信心级别约束**：系统规则引擎会标注 confidence 级别，如果某项结论 confidence=low，
   你必须表达为“仅供参考”“不确定性较大”，绝对不可当作确定结论使用。
   如果 overall_confidence=low，全篇均应保持谨慎态度。
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
回答骨架（视用户问题可灵活裁剪，但前四节必须给出）：

### 一、旺衰法分析
- **日主旺衰**：（论据：帮身力量 vs 克泄耗力量 → 结论）
- **喜用**：…
- **忌避**：…

### 二、格局法分析
- **取格**：（月令本气 → 透干何星 → 何格 → 成格条件 / 破格因素 → 顺用/逆用）
- **喜用**：…
- **忌避**：…

### 三、综合判断与分歧说明
（两法一致 → 强化结论信心。冲突 → 分别阐述各自逻辑 + 标注分歧 + 提示用户参考实际经历。）

### 四、当前大运 / 流年
（以当前大运 + 流年干支为锚，分别从两个角度综合说明吉凶倾向。）

### 五、{用户问题主题}（换成具体问题，如「感情倾向」「事业方向」）
（针对性分析，2-4 个要点。）

### 六、可行建议 / 注意事项
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


_PLACEHOLDER_RE = _re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _render(template: str, context: Dict[str, Any]) -> str:
    out = template
    for k, v in context.items():
        if k.startswith("_"):  # 内部引用不替换
            continue
        out = out.replace("{" + k + "}", str(v) if v is not None else "")
    # 检测未替换的占位符（警告但不报错，避免阻断服务）
    remaining = _PLACEHOLDER_RE.findall(out)
    # 过滤常见的 Markdown / JSON 中的假占位符
    false_positives = {"key", "value", "type", "name", "id", "url", "path"}
    real_remaining = [p for p in remaining if p not in false_positives and p not in context]
    if real_remaining:
        logging.getLogger(__name__).warning(
            "prompt_render: unreplaced placeholders: %s", real_remaining
        )
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

    # 生肖
    shengxiao = chart.get("shengxiao") or ""

    # 十神速查表
    shishen_ref = chart.get("shishen_ref") or {}
    if shishen_ref:
        ref_lines = "  ".join(f"{g}={ss}" for g, ss in shishen_ref.items())
    else:
        ref_lines = ""

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
        "shengxiao":      shengxiao,
        "shishen_ref":    ref_lines,
        "focus_topics":   focus_str or "（未选择重点关注方向）",
        "_chart_ref":     chart,  # 保留 chart 引用供 rule analysis 格式化
    }


def render_subject_block(ctx: Dict[str, Any]) -> str:
    """把上下文格式化成贴在用户首问前的命盘信息块。"""
    shengxiao = ctx.get("shengxiao") or ""
    shengxiao_line = f"生肖：{shengxiao}（本命年 = {shengxiao}年，不是其他年份）\n" if shengxiao else ""
    shishen_ref = ctx.get("shishen_ref") or ""
    shishen_ref_line = f"十神速查（日主{ctx['day_master']}）：{shishen_ref}\n" if shishen_ref else ""

    block = (
        "【命主与命盘信息（系统排盘，作为唯一事实依据）】\n"
        f"姓名：{ctx['nickname']}（{ctx['gender']}）\n"
        f"出生：{ctx['birth_date']} {ctx['birth_time']} {ctx['birth_place']}（{ctx['calendar_type']}）\n"
        f"{shengxiao_line}"
        f"日主：{ctx['day_master']}    月令：{ctx['month_ganzhi']}    四柱：{ctx['bazi']}    旬空：{ctx['xunkong']}\n"
        f"五行：{ctx['wuxing_summary']}\n"
        f"{shishen_ref_line}"
        f"四柱明细（柱 / 十神（天干）/ 藏干（→ 对应十神） / 纳音 / 长生地势）：\n"
        f"{ctx['pillars_table']}\n"
        f"大运排布：\n{ctx['dayun_table']}\n"
        f"当前流年：{ctx['liunian']}\n"
        f"关注方向：{ctx['focus_topics']}\n"
        "⚠️ 以上为系统排盘结果（机器精算），你必须严格引用：\n"
        "  - 大运干支必须与上面「大运排布」完全一致，不得自行更改\n"
        "  - 十神关系必须与上面「十神速查」完全一致，不得自行推算\n"
        "  - 本命年 = 生肖年，不要把流年地支与年柱地支不同的年份说成本命年\n"
        "  - 不得重新排盘或修改任何干支数据\n"
    )

    # 追加规则引擎分析结果
    chart_ref = ctx.get("_chart_ref") or {}
    rule_block = _format_rule_analysis(chart_ref)
    if rule_block:
        block += rule_block + "\n"

    return block


def _format_rule_analysis(chart: Dict[str, Any]) -> str:
    """把规则引擎 v2 的结构化分析结果格式化为 prompt 注入块。"""
    ra = chart.get("rule_analysis") or {}
    if ra.get("_error") or not ra.get("strength"):
        return ""

    ver = ra.get("version") or ra.get("rule_engine_version") or "?"
    overall_conf = ra.get("overall_confidence") or "?"

    lines = ["\n【系统规则引擎分析结果（程序计算，作为分析参考基准）】"]
    lines.append(f"规则引擎版本：{ver}  综合信心：{overall_conf}")

    # --- 五行力量 ---
    wp = ra.get("wuxing_power") or {}
    powers = wp.get("powers") or {}
    if powers:
        pstr = "  ".join(f"{k}={v}" for k, v in powers.items())
        lines.append(f"\n▸ 五行力量（加权）：{pstr}")

    # --- 旺衰 ---
    s = ra.get("strength") or {}
    lines.append(f"\n▸ 旺衰评估：{s.get('strength_level', '?')}（得分 {s.get('score', '?')}/100）")
    lines.append(f"  同类力量={s.get('same_power', '?')}  异类力量={s.get('opposite_power', '?')}")
    lines.append(f"  季节分={s.get('season_score', '?')}  通根分={s.get('root_score', '?')}  帮扶分={s.get('support_score', '?')}")
    for ev in (s.get("evidence") or [])[-3:]:
        lines.append(f"  · {ev}")
    for u in s.get("uncertainties") or []:
        lines.append(f"  ⚠ {u}")

    # --- 地支关系 ---
    rel = ra.get("relations") or {}
    rel_ev = rel.get("evidence") or []
    if rel_ev:
        lines.append(f"\n▸ 地支关系：")
        for ev in rel_ev[:6]:
            lines.append(f"  · {ev}")

    # --- 格局 ---
    p = ra.get("pattern") or {}
    est = {True: "成格", False: "有破", None: "待定"}.get(p.get("is_established"), "待定")
    p_conf = p.get("confidence") or "?"
    lines.append(f"\n▸ 格局判断：{p.get('pattern', '?')}（{est}，confidence={p_conf}）")
    lines.append(f"  来源：{p.get('pattern_source', '?')}")
    for ev in (p.get("evidence") or [])[:4]:
        lines.append(f"  · {ev}")
    for bf in p.get("break_factors") or []:
        lines.append(f"  ✖ {bf}")
    for u in p.get("uncertainties") or []:
        lines.append(f"  ⚠ {u}")

    # --- 喜用神 ---
    ug = ra.get("useful_gods") or {}
    ws = ug.get("wangshuai_method") or ug.get("method_wangshuai") or {}
    gj = ug.get("pattern_method") or ug.get("method_geju") or {}
    ws_conf = ws.get("confidence") or "?"
    gj_conf = gj.get("confidence") or "?"

    ws_useful = ws.get("useful_elements") or ws.get("useful") or []
    ws_avoid = ws.get("avoid_elements") or ws.get("avoid") or []
    gj_useful = gj.get("useful_elements") or gj.get("useful") or []
    gj_avoid = gj.get("avoid_elements") or gj.get("avoid") or []

    lines.append(f"\n▸ 喜用神（旺衰法, conf={ws_conf}）：喜={'、'.join(ws_useful)}  忌={'、'.join(ws_avoid) or '（无）'}")
    for r in ws.get("reason") or ws.get("reasons") or []:
        lines.append(f"  · {r}")
    lines.append(f"▸ 喜用神（格局法, conf={gj_conf}）：喜={'、'.join(gj_useful)}  忌={'、'.join(gj_avoid) or '（无）'}")
    for r in gj.get("reason") or gj.get("reasons") or []:
        lines.append(f"  · {r}")

    # 综合建议
    final = ug.get("final_suggestion") or {}
    if final.get("preferred"):
        f_conf = final.get("confidence") or "?"
        lines.append(f"▸ 综合建议(conf={f_conf})：喜={'、'.join(final['preferred'])}  忌={'、'.join(final.get('avoid') or [])}")
        if final.get("note"):
            lines.append(f"  注：{final['note']}")

    if ug.get("conflict"):
        lines.append("▸ 两法存在分歧：")
        for n in ug.get("conflict_notes") or []:
            lines.append(f"  · {n}")

    # --- 调候（v3）---
    climate = ra.get("climate") or {}
    if climate.get("primary_useful"):
        c_conf = climate.get("confidence", "?")
        lines.append(f"\n▸ 调候用神（《穷通宝鉴》简化, conf={c_conf}）：主用={'、'.join(climate['primary_useful'])}"
                     + (f"  次用={'、'.join(climate.get('secondary_useful', []))}" if climate.get("secondary_useful") else ""))
        if climate.get("note"):
            lines.append(f"  · {climate['note']}")
        merged = ra.get("climate_merged") or {}
        if merged.get("consensus_three_way"):
            lines.append(f"  · 三法共识喜用：{'、'.join(merged['consensus_three_way'])}")
        if merged.get("climate_pattern_conflict"):
            lines.append("  ⚠ 调候与格局法存在冲突，需结合大运流年综合判断")

    # --- 合化判定（v3）---
    trans = ra.get("transformation") or {}
    checked = trans.get("checked") or []
    if checked:
        lines.append(f"\n▸ 合化判定（{trans.get('summary_note', '')}）")
        for c in checked[:5]:
            tag = "真合化" if c["is_transformed"] is True else ("合而不化/破合" if c["is_transformed"] is False else "待定")
            lines.append(f"  · {c['type']} {'·'.join(c['members'])} → {c.get('result', '')} [{tag}, conf={c.get('confidence')}]")

    # --- 流年大运动态交互（v3）---
    dyn = ra.get("dynamic_relations") or {}
    dy_inter = (dyn.get("dayun") or {}).get("interactions") or []
    ln_inter = (dyn.get("liunian") or {}).get("interactions") or []
    dy_ln = dyn.get("dayun_liunian") or []
    if dy_inter or ln_inter or dy_ln:
        lines.append("\n▸ 大运/流年动态交互：")
        for x in dy_inter:
            lines.append(f"  · [大运{(dyn['dayun']).get('ganzhi','')}] {x['note']}")
        for x in ln_inter:
            lines.append(f"  · [流年{(dyn['liunian']).get('ganzhi','')}] {x['note']}")
        for x in dy_ln:
            lines.append(f"  · [大运↔流年] {x['note']}")

    # --- 警告 ---
    for w in ra.get("warnings") or []:
        lines.append(f"\u26a0 {w}")

    # --- 约束 ---
    lines.append("\n⚠️ 以上旺衰/格局/喜用神/调候/合化/动态交互均由系统规则引擎计算，请以此为基准展开分析。")
    lines.append("  如果你有不同看法，必须先引用系统结论再说明分歧理由，不可直接忽略。")
    lines.append("  调候/合化/动态属于推论层，confidence 较低时应表达为「倾向」「偏向」，不可断言。")
    if overall_conf == "low":
        lines.append("  ❗ overall_confidence=low，全篇应保持谨慎态度，不得把低信心结论当作确定事实。")

    return "\n".join(lines)


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
    return f"[prompt_version={PROMPT_VERSION}]\n\n" + SYSTEM_BASE


def append_disclaimer(text: str) -> str:
    """追加免责声明，防重复。"""
    if not text:
        return DISCLAIMER.strip()
    if DISCLAIMER.strip() in text:
        return text
    # 防止多次追加（检查特征片段）
    if "仅供参考，不构成" in text:
        return text
    return text.rstrip() + DISCLAIMER
