"""FastAPI 入口 —— 明理 AI 助手后端。

启动（项目根）：
    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

接口前缀：/api
约束：
- 不返回 / 不打印 真实 API Key。
- 命主与对话使用 SQLite 存储（backend/storage/mingli.db）。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    chart_routes,
    chat_routes,
    health_routes,
    history_routes,
    report_routes,
    subject_routes,
)
from .core.settings import settings
from .db.init_db import init_db


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def create_app() -> FastAPI:
    _configure_logging()
    init_db()

    app = FastAPI(
        title="MingLi AI Backend",
        description="明理 AI · 个人命理分析助手后端",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_routes.router)
    app.include_router(subject_routes.router)
    app.include_router(chart_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(report_routes.router)
    app.include_router(history_routes.router)

    return app


app = create_app()
