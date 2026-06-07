"""ORM 模型 —— 命主、命盘、对话、报告。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
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
    risk_check_result: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class Report(Base):
    """生成的结构化分析报告。"""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    report_type: Mapped[str] = mapped_column(String(32), default="general")
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subject: Mapped["Subject"] = relationship(back_populates="reports")
    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="reports")
    versions: Mapped[List["ReportVersion"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportVersion.id"
    )


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


class KnowledgeCategory(Base):
    """易学传统文化知识类目。"""

    __tablename__ = "knowledge_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_code: Mapped[Optional[str]] = mapped_column(String(16))
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(8), default="P2")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KnowledgeBook(Base, TimestampMixin):
    """古籍书籍条目。"""

    __tablename__ = "knowledge_books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    alias: Mapped[Optional[str]] = mapped_column(String(128))
    category_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    author: Mapped[Optional[str]] = mapped_column(String(64))
    dynasty: Mapped[Optional[str]] = mapped_column(String(32))
    version: Mapped[Optional[str]] = mapped_column(String(64))
    source: Mapped[Optional[str]] = mapped_column(String(256))
    copyright_status: Mapped[Optional[str]] = mapped_column(String(64))
    reliability_level: Mapped[str] = mapped_column(String(8), default="C")
    risk_level: Mapped[str] = mapped_column(String(16), default="medium")
    description: Mapped[Optional[str]] = mapped_column(Text)

    chunks: Mapped[List["KnowledgeChunk"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="KnowledgeChunk.id"
    )


class KnowledgeChunk(Base):
    """古籍内容分片。"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter: Mapped[Optional[str]] = mapped_column(String(128))
    section: Mapped[Optional[str]] = mapped_column(String(128))
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text)
    applicable_modules: Mapped[Optional[str]] = mapped_column(Text)
    source_ref: Mapped[Optional[str]] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    book: Mapped["KnowledgeBook"] = relationship(back_populates="chunks")


class KnowledgeImportLog(Base):
    """古籍 JSON 导入日志。"""

    __tablename__ = "knowledge_import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512))
    folder_path: Mapped[Optional[str]] = mapped_column(String(512))
    duplicate_strategy: Mapped[str] = mapped_column(String(16), nullable=False)
    books_total: Mapped[int] = mapped_column(Integer, default=0)
    books_inserted: Mapped[int] = mapped_column(Integer, default=0)
    books_skipped: Mapped[int] = mapped_column(Integer, default=0)
    chunks_inserted: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="success")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PromptTemplate(Base, TimestampMixin):
    """可在前端管理的 Prompt 模板。"""

    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class RiskTerm(Base):
    """AI 输出风险词。"""

    __tablename__ = "risk_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    replacement_suggestion: Mapped[Optional[str]] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HouseProfile(Base, TimestampMixin):
    """房屋档案。"""

    __tablename__ = "house_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    address_note: Mapped[Optional[str]] = mapped_column(String(256))
    house_type: Mapped[Optional[str]] = mapped_column(String(64))
    build_year: Mapped[Optional[int]] = mapped_column(Integer)
    move_in_date: Mapped[Optional[str]] = mapped_column(String(16))
    main_door_degree: Mapped[Optional[float]] = mapped_column(Float)
    main_door_direction_8: Mapped[Optional[str]] = mapped_column(String(16))
    main_door_direction_24: Mapped[Optional[str]] = mapped_column(String(16))
    floorplan_note: Mapped[Optional[str]] = mapped_column(Text)

    compass_records: Mapped[List["CompassRecord"]] = relationship(
        back_populates="house", order_by="CompassRecord.id"
    )
    xuan_kong_records: Mapped[List["XuanKongRecord"]] = relationship(
        back_populates="house", order_by="XuanKongRecord.id"
    )
    photo_analysis_records: Mapped[List["PhotoAnalysisRecord"]] = relationship(
        back_populates="house", order_by="PhotoAnalysisRecord.id"
    )
    landscape_photo_records: Mapped[List["LandscapePhotoRecord"]] = relationship(
        back_populates="house", order_by="LandscapePhotoRecord.id"
    )
    yinzhai_study_records: Mapped[List["YinzhaiStudyRecord"]] = relationship(
        back_populates="house", order_by="YinzhaiStudyRecord.id"
    )
    tianxing_fengshui_records: Mapped[List["TianxingFengshuiRecord"]] = relationship(
        back_populates="house", order_by="TianxingFengshuiRecord.id"
    )
    reports: Mapped[List["Report"]] = relationship(back_populates="house")


