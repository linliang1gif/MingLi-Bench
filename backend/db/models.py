"""ORM 模型 —— 命主、命盘、对话、报告。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Subject(Base, TimestampMixin):
    """命主档案。"""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(8))                # 男 / 女 / 其他
    birth_date: Mapped[Optional[str]] = mapped_column(String(16))           # YYYY-MM-DD
    birth_time: Mapped[Optional[str]] = mapped_column(String(8))            # HH:MM
    birth_place: Mapped[Optional[str]] = mapped_column(String(128))
    calendar_type: Mapped[str] = mapped_column(String(8), default="solar")  # solar / lunar
    longitude: Mapped[Optional[float]] = mapped_column(default=None)        # 出生地经度（°E），用于真太阳时近似
    focus_topics: Mapped[Optional[str]] = mapped_column(Text)               # JSON 字符串
    notes: Mapped[Optional[str]] = mapped_column(Text)

    charts: Mapped[List["Chart"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["ChatSession"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


class Chart(Base):
    """命盘（八字 / 五行 简析）。"""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bazi_json: Mapped[Optional[str]] = mapped_column(Text)
    wuxing_json: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subject: Mapped["Subject"] = relationship(back_populates="charts")


class ChatSession(Base, TimestampMixin):
    """对话会话（一个命主可有多条会话线）。"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(128))

    subject: Mapped["Subject"] = relationship(back_populates="sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """单条消息。role: user / assistant / system。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class Report(Base):
    """生成的结构化分析报告。"""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(32), default="general")
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subject: Mapped["Subject"] = relationship(back_populates="reports")


class CaseFeedback(Base, TimestampMixin):
    """命理师/用户对标准案例的反馈校正。

    用于打破"规则引擎自标注自评估"的闭环，引入外部专家意见。
    """

    __tablename__ = "case_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(64), nullable=False)          # 审核人姓名/标识
    reviewer_role: Mapped[str] = mapped_column(String(32), default="user")     # user / expert / master
    # 审核意见
    strength_agree: Mapped[Optional[str]] = mapped_column(String(8))           # agree / disagree / unsure
    strength_suggestion: Mapped[Optional[str]] = mapped_column(String(16))     # 建议的旺衰级别
    pattern_agree: Mapped[Optional[str]] = mapped_column(String(8))            # agree / disagree / unsure
    pattern_suggestion: Mapped[Optional[str]] = mapped_column(String(32))      # 建议的格局名
    useful_gods_agree: Mapped[Optional[str]] = mapped_column(String(8))        # agree / disagree / unsure
    useful_gods_note: Mapped[Optional[str]] = mapped_column(Text)              # 喜用神修正说明
    overall_score: Mapped[Optional[int]] = mapped_column(Integer)              # 整体评分 1-5
    comment: Mapped[Optional[str]] = mapped_column(Text)                       # 自由评论
    status: Mapped[str] = mapped_column(String(16), default="pending")         # pending / accepted / rejected
