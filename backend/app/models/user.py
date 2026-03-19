"""
用户模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为系统管理员"
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Token 版本号，修改密码时+1使所有旧token失效"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联关系
    coursewares: Mapped[list["Courseware"]] = relationship(
        "Courseware",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    chat_histories: Mapped[list["ChatHistory"]] = relationship(
        "ChatHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    knowledge_assets: Mapped[list["KnowledgeAsset"]] = relationship(
        "KnowledgeAsset",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    knowledge_libraries: Mapped[list["KnowledgeLibrary"]] = relationship(
        "KnowledgeLibrary",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    ppt_sessions: Mapped[list["PptSession"]] = relationship(
        "PptSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, phone={self.phone})>"
