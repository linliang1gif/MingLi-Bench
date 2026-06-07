from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import Chart, ChatMessage, ChatSession, Subject
from ..db.session import SessionLocal, get_db
from ..domain import landscape_photo_rules
from ..services import (
    analysis_mode_service,
    chart_service,
    llm_service,
    prompt_service,
    risk_service,
    subject_service,
)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    subject_id: int
    session_id: Optional[int] = None
    message: str = Field(..., min_length=1)
    analysis_mode: str = "safe"


def _ensure_session(db: Session, subject_id: int, session_id: Optional[int]) -> ChatSession:
    if session_id is not None:
        sess = db.get(ChatSession, session_id)
        if sess and sess.subject_id == subject_id:
            return sess
    s = db.get(Subject, subject_id)
    if not s:
        raise HTTPException(status_code=404, detail="subject not found")
    sess = ChatSession(subject_id=subject_id, title=None)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _build_chart_for_subject(db: Session, subject: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """对话场景下永远现算一次完整命盘（含十神 / 大运 / 流年），
    避免使用 DB 缓存里的旧版精简结构导致 prompt 信息缺失。
    lunar_python 计算开销极小（毫秒级），值得每次重算以保证准确性。"""
    bazi = chart_service.compute_chart(
        birth_date=subject.get("birth_date"),
        birth_time=subject.get("birth_time"),
        calendar_type=subject.get("calendar_type") or "solar",
        longitude=subject.get("longitude"),
        gender=subject.get("gender"),
    )
    return bazi if bazi.get("available") else None


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    analysis_mode = analysis_mode_service.validate_analysis_mode(payload.analysis_mode)
    subject = subject_service.get_subject(db, payload.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="subject not found")

    session = _ensure_session(db, payload.subject_id, payload.session_id)
    chart = _build_chart_for_subject(db, subject)

    # 持久化用户消息
    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    if landscape_photo_rules.is_forbidden_heritage_request(payload.message):
        reply = prompt_service.append_mode_warning(
            landscape_photo_rules.HERITAGE_BLOCKED_REPLY,
            analysis_mode,
        )
        risk = risk_service.check_text(db, reply, analysis_mode=analysis_mode)
        reply = risk_service.final_text_for_mode(reply, risk)
        asst = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=reply,
            risk_check_result=json.dumps(risk, ensure_ascii=False),
        )
        db.add(asst)
        if not session.title:
            session.title = (payload.message or "对话").strip()[:32]
        db.commit()
        db.refresh(asst)
        db.refresh(session)
        return {
            "session_id": session.id,
            "session_title": session.title,
            "message_id": asst.id,
            "user_message_id": user_msg.id,
            "reply": reply,
            "provider": "policy",
            "model": None,
            "ok": True,
            "analysis_mode": analysis_mode,
            "risk_check_result": risk,
        }

    # 取最近若干条历史（最多 12 条），用于 LLM 多轮上下文
    recent: List[ChatMessage] = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()[-12:]
    )
    history = [{"role": m.role, "content": m.content} for m in recent]

    # 构建 prompt：第一条用户消息附带命盘上下文（含十神 / 大运 / 流年），避免每次重复堆叠
    ctx = prompt_service.build_subject_context(subject, chart)
    if not history or history[0]["role"] != "user" or "系统排盘结果" not in history[0]["content"]:
        ctx_block = prompt_service.render_subject_block(ctx)
        if history:
            history[0] = {"role": "user", "content": ctx_block + "\n" + history[0]["content"]}

    chat_template = prompt_service.get_db_template(db, "chat")
    chat_system_prompt = prompt_service.get_system_prompt(analysis_mode, module="bazi")
    if chat_template:
        rendered = prompt_service.render_db_template(
            chat_template,
            {"message": payload.message, "analysis_mode": analysis_mode},
        )
        chat_system_prompt = rendered["system_prompt"] or None

    llm = llm_service.chat_complete(
        system_prompt=chat_system_prompt,
        messages=history,
        max_tokens=4096,
        temperature=0.5,
    )

    if llm["ok"]:
        reply = prompt_service.append_mode_warning(llm["content"], analysis_mode)
    else:
        reply = prompt_service.append_mode_warning(
            prompt_service.append_disclaimer(
                "很抱歉，AI 暂时不可用（错误：{}）。请检查 .env 中的 API Key 后重试。".format(
                    llm.get("error") or "unknown"
                )
            ),
            analysis_mode,
        )

    risk = risk_service.check_text(db, reply, analysis_mode=analysis_mode)
    reply = risk_service.final_text_for_mode(reply, risk)
    asst = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply,
        risk_check_result=json.dumps(risk, ensure_ascii=False),
    )
    db.add(asst)

    if not session.title:
        session.title = (payload.message or "对话").strip()[:32]
    db.commit()
    db.refresh(asst)
    db.refresh(session)

    return {
        "session_id": session.id,
        "session_title": session.title,
        "message_id": asst.id,
        "user_message_id": user_msg.id,
        "reply": reply,
        "provider": llm.get("provider"),
        "model": llm.get("model"),
        "ok": llm["ok"],
        "analysis_mode": analysis_mode,
        "risk_check_result": risk,
    }


