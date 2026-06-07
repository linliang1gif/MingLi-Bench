"""后端运行时设置 —— 明理 AI 助手。

约束：
- 路径必须基于 PROJECT_ROOT 自动解析，禁止硬编码绝对路径。
- 任何使用 .env 中变量的代码须通过此模块统一访问，绝不打印密钥原文。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple


def _detect_project_root() -> Path:
    """backend/core/settings.py → 项目根 = 上两级。"""
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT: Path = _detect_project_root()


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT

    # —— 持久化存储（SQLite）
    storage_dir: Path = PROJECT_ROOT / "backend" / "storage"
    sqlite_path: Path = PROJECT_ROOT / "backend" / "storage" / "mingli.db"
    prompts_dir: Path = PROJECT_ROOT / "backend" / "prompts"

    # —— LLM 默认偏好（按可用性自动挑选）
    default_provider_priority: Tuple[str, ...] = (
        "deepseek",
        "openrouter",
        "openai",
        "anthropic",
        "google",
    )
    default_models: dict = field(
        default_factory=lambda: {
            "deepseek": "deepseek-v4-pro",
            "openrouter": "deepseek/deepseek-chat-v3-0324",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet",
            "google": "gemini-1.5-pro",
        }
    )

    # 允许的前端来源
    cors_origins: tuple = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @property
    def database_url(self) -> str:
        # SQLAlchemy URL；正斜杠形式更安全
        return f"sqlite:///{self.sqlite_path.as_posix()}"

    @property
    def cors_origin_list(self) -> List[str]:
        extra = [
            item.strip()
            for item in os.getenv("CORS_ORIGINS", "").split(",")
            if item.strip()
        ]
        return list(dict.fromkeys([*self.cors_origins, *extra]))


settings = Settings()

# 确保 storage 目录存在（数据库文件会落在这里）
os.makedirs(settings.storage_dir, exist_ok=True)
