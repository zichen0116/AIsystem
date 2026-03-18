"""
PPT消息模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PptMessage(Base):
    """
    PPT会话消息表

    记录用户与系统在PPT会话中的消息
    """
    __tablename__ = "ppt_messages"

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
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user / assistant / system"
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="text",
        comment="text / outline / ppt_result / error / system"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=None,
        comment="附加元数据"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联关系
    session: Mapped["PptSession"] = relationship(
        "PptSession",
        back_populates="messages"
    )

    def __repr__(self):
        return f"<PptMessage(id={self.id}, role={self.role}, type={self.message_type})>"
