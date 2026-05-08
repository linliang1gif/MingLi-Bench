"""案例反馈 API —— 命理师审核标准案例的闭环接口。

端点：
- GET  /api/cases                      列出标准案例（含规则引擎分析结果）
- GET  /api/cases/{case_id}            获取单个案例详情
- POST /api/cases/{case_id}/feedback   提交反馈
- GET  /api/feedbacks                  列出所有反馈
- GET  /api/feedbacks/summary          反馈汇总统计
"""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.models import CaseFeedback
from ..db.session import get_db
from ..domain.bazi_case_loader import load_standard_cases
from ..services import chart_service

router = APIRouter(prefix="/api", tags=["cases-feedback"])


# ========================== Schemas ==========================


class FeedbackCreate(BaseModel):
    reviewer: str = Field(..., min_length=1, max_length=64)
    reviewer_role: str = Field(default="user", pattern="^(user|expert|master)$")
    strength_agree: Optional[str] = Field(None, pattern="^(agree|disagree|unsure)$")
    strength_suggestion: Optional[str] = None
    pattern_agree: Optional[str] = Field(None, pattern="^(agree|disagree|unsure)$")
    pattern_suggestion: Optional[str] = None
    useful_gods_agree: Optional[str] = Field(None, pattern="^(agree|disagree|unsure)$")
    useful_gods_note: Optional[str] = None
    overall_score: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    case_id: str
    reviewer: str
    reviewer_role: str
    strength_agree: Optional[str] = None
    strength_suggestion: Optional[str] = None
    pattern_agree: Optional[str] = None
    pattern_suggestion: Optional[str] = None
    useful_gods_agree: Optional[str] = None
    useful_gods_note: Optional[str] = None
    overall_score: Optional[int] = None
    comment: Optional[str] = None
    status: str
    created_at: str

    class Config:
        from_attributes = True


# ========================== 案例列表 ==========================


