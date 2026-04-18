from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RehearsalSession(Base):
    __tablename__ = "rehearsal_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="未命名预演")
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    # 会话级状态：由页级状态汇总得出
    # generating: 有页面正在生成中
    # partial: 部分页面 ready，部分 failed，无 generating/pending
    # ready: 所有页面 ready
    # failed: 所有页面 failed 或无页面
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    total_scenes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    playback_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-CN")
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    scenes: Mapped[list["RehearsalScene"]] = relationship(
        "RehearsalScene", back_populates="session", cascade="all, delete-orphan",
        order_by="RehearsalScene.scene_order"
    )


class RehearsalScene(Base):
    __tablename__ = "rehearsal_scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rehearsal_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # 页级状态：pending → generating → ready / failed
    scene_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    slide_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # 页级 TTS 音频粗略摘要：pending / partial / ready / failed
    audio_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session: Mapped["RehearsalSession"] = relationship("RehearsalSession", back_populates="scenes")
