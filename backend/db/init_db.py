"""建表入口：导入模型后调用 create_all 即可。

每次进程启动调用一次，幂等。包含轻量列迁移（add column if missing）。
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from . import models  # noqa: F401  保证模型被注册到 metadata
from .session import Base, engine


# 列迁移规则：表名 → [(列名, 列类型 SQL)]
_COLUMN_MIGRATIONS = {
    "subjects": [
        ("longitude", "REAL"),
    ],
    "chat_messages": [
        ("risk_check_result", "TEXT"),
    ],
    "reports": [
        ("house_id", "INTEGER"),
    ],
    "knowledge_books": [
        ("copyright_status", "TEXT"),
    ],
    "report_versions": [
        ("references_json", "TEXT"),
    ],
    "landscape_photo_records": [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("location_note", "TEXT"),
    ],
    "yinzhai_study_records": [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
    ],
    "tianxing_fengshui_records": [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("location_note", "TEXT"),
    ],
}


def _ensure_columns() -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in _COLUMN_MIGRATIONS.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, type_sql in cols:
                if name in existing:
                    continue
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {type_sql}'))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