@router.get("/cases")
def list_cases(
    day_master: Optional[str] = Query(None),
    strength: Optional[str] = Query(None),
    pattern: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """列出标准案例，支持过滤和分页。"""
    cases = load_standard_cases()

    # 过滤
    if day_master:
        cases = [c for c in cases if c.get("expected", {}).get("day_master") == day_master]
    if strength:
        cases = [c for c in cases if c.get("expected", {}).get("primary_strength_level") == strength]
    if pattern:
        cases = [c for c in cases if c.get("expected", {}).get("primary_pattern") == pattern]
    if source:
        cases = [c for c in cases if c.get("source") == source]

    total = len(cases)
    start = (page - 1) * page_size
    end = start + page_size
    page_cases = cases[start:end]

    # 精简输出
    items = []
    for c in page_cases:
        exp = c.get("expected", {})
        items.append({
            "case_id": c.get("case_id"),
            "title": c.get("title"),
            "source": c.get("source"),
            "confidence": c.get("confidence"),
            "day_master": exp.get("day_master"),
            "primary_strength": exp.get("primary_strength_level"),
            "primary_pattern": exp.get("primary_pattern"),
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/cases/{case_id}")
def get_case_detail(case_id: str):
    """获取单个案例详情，包含规则引擎的实时分析结果。"""
    cases = load_standard_cases()
    case = next((c for c in cases if c.get("case_id") == case_id), None)
    if not case:
        raise HTTPException(404, f"案例 {case_id} 不存在")

    # 实时排盘 + 规则分析
    inp = case["input"]
    try:
        chart = chart_service.compute_chart(
            birth_date=inp["birth_date"],
            birth_time=inp["birth_time"],
            calendar_type=inp.get("calendar_type", "solar"),
            gender=inp.get("gender", "male"),
        )
    except Exception as e:
        chart = {"error": str(e)}

    ra = chart.get("rule_analysis", {})
    return {
        "case": case,
        "chart_pillars": chart.get("pillars"),
        "rule_analysis": {
            "strength": ra.get("strength"),
            "pattern": ra.get("pattern"),
            "useful_gods": ra.get("useful_gods"),
            "version": ra.get("version"),
        },
    }


# ========================== 反馈 CRUD ==========================


@router.post("/cases/{case_id}/feedback", response_model=FeedbackOut)
def submit_feedback(case_id: str, body: FeedbackCreate, db: Session = Depends(get_db)):
    """提交案例反馈。"""
    # 验证 case_id 存在
    cases = load_standard_cases()
    if not any(c.get("case_id") == case_id for c in cases):
        raise HTTPException(404, f"案例 {case_id} 不存在")

    fb = CaseFeedback(
        case_id=case_id,
        reviewer=body.reviewer,
        reviewer_role=body.reviewer_role,
        strength_agree=body.strength_agree,
        strength_suggestion=body.strength_suggestion,
        pattern_agree=body.pattern_agree,
        pattern_suggestion=body.pattern_suggestion,
        useful_gods_agree=body.useful_gods_agree,
        useful_gods_note=body.useful_gods_note,
        overall_score=body.overall_score,
        comment=body.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return FeedbackOut(
        id=fb.id,
        case_id=fb.case_id,
        reviewer=fb.reviewer,
        reviewer_role=fb.reviewer_role,
        strength_agree=fb.strength_agree,
        strength_suggestion=fb.strength_suggestion,
        pattern_agree=fb.pattern_agree,
        pattern_suggestion=fb.pattern_suggestion,
        useful_gods_agree=fb.useful_gods_agree,
        useful_gods_note=fb.useful_gods_note,
        overall_score=fb.overall_score,
        comment=fb.comment,
        status=fb.status,
        created_at=str(fb.created_at),
    )


@router.get("/feedbacks", response_model=List[FeedbackOut])
def list_feedbacks(
    case_id: Optional[str] = Query(None),
    reviewer: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """列出反馈记录。"""
    q = db.query(CaseFeedback)
    if case_id:
        q = q.filter(CaseFeedback.case_id == case_id)
    if reviewer:
        q = q.filter(CaseFeedback.reviewer == reviewer)
    if status:
        q = q.filter(CaseFeedback.status == status)
    rows = q.order_by(CaseFeedback.id.desc()).limit(200).all()
    return [
        FeedbackOut(
            id=r.id, case_id=r.case_id, reviewer=r.reviewer,
            reviewer_role=r.reviewer_role,
            strength_agree=r.strength_agree,
            strength_suggestion=r.strength_suggestion,
            pattern_agree=r.pattern_agree,
            pattern_suggestion=r.pattern_suggestion,
            useful_gods_agree=r.useful_gods_agree,
            useful_gods_note=r.useful_gods_note,
            overall_score=r.overall_score,
            comment=r.comment,
            status=r.status,
            created_at=str(r.created_at),
        )
        for r in rows
    ]


@router.get("/feedbacks/summary")
def feedback_summary(db: Session = Depends(get_db)):
    """反馈汇总统计。"""
    rows = db.query(CaseFeedback).all()
    total = len(rows)
    if total == 0:
        return {"total": 0, "message": "暂无反馈数据"}

    strength_agree = sum(1 for r in rows if r.strength_agree == "agree")
    strength_disagree = sum(1 for r in rows if r.strength_agree == "disagree")
    pattern_agree = sum(1 for r in rows if r.pattern_agree == "agree")
    pattern_disagree = sum(1 for r in rows if r.pattern_agree == "disagree")
    scores = [r.overall_score for r in rows if r.overall_score]
    avg_score = sum(scores) / len(scores) if scores else None

    # 按 case_id 统计需修正的案例
    disagree_cases = set()
    for r in rows:
        if r.strength_agree == "disagree" or r.pattern_agree == "disagree":
            disagree_cases.add(r.case_id)

    return {
        "total_feedbacks": total,
        "strength_agreement": {
            "agree": strength_agree,
            "disagree": strength_disagree,
            "rate": round(strength_agree / total * 100, 1) if total else 0,
        },
        "pattern_agreement": {
            "agree": pattern_agree,
            "disagree": pattern_disagree,
            "rate": round(pattern_agree / total * 100, 1) if total else 0,
        },
        "average_overall_score": round(avg_score, 2) if avg_score else None,
        "cases_needing_correction": sorted(disagree_cases),
        "cases_needing_correction_count": len(disagree_cases),
    }
