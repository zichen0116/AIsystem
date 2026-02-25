"""
知识资产模型（上传的资料）
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class KnowledgeAsset(Base):
    """
    知识资产表（上传的资料）

    存储用户上传的 PDF、Word、视频等资料，用于 AI 生成课件时的上下文参考。
    vector_status 表示该资料是否已经向量化，可以被 AI 检索。
    """
    __tablename__ = "knowledge_assets"

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
    library_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("knowledge_libraries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属知识库"
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    vector_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="向量化状态: pending/processing/completed/failed"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="切片后的文本块数量"
    )
    image_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="解析出的图片数量"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="knowledge_assets")
    library: Mapped["KnowledgeLibrary | None"] = relationship(
        "KnowledgeLibrary",
        back_populates="assets"
    )

    def __repr__(self):
        return f"<KnowledgeAsset(id={self.id}, file_name={self.file_name})>"
