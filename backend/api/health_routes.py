from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from ..core.settings import settings
from ..services import llm_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    llm = llm_service.get_active_provider_info()
    return {
        "status": "ok",
        "service": "mingli-ai-backend",
        "stage": "C-MVP",
        "time": datetime.utcnow().isoformat() + "Z",
        "db_ready": settings.sqlite_path.exists(),
        "prompts_ready": settings.prompts_dir.exists(),
        "llm": llm,  # 仅 provider/model，不含密钥
    }