@router.get("/chat/sessions")
def list_sessions(
    subject_id: Optional[int] = None, db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    stmt = select(ChatSession).order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
    if subject_id is not None:
        stmt = stmt.where(ChatSession.subject_id == subject_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": s.id,
            "subject_id": s.subject_id,
            "title": s.title or "未命名对话",
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in rows
    ]


def _build_history_for_llm(history_msgs: List[ChatMessage], subject: Dict[str, Any], chart: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """把消息历史 + 命主上下文拼成 LLM 输入。"""
    history = [{"role": m.role, "content": m.content} for m in history_msgs]
    ctx = prompt_service.build_subject_context(subject, chart)
    if history and history[0]["role"] == "user" and "系统排盘结果" not in history[0]["content"]:
        ctx_block = prompt_service.render_subject_block(ctx)
        history[0] = {"role": "user", "content": ctx_block + "\n" + history[0]["content"]}
    return history


def _sse(event: str, data: Dict[str, Any]) -> bytes:
    """编码单个 SSE 事件。"""
    body = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")


def _maybe_update_title(session_id: int) -> Optional[str]:
    """如果会话仍是默认/截断标题，则用 LLM 生成更恰当的标题并落库。"""
    db = SessionLocal()
    try:
        sess = db.get(ChatSession, session_id)
        if not sess:
            return None
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        # 至少要有一问一答才总结
        n_user = sum(1 for m in msgs if m.role == "user")
        n_asst = sum(1 for m in msgs if m.role == "assistant")
        if n_user < 1 or n_asst < 1:
            return None

        # 已被人工/智能总结过（不再覆写）：标题既不为空且和首条用户消息截断不同 → 跳过
        first_user = next((m for m in msgs if m.role == "user"), None)
        truncated_default = (first_user.content if first_user else "")[:32]
        if sess.title and sess.title != truncated_default and not sess.title.startswith(truncated_default):
            return sess.title

        history = [{"role": m.role, "content": m.content} for m in msgs]
        new_title = llm_service.summarize_session_title(history)
        if new_title:
            sess.title = new_title
            db.commit()
            return new_title
        return None
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    """流式对话（SSE）。

    协议：以 `event: <name>` + `data: <json>` 形式逐行返回。
        meta   { session_id, provider, model, subject_id }
        delta  { content }
        done   { message_id, title, ok }
        title  { title }            # 后台总结完成后单独推送
        error  { error }
    """
    # 第一阶段：在请求线程内同步完成「鉴权 / 命主 / 会话 / 命盘 / 用户消息持久化」
    analysis_mode = analysis_mode_service.validate_analysis_mode(payload.analysis_mode)
    db = SessionLocal()
    try:
        subject = subject_service.get_subject(db, payload.subject_id)
        if not subject:
            db.close()
            raise HTTPException(status_code=404, detail="subject not found")

        session = _ensure_session(db, payload.subject_id, payload.session_id)
        chart = _build_chart_for_subject(db, subject)

        user_msg = ChatMessage(session_id=session.id, role="user", content=payload.message)
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        if not session.title:
            session.title = (payload.message or "对话").strip()[:32]
            db.commit()
            db.refresh(session)

        if landscape_photo_rules.is_forbidden_heritage_request(payload.message):
            session_id = session.id
            current_title = session.title
            user_message_id = user_msg.id
            blocked_reply = prompt_service.append_mode_warning(
                landscape_photo_rules.HERITAGE_BLOCKED_REPLY,
                analysis_mode,
            )
            risk = risk_service.check_text(db, blocked_reply, analysis_mode=analysis_mode)
            blocked_reply = risk_service.final_text_for_mode(blocked_reply, risk)
            asst = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=blocked_reply,
                risk_check_result=json.dumps(risk, ensure_ascii=False),
            )
            db.add(asst)
            db.commit()
            db.refresh(asst)
            message_id = asst.id
            db.close()

            def blocked_event_generator():
                yield _sse("meta", {
                    "session_id": session_id,
                    "subject_id": payload.subject_id,
                    "title": current_title,
                    "provider": "policy",
                    "model": None,
                    "analysis_mode": analysis_mode,
                })
                yield _sse("delta", {"content": blocked_reply})
                yield _sse("done", {
                    "message_id": message_id,
                    "user_message_id": user_message_id,
                    "ok": True,
                    "title": current_title,
                    "provider": "policy",
                    "model": None,
                    "content": blocked_reply,
                    "analysis_mode": analysis_mode,
                    "risk_check_result": risk,
                })

            return StreamingResponse(
                blocked_event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                },
            )

        recent: List[ChatMessage] = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id.asc())
            .all()[-12:]
        )
        llm_history = _build_history_for_llm(recent, subject, chart)
        chat_template = prompt_service.get_db_template(db, "chat")
        chat_system_prompt = prompt_service.get_system_prompt(analysis_mode, module="bazi")
        if chat_template:
            rendered = prompt_service.render_db_template(
                chat_template,
                {"message": payload.message, "analysis_mode": analysis_mode},
            )
            chat_system_prompt = rendered["system_prompt"] or None
        session_id = session.id
        current_title = session.title
    finally:
        db.close()

    def event_generator():
        # meta
        yield _sse("meta", {
            "session_id": session_id,
            "subject_id": payload.subject_id,
            "title": current_title,
            "analysis_mode": analysis_mode,
        })

        # 流式调用 LLM
        full_text = ""
        had_error: Optional[str] = None
        meta_provider, meta_model = None, None
        for piece in llm_service.chat_complete_stream(messages=llm_history,
                                                     system_prompt=chat_system_prompt,
                                                     max_tokens=4096,
                                                     temperature=0.5):
            ev = piece.get("event")
            if ev == "meta":
                meta_provider = piece.get("provider")
                meta_model = piece.get("model")
                yield _sse("meta", {
                    "session_id": session_id,
                    "provider": meta_provider,
                    "model": meta_model,
                    "analysis_mode": analysis_mode,
                })
            elif ev == "delta":
                content = piece.get("content") or ""
                full_text += content
                yield _sse("delta", {"content": content})
            elif ev == "error":
                had_error = piece.get("error")
                yield _sse("error", {"error": had_error})
                break
            elif ev == "done":
                break

        if had_error:
            # 写入降级文案，前端也已收到 error 事件
            fallback = prompt_service.append_mode_warning(
                prompt_service.append_disclaimer(
                    f"很抱歉，AI 暂时不可用（错误：{had_error}）。请稍后再试。"
                ),
                analysis_mode,
            )
            db2 = SessionLocal()
            try:
                risk = risk_service.check_text(db2, fallback, analysis_mode=analysis_mode)
                fallback = risk_service.final_text_for_mode(fallback, risk)
                asst = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=fallback,
                    risk_check_result=json.dumps(risk, ensure_ascii=False),
                )
                db2.add(asst)
                sess_obj = db2.get(ChatSession, session_id)
                if sess_obj:
                    sess_obj.updated_at = func.now()
                db2.commit(); db2.refresh(asst)
                yield _sse("done", {
                    "message_id": asst.id,
                    "ok": False,
                    "title": current_title,
                    "content": fallback,
                    "analysis_mode": analysis_mode,
                    "risk_check_result": risk,
                })
            finally:
                db2.close()
            return

        # 追加免责声明（作为最后一段 delta，便于前端原样累积）
        final_text = prompt_service.append_mode_warning(
            prompt_service.append_disclaimer(full_text),
            analysis_mode,
        )
        final_tail = final_text[len(full_text):] if final_text.startswith(full_text) else ""
        if final_tail:
            yield _sse("delta", {"content": final_tail})
        # 落库 + done
        db2 = SessionLocal()
        try:
            risk = risk_service.check_text(db2, final_text, analysis_mode=analysis_mode)
            final_text = risk_service.final_text_for_mode(final_text, risk)
            asst = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=final_text,
                risk_check_result=json.dumps(risk, ensure_ascii=False),
            )
            db2.add(asst)
            # 触发 session.updated_at 以确保最新对话排在前面
            sess_obj = db2.get(ChatSession, session_id)
            if sess_obj:
                sess_obj.updated_at = func.now()
            db2.commit()
            db2.refresh(asst)
            yield _sse("done", {
                "message_id": asst.id,
                "ok": True,
                "title": current_title,
                "provider": meta_provider,
                "model": meta_model,
                "content": final_text,
                "analysis_mode": analysis_mode,
                "risk_check_result": risk,
            })
        finally:
            db2.close()

        # 后台总结标题（同步阻塞，不影响前端 done 已经渲染完毕）
        new_title = _maybe_update_title(session_id)
        if new_title and new_title != current_title:
            yield _sse("title", {"title": new_title})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/chat/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    sess = db.get(ChatSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return {
        "id": sess.id,
        "subject_id": sess.subject_id,
        "title": sess.title,
        "created_at": sess.created_at.isoformat() if sess.created_at else None,
        "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "risk_check_result": json.loads(m.risk_check_result) if m.risk_check_result else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }
