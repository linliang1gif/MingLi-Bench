"""标准案例加载器：加载、校验、按 ID 查找标准案例。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

CASES_FILE = Path(__file__).resolve().parent / "fixtures" / "bazi_cases" / "standard_cases.json"


# ========================== Schema 校验 ==========================

REQUIRED_TOP_FIELDS = ("case_id", "title", "input", "expected")
RECOMMENDED_TOP_FIELDS = ("source", "source_note", "confidence", "notes")
REQUIRED_INPUT_FIELDS = ("gender", "calendar_type", "birth_date", "birth_time")
REQUIRED_EXPECTED_FIELDS = ("pillars", "day_master")
REQUIRED_PILLAR_KEYS = ("year", "month", "day", "hour")


def validate_case_schema(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """校验单个案例字段。

    返回
    ----
    {"valid": bool, "errors": [str]}
    """
    errors: List[str] = []

    if not isinstance(case_data, dict):
        return {"valid": False, "errors": ["case_data 必须是 dict"]}

    # 顶层字段
    for f in REQUIRED_TOP_FIELDS:
        if f not in case_data:
            errors.append(f"缺少必要字段: {f}")

    # input 子字段
    inp = case_data.get("input") or {}
    if not isinstance(inp, dict):
        errors.append("input 必须是 dict")
    else:
        for f in REQUIRED_INPUT_FIELDS:
            if f not in inp:
                errors.append(f"input 缺少: {f}")
        cal = inp.get("calendar_type")
        if cal and cal not in ("solar", "lunar"):
            errors.append(f"input.calendar_type 必须是 solar/lunar，实际: {cal}")
        gender = inp.get("gender")
        if gender and gender not in ("male", "female", "男", "女"):
            errors.append(f"input.gender 必须是 male/female 或 男/女，实际: {gender}")

    # expected 子字段
    exp = case_data.get("expected") or {}
    if not isinstance(exp, dict):
        errors.append("expected 必须是 dict")
    else:
        for f in REQUIRED_EXPECTED_FIELDS:
            if f not in exp:
                errors.append(f"expected 缺少: {f}")
        # pillars
        pillars = exp.get("pillars") or {}
        if not isinstance(pillars, dict):
            errors.append("expected.pillars 必须是 dict")
        else:
            for k in REQUIRED_PILLAR_KEYS:
                if k not in pillars:
                    errors.append(f"expected.pillars 缺少: {k}")
                elif not isinstance(pillars[k], str) or len(pillars[k]) != 2:
                    errors.append(f"expected.pillars.{k} 必须是 2 字干支字符串，实际: {pillars[k]!r}")

        # 旧 schema 支持: expected.strength = {"accepted_levels": [...], "rejected_levels": [...]}
        strength = exp.get("strength")
        if strength is not None:
            if not isinstance(strength, dict):
                errors.append("expected.strength 必须是 dict")
            else:
                if "accepted_levels" in strength and not isinstance(strength["accepted_levels"], list):
                    errors.append("expected.strength.accepted_levels 必须是 list")
                if "rejected_levels" in strength and not isinstance(strength["rejected_levels"], list):
                    errors.append("expected.strength.rejected_levels 必须是 list")

        # 新 schema (v3.6): primary_strength_level / accepted_strength_levels / rejected_strength_levels 直接放在 expected
        for fld in ("accepted_strength_levels", "rejected_strength_levels",
                    "accepted_patterns", "rejected_patterns",
                    "accepted_useful_elements", "accepted_avoid_elements"):
            if fld in exp and not isinstance(exp[fld], list):
                errors.append(f"expected.{fld} 必须是 list")
        if "dispute_notes" in exp and not isinstance(exp["dispute_notes"], list):
            errors.append("expected.dispute_notes 必须是 list")

        # 旧 schema 兼容
        pattern = exp.get("pattern")
        if pattern is not None and not isinstance(pattern, dict):
            errors.append("expected.pattern 必须是 dict")
        ug = exp.get("useful_gods")
        if ug is not None and not isinstance(ug, dict):
            errors.append("expected.useful_gods 必须是 dict")

    return {"valid": len(errors) == 0, "errors": errors}


# ========================== 加载器 ==========================

@lru_cache(maxsize=1)
def load_standard_cases(strict: bool = False) -> List[Dict[str, Any]]:
    """加载标准案例文件。

    Args:
        strict: True 时遇到 schema 错误抛异常；False 时跳过非法案例并打印警告。
    """
    if not CASES_FILE.exists():
        return []

    raw = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{CASES_FILE} 必须是 JSON 数组")

    valid: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw):
        result = validate_case_schema(item)
        if not result["valid"]:
            msg = f"案例 #{idx} ({item.get('case_id', '?')}) schema 校验失败: {result['errors']}"
            if strict:
                raise ValueError(msg)
            import logging
            logging.getLogger(__name__).warning(msg)
            continue
        valid.append(item)

    return valid


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    """按 case_id 查找单个案例。"""
    for c in load_standard_cases():
        if c.get("case_id") == case_id:
            return c
    return None


def list_case_ids() -> List[str]:
    """列出所有案例 ID。"""
    return [c.get("case_id", "") for c in load_standard_cases()]


def reload_cases() -> List[Dict[str, Any]]:
    """清空缓存重新加载（测试用）。"""
    load_standard_cases.cache_clear()
    return load_standard_cases()
