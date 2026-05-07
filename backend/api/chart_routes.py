"""命盘只读接口（命盘的生成/查询主要由 /api/subjects/{id}/chart 提供）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter

from ..services import chart_service, llm_service

router = APIRouter(prefix="/api", tags=["chart"])


@router.get("/llm/status")
def llm_status() -> Dict[str, Any]:
    """前端可用此接口判断 AI 能否工作（不返回密钥）。"""
    return llm_service.get_active_provider_info()


@router.get("/chart/preview")
def chart_preview(
    birth_date: str,
    birth_time: str = "12:00",
    calendar_type: str = "solar",
    longitude: Optional[float] = None,
) -> Dict[str, Any]:
    """临时计算（不入库）。供「命主创建」表单实时预览。"""
    return chart_service.compute_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        calendar_type=calendar_type,
        longitude=longitude,
    )
