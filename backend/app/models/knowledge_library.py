"""
知识库模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class KnowledgeLibrary(Base):
    """
    知识库表

    用户可创建多个知识库，每个知识库包含多个知识资产。
    管理员创建的系统库可标记为公开，供所有用户在对话中选用。
    """
    __tablename__ = "knowledge_libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False, server_default="[]")
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

    # 关联
    owner: Mapped["User"] = relationship("User", back_populates="knowledge_libraries")
    assets: Mapped[list["KnowledgeAsset"]] = relationship(
        "KnowledgeAsset",
        back_populates="library",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<KnowledgeLibrary(id={self.id}, name={self.name})>"
