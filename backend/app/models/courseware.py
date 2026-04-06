"""
课件模型（核心表）
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, BigInteger, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Courseware(Base):
    """
    课件表（核心表）

    content_json 字段存储 AI 生成的结构化教学内容（Master Lesson JSON），包括：
    - slides: 幻灯片数组，每项含标题、正文、生图提示词
    - lesson_plan_details: 教案细节
    - interactive_elements: 互动题/小游戏逻辑
    """
    __tablename__ = "courseware"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PPT"
    )
    content_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PLANNING"
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # pdf/ppt/word/video/image
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user: Mapped["User"] = relationship("User", back_populates="coursewares")

    # ⚠️ 单向FK，PPTProject不维护反向关系
    ppt_project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="SET NULL"),
        nullable=True, unique=True
    )

    def __repr__(self):
        return f"<Courseware(id={self.id}, title={self.title}, status={self.status})>"
