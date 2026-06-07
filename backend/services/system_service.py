"""系统自检、数据库备份与测试样例读取。"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from ..core.version import APP_VERSION
from ..core.settings import settings
from ..db.models import KnowledgeCategory, PromptTemplate, Report, RiskTerm
from . import llm_service


TEST_CASES_PATH: Path = settings.project_root / "backend" / "data" / "test_cases.json"
CORE_TABLES = ("subjects", "reports", "risk_terms")


def _backup_files() -> Dict[str, Any]:
    storage_dir = settings.storage_dir.resolve()
    backups = sorted(
        (p for p in storage_dir.glob(f"{settings.sqlite_path.name}.bak-*") if p.is_file()),
        key=lambda p: p.name,
        reverse=True,
    )
    return {
        "count": len(backups),
        "latest": [p.name for p in backups[:10]],
    }


def _safe_count(db: Session, model: Any, issues: List[str], label: str) -> int:
    try:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)
    except Exception as exc:
        issues.append(f"{label} 统计失败：{type(exc).__name__}")
        return 0


def _latest_report_time(db: Session, issues: List[str]) -> str | None:
    try:
        latest = db.scalar(select(func.max(Report.created_at)))
        return latest.isoformat() if latest else None
    except Exception as exc:
        issues.append(f"最新报告时间读取失败：{type(exc).__name__}")
        return None


def check_system(db: Session) -> Dict[str, Any]:
    """返回可展示的系统自检结果。

    自检应尽量返回结构化 issues，而不是因为某张表或某个统计失败直接 500。
    """
    issues: List[str] = []
    db_path = settings.sqlite_path.resolve()

    try:
        table_names = set(inspect(db.bind).get_table_names()) if db.bind else set()
    except Exception as exc:
        table_names = set()
        issues.append(f"数据库表检查失败：{type(exc).__name__}")

    tables = {name: name in table_names for name in CORE_TABLES}
    for name, exists in tables.items():
        if not exists:
            issues.append(f"核心表缺失：{name}")

    database_exists = db_path.exists()
    if not database_exists:
        issues.append("数据库文件不存在")

    test_cases_exists = TEST_CASES_PATH.exists()
    if not test_cases_exists:
        issues.append("测试样例文件不存在")

    return {
        "version": APP_VERSION,
        "backend": {"ok": True},
        "llm": llm_service.get_active_provider_info(),
        "database": {
            "path": str(db_path),
            "exists": database_exists,
        },
        "backups": _backup_files(),
        "tables": tables,
        "counts": {
            "categories_count": _safe_count(db, KnowledgeCategory, issues, "知识类目"),
            "risk_terms_count": _safe_count(db, RiskTerm, issues, "风险词"),
            "prompt_templates_count": _safe_count(db, PromptTemplate, issues, "Prompt 模板"),
            "reports_count": _safe_count(db, Report, issues, "报告"),
        },
        "latest_report_time": _latest_report_time(db, issues),
        "test_cases": {"path": str(TEST_CASES_PATH.resolve()), "exists": test_cases_exists},
        "issues": issues,
    }


def backup_database() -> Dict[str, Any]:
    """备份 SQLite 数据库，目标严格限制在 backend/storage 下。"""
    storage_dir = settings.storage_dir.resolve()
    db_path = settings.sqlite_path.resolve()
    if not db_path.exists():
        raise FileNotFoundError("database file not found")
    if storage_dir not in db_path.parents:
        raise ValueError("database path escaped storage directory")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = (storage_dir / f"{db_path.name}.bak-{stamp}").resolve()
    if storage_dir not in backup_path.parents:
        raise ValueError("backup path escaped storage directory")

    shutil.copy2(db_path, backup_path)
    return {
        "ok": True,
        "backup_path": str(backup_path),
    }


def load_test_cases() -> Dict[str, Any]:
    if not TEST_CASES_PATH.exists():
        return {"cases": [], "issues": ["测试样例文件不存在"]}
    with TEST_CASES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"cases": data}
    if isinstance(data, dict):
        return data
    return {"cases": [], "issues": ["测试样例文件格式无效"]}
