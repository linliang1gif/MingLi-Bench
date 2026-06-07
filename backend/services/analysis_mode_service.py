"""Analysis mode helpers shared by AI, reports and traditional tools."""

from __future__ import annotations

from typing import Any, Dict, Optional


SAFE_MODE = "safe"
RESEARCH_MODE = "research"
VALID_ANALYSIS_MODES = {SAFE_MODE, RESEARCH_MODE}


SAFE_MODE_RULES = (
    "当前为普通模式。必须使用温和、非绝对化表达，不得输出恐吓、强断、"
    "诱导消费内容；涉及医疗、法律、投资或重大现实决策时，只能给出"
    "风险提示并建议咨询持证专业人士。"
)

RESEARCH_MODE_RULES = (
    "当前为自用研究模式。可以整理传统断语、古籍说法、民间流派观点和"
    "强吉凶术语，但必须标注【传统断语】【古籍说法】【民俗资料】"
    "【流派观点】或【术语解释】等来源性质；必须说明不确定性、仅供"
    "自用研究、不作为现实决策依据；不得承诺结果，不得诱导现实执行，"
    "不得要求用户必须执行法事、化解、迁坟、改葬、改名或购买物品。"
)

SAFE_MODE_WARNING = (
    "普通模式：内容仅作传统文化参考，不构成医疗、法律、投资或重大决策建议。"
)

RESEARCH_MODE_WARNING = (
    "【自用研究模式提示】该内容可能包含传统断语、民俗资料或流派观点，"
    "仅供个人研究，不作为现实决策依据。涉及现实操作时，请结合当地"
    "法律法规、地方习俗、家族沟通与专业人士意见。"
)

RESEARCH_RISK_NOTE = (
    "该词在自用研究模式下作为传统术语或资料语境允许展示；仍需标注"
    "来源性质、说明不确定性，并明确不作为现实决策依据。"
)


MODULE_RULES: Dict[str, Dict[str, str]] = {
    "bazi": {
        RESEARCH_MODE: (
            "八字命理研究模式允许展示神煞、格局、刑冲合害等传统术语，"
            "但不得承诺生死、婚姻、财富或职业结果。"
        )
    },
    "fengshui": {
        RESEARCH_MODE: (
            "风水研究模式允许展示阳宅、玄空、八宅等传统吉凶术语，"
            "但不得说现实中必定发生灾祸或发财。"
        )
    },
    "yinzhai": {
        RESEARCH_MODE: (
            "阴宅研究模式仅用于资料整理和环境记录，可整理龙穴砂水向、"
            "迁改与民俗科仪资料，但不得要求现实执行或制造恐吓。"
        )
    },
    "tianxing": {
        RESEARCH_MODE: (
            "天星研究模式允许展示二十四山天星术语和流派观点，"
            "不得承诺官运、财运或后代结果。"
        )
    },
    "date_selection": {
        RESEARCH_MODE: (
            "择日研究模式允许展示传统宜忌、神煞、冲煞、黄黑道等资料，"
            "不得表达“不选此日必有灾”等绝对结论。"
        )
    },
    "naming": {
        RESEARCH_MODE: (
            "起名研究模式允许展示五格、数理、五行喜忌等传统说法，"
            "不得承诺改名改命、发财、升官或必旺。"
        )
    },
    "divination": {
        RESEARCH_MODE: (
            "测字灵签研究模式允许展示传统断语和签文解释，"
            "不得输出恐吓或现实必然结论。"
        )
    },
}


def validate_analysis_mode(mode: Optional[str]) -> str:
    """Return a normalized mode or raise ValueError for invalid input."""
    normalized = (mode or SAFE_MODE).strip().lower()
    if normalized not in VALID_ANALYSIS_MODES:
        raise ValueError("analysis_mode must be 'safe' or 'research'")
    return normalized


def normalize_mode_from_input(input_json: Any) -> str:
    """Read analysis_mode from common payload shapes, defaulting to safe."""
    if isinstance(input_json, dict):
        return validate_analysis_mode(input_json.get("analysis_mode"))
    return SAFE_MODE


def get_mode_prompt_rules(mode: Optional[str], module: Optional[str] = None) -> str:
    """Build prompt rules for the selected mode and module."""
    normalized = validate_analysis_mode(mode)
    base = SAFE_MODE_RULES if normalized == SAFE_MODE else RESEARCH_MODE_RULES
    extra = ""
    if module:
        extra = (MODULE_RULES.get(module) or {}).get(normalized, "")
    return "\n".join(part for part in (base, extra) if part)


def build_mode_warning(mode: Optional[str]) -> str:
    normalized = validate_analysis_mode(mode)
    return RESEARCH_MODE_WARNING if normalized == RESEARCH_MODE else SAFE_MODE_WARNING


def build_prompt_context(mode: Optional[str], module: Optional[str] = None) -> Dict[str, Any]:
    normalized = validate_analysis_mode(mode)
    return {
        "analysis_mode": normalized,
        "mode_label": "自用研究模式" if normalized == RESEARCH_MODE else "普通模式",
        "mode_rules": get_mode_prompt_rules(normalized, module),
        "mode_warning": build_mode_warning(normalized),
    }


def ensure_mode_warning(text: str, mode: Optional[str]) -> str:
    normalized = validate_analysis_mode(mode)
    if normalized != RESEARCH_MODE:
        return text or ""
    warning = build_mode_warning(normalized)
    source = text or ""
    if warning in source or "不作为现实决策依据" in source:
        return source
    return f"{source.rstrip()}\n\n---\n{warning}"


def apply_mode_to_risk_check(risk: Dict[str, Any], mode: Optional[str]) -> Dict[str, Any]:
    """Attach mode metadata to a risk scan result."""
    normalized = validate_analysis_mode(mode)
    result = dict(risk or {})
    safe_text = result.get("safe_text") or ""
    hits = []
    for hit in result.get("hits") or []:
        item = dict(hit)
        if normalized == RESEARCH_MODE:
            item["allowed_by_research_mode"] = True
            item["safety_note"] = RESEARCH_RISK_NOTE
        else:
            item["allowed_by_research_mode"] = False
            item["safety_note"] = "普通模式下应避免原样输出该类强断、恐吓或诱导表达。"
            term = str(item.get("term") or "")
            if term:
                safe_text = safe_text.replace(term, "需谨慎看待")
        hits.append(item)

    result["hits"] = hits
    result["safe_text"] = safe_text
    result["analysis_mode"] = normalized
    result["mode_label"] = "自用研究模式" if normalized == RESEARCH_MODE else "普通模式"
    result["mode_warning"] = build_mode_warning(normalized)
    if normalized == RESEARCH_MODE:
        result["passed"] = True
        result["allowed_by_research_mode"] = bool(hits)
        result["action"] = "allowed_with_research_warning" if hits else "pass"
    else:
        result["allowed_by_research_mode"] = False
        result["action"] = "flag_for_review" if hits else "pass"
    return result
