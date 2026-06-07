from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..services import prompt_template_service

router = APIRouter(prefix="/api", tags=["prompts"])


class PromptTemplateIn(BaseModel):
    module: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)
    user_prompt_template: str = Field(..., min_length=1)
    output_schema: Optional[str] = None
    version: str = "1.0.0"
    enabled: bool = True


class PromptTemplateUpdate(BaseModel):
    module: Optional[str] = None
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    output_schema: Optional[str] = None
    version: Optional[str] = None
    enabled: Optional[bool] = None


class PromptTemplateTestIn(BaseModel):
    input_text: Optional[str] = None
    input_json: Optional[Any] = None
    analysis_mode: str = "safe"


@router.post("/prompts/init")
def init_prompts(db: Session = Depends(get_db)) -> Dict[str, int]:
    return prompt_template_service.init_templates(db)


@router.get("/prompts")
def list_prompts(module: Optional[str] = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return prompt_template_service.list_templates(db, module=module)


@router.post("/prompts")
def create_prompt(payload: PromptTemplateIn, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return prompt_template_service.create_template(db, payload.model_dump())


@router.put("/prompts/{template_id}")
def update_prompt(
    template_id: int, payload: PromptTemplateUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    row = prompt_template_service.update_template(
        db, template_id, payload.model_dump(exclude_unset=True)
    )
    if not row:
        raise HTTPException(status_code=404, detail="prompt template not found")
    return row


@router.post("/prompts/{template_id}/test")
def test_prompt(
    template_id: int,
    payload: PromptTemplateTestIn,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    row = prompt_template_service.test_template(db, template_id, payload.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail="prompt template not found")
    return row
