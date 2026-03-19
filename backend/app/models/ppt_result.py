"""
PPT结果模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PptResult(Base):
    """
    PPT结果版本表

    存储PPT生成结果，支持版本管理和编辑快照
    """
    __tablename__ = "ppt_results"

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
    outline_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ppt_outlines.id", ondelete="CASCADE"),
        nullable=False
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    template_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Docmee模板ID"
    )
    docmee_ppt_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Docmee返回的PPT ID"
    )
    source_pptx_property: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Docmee返回的原始预览数据"
    )
    edited_pptx_property: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="前端元素编辑后保存的最新快照"
    )
    file_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="PPT下载地址"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="generating",
        comment="generating / completed / failed"
    )
    current_page: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="当前已生成页数"
    )
    total_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="总页数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # 关联关系
    session: Mapped["PptSession"] = relationship(
        "PptSession",
        back_populates="results",
        foreign_keys=[session_id]
    )
    outline: Mapped["PptOutline"] = relationship(
        "PptOutline",
        back_populates="results"
    )

    def __repr__(self):
        return f"<PptResult(id={self.id}, session_id={self.session_id}, version={self.version}, status={self.status})>"