class CompassRecord(Base):
    """罗盘测向记录。"""

    __tablename__ = "compass_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scene_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    degree: Mapped[float] = mapped_column(Float, nullable=False)
    direction_8: Mapped[str] = mapped_column(String(16), nullable=False)
    direction_24: Mapped[str] = mapped_column(String(16), nullable=False)
    stability_score: Mapped[Optional[float]] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="compass_records")


class XuanKongRecord(Base):
    """玄空飞星基础盘计算记录。"""

    __tablename__ = "xuan_kong_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    build_year: Mapped[int] = mapped_column(Integer, nullable=False)
    move_in_year: Mapped[Optional[int]] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    facing_degree: Mapped[float] = mapped_column(Float, nullable=False)
    facing_direction_24: Mapped[str] = mapped_column(String(16), nullable=False)
    sitting_direction_24: Mapped[str] = mapped_column(String(16), nullable=False)
    base_star_json: Mapped[str] = mapped_column(Text, nullable=False)
    annual_star_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="xuan_kong_records")


class PhotoAnalysisRecord(Base):
    """拍照风水图片识别记录。"""

    __tablename__ = "photo_analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    room_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    analysis_json: Mapped[Optional[str]] = mapped_column(Text)
    user_correction_json: Mapped[Optional[str]] = mapped_column(Text)
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="photo_analysis_records")


class LandscapePhotoRecord(Base):
    """外局拍照识别记录，覆盖阴宅环境、天星现场方向、房屋外局和手动目标。"""

    __tablename__ = "landscape_photo_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    scene_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_label: Mapped[Optional[str]] = mapped_column(String(128))
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    degree: Mapped[Optional[float]] = mapped_column(Float)
    direction_8: Mapped[Optional[str]] = mapped_column(String(16))
    direction_24: Mapped[Optional[str]] = mapped_column(String(16))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    location_note: Mapped[Optional[str]] = mapped_column(String(256))
    analysis_json: Mapped[Optional[str]] = mapped_column(Text)
    user_correction_json: Mapped[Optional[str]] = mapped_column(Text)
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="landscape_photo_records")


class YinzhaiStudyRecord(Base):
    """Yinzhai research note. Records data only; no burial or relocation advice."""

    __tablename__ = "yinzhai_study_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    site_type: Mapped[Optional[str]] = mapped_column(String(64))
    location_note: Mapped[Optional[str]] = mapped_column(String(256))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    mountain_degree: Mapped[Optional[float]] = mapped_column(Float)
    mountain_direction_24: Mapped[Optional[str]] = mapped_column(String(16))
    facing_degree: Mapped[Optional[float]] = mapped_column(Float)
    facing_direction_24: Mapped[Optional[str]] = mapped_column(String(16))
    dragon_json: Mapped[Optional[str]] = mapped_column(Text)
    cave_json: Mapped[Optional[str]] = mapped_column(Text)
    sand_json: Mapped[Optional[str]] = mapped_column(Text)
    water_json: Mapped[Optional[str]] = mapped_column(Text)
    direction_json: Mapped[Optional[str]] = mapped_column(Text)
    environment_json: Mapped[Optional[str]] = mapped_column(Text)
    research_note: Mapped[Optional[str]] = mapped_column(Text)
    result_json: Mapped[Optional[str]] = mapped_column(Text)
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="yinzhai_study_records")


class TianxingFengshuiRecord(Base):
    """Tianxing fengshui lookup/report record."""

    __tablename__ = "tianxing_fengshui_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    house_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("house_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query_type: Mapped[str] = mapped_column(String(32), default="mountain")
    degree: Mapped[Optional[float]] = mapped_column(Float)
    mountain_24: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    location_note: Mapped[Optional[str]] = mapped_column(String(256))
    tianxing_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[Optional[str]] = mapped_column(Text)
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    house: Mapped[Optional["HouseProfile"]] = relationship(back_populates="tianxing_fengshui_records")


class ReportVersion(Base):
    """报告版本快照。"""

    __tablename__ = "report_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[Optional[str]] = mapped_column(Text)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(32))
    model_used: Mapped[Optional[str]] = mapped_column(String(128))
    risk_check_result: Mapped[Optional[str]] = mapped_column(Text)
    references_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    report: Mapped["Report"] = relationship(back_populates="versions")


class DateSelectionRecord(Base):
    """择日记录。"""

    __tablename__ = "date_selection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    start_date: Mapped[str] = mapped_column(String(16), nullable=False)
    end_date: Mapped[str] = mapped_column(String(16), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(128))
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NamingRecord(Base):
    """起名记录。"""

    __tablename__ = "naming_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    naming_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DivinationRecord(Base):
    """测字灵签记录。"""

    __tablename__ = "divination_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    divination_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
