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
    category_routes,
    chart_routes,
    chat_routes,
    compass_routes,
    date_selection_routes,
    divination_routes,
    feedback_routes,
    fengshui_photo_routes,
    fengshui_routes,
    health_routes,
    history_routes,
    house_routes,
    knowledge_import_routes,
    knowledge_routes,
    landscape_photo_routes,
    naming_routes,
    prompt_routes,
    report_routes,
    risk_routes,
    subject_routes,
    system_routes,
    tianxing_routes,
    xuankong_routes,
    yinzhai_routes,
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
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173",
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_routes.router)
    app.include_router(subject_routes.router)
    app.include_router(chart_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(report_routes.router)
    app.include_router(history_routes.router)
    app.include_router(feedback_routes.router)
    app.include_router(fengshui_routes.router)
    app.include_router(fengshui_photo_routes.router)
    app.include_router(landscape_photo_routes.router)
    app.include_router(category_routes.router)
    app.include_router(knowledge_routes.router)
    app.include_router(knowledge_import_routes.router)
    app.include_router(prompt_routes.router)
    app.include_router(risk_routes.router)
    app.include_router(house_routes.router)
    app.include_router(compass_routes.router)
    app.include_router(date_selection_routes.router)
    app.include_router(naming_routes.router)
    app.include_router(divination_routes.router)
    app.include_router(system_routes.router)
    app.include_router(xuankong_routes.router)
    app.include_router(yinzhai_routes.router)
    app.include_router(tianxing_routes.router)

    return app


app = create_app()
