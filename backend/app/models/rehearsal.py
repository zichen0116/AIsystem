from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="topic")
    original_file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    converted_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 会话级状态：由页级状态汇总得出
    # topic: generating / partial / ready / failed
    # upload: processing / partial / ready / failed
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
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    scenes: Mapped[list["RehearsalScene"]] = relationship(
        "RehearsalScene",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="RehearsalScene.scene_order",
    )

    @property
    def ready_count(self) -> int:
        return sum(1 for scene in self.scenes or [] if scene.scene_status == "ready")

    @property
    def fallback_count(self) -> int:
        return sum(1 for scene in self.scenes or [] if scene.scene_status == "fallback")

    @property
    def skipped_count(self) -> int:
        return sum(
            1
            for scene in self.scenes or []
            if scene.scene_status == "skipped" or scene.is_skipped
        )

    @property
    def failed_count(self) -> int:
        return sum(1 for scene in self.scenes or [] if scene.scene_status == "failed")

    @property
    def playable_count(self) -> int:
        return self.ready_count + self.fallback_count


class RehearsalScene(Base):
    __tablename__ = "rehearsal_scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rehearsal_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # 页级状态：pending / generating / ready / failed / skipped / fallback
    scene_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    slide_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    original_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skip_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 页级 TTS 音频粗略摘要：pending / partial / ready / failed
    audio_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session: Mapped["RehearsalSession"] = relationship("RehearsalSession", back_populates="scenes")
