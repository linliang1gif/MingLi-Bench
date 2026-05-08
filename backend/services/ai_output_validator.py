"""AI 输出后置校验器。

检测 AI 回复是否违反约束：
1. 禁止词（绝对化/恐吓）
2. 引用了不存在的大运干支
3. 错误的本命年
4. 自行修改四柱
5. 未在十神速查表中的十神关系
6. 健康/投资/法律上的绝对建议

初版只检测 + 日志，不自动重试。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ========================== 禁止词 ==========================

FORBIDDEN_PHRASES = [
    "必定", "注定", "一定发财", "一定离婚", "必有大灾",
    "活不过", "必死", "必然破产", "肯定暴富", "注定孤独",
    "必定发生", "一定会死", "必然离婚",
]

ABSOLUTE_PATTERNS = [
    r"必[定然](?:会|要|将|能)",
    r"一定(?:会|要|能|将)",
    r"注定(?:会|要|能|将)",
    r"肯定(?:会|要|能|将)",
]

MEDICAL_LEGAL_PATTERNS = [
    r"(?:确诊|诊断)(?:为|有|患)",
    r"建议(?:购买|投资|卖出).{0,10}(?:股票|基金|期货|比特币|虚拟货币)",
    r"(?:起诉|打官司|告他)(?:一定|必定|肯定)",
]


# ========================== 主函数 ==========================

def validate_bazi_ai_output(
    text: str,
    chart: Optional[Dict[str, Any]] = None,
    rule_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """校验 AI 输出，返回校验结果。

    返回
    ----
    {
        "passed": bool,
        "violations": [{"type": str, "detail": str, "severity": "error"|"warning"}],
        "suggested_action": "pass" | "warn" | "retry",
    }
    """
    violations: List[Dict[str, str]] = []

    if not text:
        return {"passed": True, "violations": [], "suggested_action": "pass"}

    # --- 1. 禁止词 ---
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            violations.append({
                "type": "forbidden_phrase",
                "detail": f"出现禁止词「{phrase}」",
                "severity": "error",
            })

    for pattern in ABSOLUTE_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            # 避免重复报告
            if not any(m in v["detail"] for v in violations):
                violations.append({
                    "type": "absolute_language",
                    "detail": f"出现绝对化表述「{m}」",
                    "severity": "warning",
                })

    for pattern in MEDICAL_LEGAL_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            violations.append({
                "type": "medical_legal_absolute",
                "detail": f"健康/法律/投资绝对建议「{m}」",
                "severity": "error",
            })

    # --- 2. 大运干支校验 ---
    if chart:
        dayun_list = chart.get("dayun") or []
        valid_gz = {d.get("ganzhi") for d in dayun_list if d.get("ganzhi")}
        # 查找 AI 文中出现的干支格式（两个汉字）
        gz_pattern = re.compile(
            r"(?:大运|运程|运势|行运).{0,20}?([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])"
        )
        mentioned = gz_pattern.findall(text)
        for gz in mentioned:
            if gz not in valid_gz:
                violations.append({
                    "type": "invalid_dayun",
                    "detail": f"引用了不存在的大运干支「{gz}」",
                    "severity": "error",
                })

    # --- 3. 本命年校验 ---
    if chart:
        shengxiao = chart.get("shengxiao") or ""
        if shengxiao:
            benming_pattern = re.compile(r"本命年.{0,10}?([\u4e00-\u9fa5])年")
            for match in benming_pattern.finditer(text):
                animal = match.group(1)
                # 生肖映射
                animals = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
                if animal in animals and animal != shengxiao:
                    violations.append({
                        "type": "wrong_benming",
                        "detail": f"本命年生肖应为{shengxiao}，AI 说成{animal}",
                        "severity": "error",
                    })

    # --- 4. 四柱校验 ---
    if chart:
        pillars = chart.get("pillars") or {}
        for pos in ("year", "month", "day", "hour"):
            cell = pillars.get(pos) or {}
            stem = cell.get("stem") or ""
            branch = cell.get("branch") or ""
            if stem and branch:
                gz = stem + branch
                pillar_label = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}.get(pos, pos)
                # 检查是否有"年柱 XX"但与实际不符
                ptn = re.compile(f"{pillar_label}.{{0,5}}?([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])")
                for m in ptn.finditer(text):
                    if m.group(1) != gz:
                        violations.append({
                            "type": "wrong_pillar",
                            "detail": f"AI 将{pillar_label}写为{m.group(1)}，实际应为{gz}",
                            "severity": "error",
                        })

    # --- 5. 十神校验（仅当出现明确归属语境时）---
    if chart:
        shishen_ref = chart.get("shishen_ref") or {}
        if shishen_ref:
            shishen_names = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]
            # 仅检测明确归属语境，避免假阳性：
            #   "癸为正财" / "癸是正财" / "癸=正财" / "癸属正财" / "癸对应正财" / "癸代表正财"
            attribution_words = "(?:为|是|属|对应|代表|→|=)"
            for gan, correct_ss in shishen_ref.items():
                clean_ss = correct_ss.replace("(日主)", "")
                for wrong_ss in shishen_names:
                    if wrong_ss == clean_ss:
                        continue
                    ptn = re.compile(f"{gan}\\s*{attribution_words}\\s*{wrong_ss}")
                    if ptn.search(text):
                        violations.append({
                            "type": "wrong_shishen",
                            "detail": f"AI 将{gan}标为{wrong_ss}，应为{clean_ss}",
                            "severity": "warning",
                        })
                        break

    # --- 汇总 ---
    has_error = any(v["severity"] == "error" for v in violations)
    has_warning = any(v["severity"] == "warning" for v in violations)

    if has_error:
        action = "retry"
    elif has_warning:
        action = "warn"
    else:
        action = "pass"

    passed = not has_error

    if violations:
        logger.warning(
            "ai_output_validation: %d violation(s) found — %s",
            len(violations),
            "; ".join(v["detail"] for v in violations[:5]),
        )

    return {
        "passed": passed,
        "violations": violations,
        "suggested_action": action,
    }
