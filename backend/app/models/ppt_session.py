"""
PPT会话模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PptSession(Base):
    """
    PPT会话表

    表示一次完整的PPT创作会话，包含多个消息、大纲版本和PPT结果版本
    """
    __tablename__ = "ppt_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="新建PPT"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft"
    )
    current_outline_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ppt_outlines.id", ondelete="SET NULL"),
        nullable=True
    )
    current_result_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ppt_results.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="ppt_sessions")
    messages: Mapped[list["PptMessage"]] = relationship(
        "PptMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PptMessage.created_at"
    )
    outlines: Mapped[list["PptOutline"]] = relationship(
        "PptOutline",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="PptOutline.session_id"
    )
    results: Mapped[list["PptResult"]] = relationship(
        "PptResult",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="PptResult.session_id"
    )

    def __repr__(self):
        return f"<PptSession(id={self.id}, title={self.title}, status={self.status})>"
