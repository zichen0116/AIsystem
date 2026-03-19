"""
PPT大纲模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PptOutline(Base):
    """
    PPT大纲版本表

    存储会话中的大纲版本，支持版本管理和审批流程
    """
    __tablename__ = "ppt_outlines"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ppt_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    image_urls: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="自动配图结果，格式: {page_index: image_url}"
    )
    outline_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="结构化大纲卡片真源数据"
    )
    template_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Docmee模板ID"
    )
    knowledge_library_ids: Mapped[list] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="关联的知识库ID列表"
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联关系
    session: Mapped["PptSession"] = relationship(
        "PptSession",
        back_populates="outlines",
        foreign_keys=[session_id]
    )
    results: Mapped[list["PptResult"]] = relationship(
        "PptResult",
        back_populates="outline",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PptOutline(id={self.id}, session_id={self.session_id}, version={self.version})>"
