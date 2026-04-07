"""
PPT生成模块 - SQLAlchemy模型
对应 banana-slides 的 8 张核心表
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class PPTProject(Base):
    """
    PPT项目表

    存储一个PPT项目的所有元数据。
    一个用户可以创建多个PPT项目。
    """
    __tablename__ = "ppt_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名PPT")
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 创建类型: dialog/file/renovation (对应 banana 内部的 idea/outline/ppt_renovation)
    creation_type: Mapped[str] = mapped_column(String(20), nullable=False, default="dialog")

    # 原始输入内容 (如用户输入的教学需求描述)
    outline_text: Mapped[str] = mapped_column(Text, nullable=True)

    # 项目配置 (JSONB)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 主题/风格
    theme: Mapped[str] = mapped_column(String(50), nullable=True)
    template_style: Mapped[str] = mapped_column(Text, nullable=True)

    # 状态: PLANNING / GENERATING / COMPLETED / FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNING")

    # 导出相关
    exported_file_url: Mapped[str] = mapped_column(String(500), nullable=True)
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # 知识库ID列表：用户选择的知识库，Dialog生成时做RAG检索用
    knowledge_library_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)

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
    user: Mapped["User"] = relationship("User", back_populates="ppt_projects")
    pages: Mapped[list["PPTPage"]] = relationship("PPTPage", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[list["PPTTask"]] = relationship("PPTTask", back_populates="project", cascade="all, delete-orphan")
    sessions: Mapped[list["PPTSession"]] = relationship("PPTSession", back_populates="project", cascade="all, delete-orphan")
    intent: Mapped["PPTProjectIntent"] = relationship("PPTProjectIntent", back_populates="project", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<PPTProject(id={self.id}, title={self.title}, status={self.status})>"


class PPTPage(Base):
    """
    PPT页面表

    存储每一页的内容、描述、图片信息。
    """
    __tablename__ = "ppt_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 页面标题
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    # 页面描述 (AI生成)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    # 生图提示词
    image_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    # 备注/演讲者笔记
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # 图片URL
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # 图片版本锁 (每次编辑图片生成新版本，保留历史)
    image_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 页面配置 (JSONB): 背景色、布局、字体等
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 描述生成模式: auto / manual
    description_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")

    # AI处理状态
    is_description_generating: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_image_generating: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 页面素材引用
    material_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)

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
    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="pages")
    image_versions: Mapped[list["PageImageVersion"]] = relationship(
        "PageImageVersion", back_populates="page", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PPTPage(id={self.id}, page_number={self.page_number}, title={self.title})>"


class PPTTask(Base):
    """
    PPT异步任务表

    存储所有异步Celery任务的状态和结果。
    包括: 图片生成、导出、翻新解析等。
    """
    __tablename__ = "ppt_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    """
    task_type 取值:
      - generate_image       图片生成
      - export_pptx          导出PPTX
      - export_pdf           导出PDF
      - export_images        导出图片集
      - export_editable_pptx 导出可编辑PPTX (异步)
      - renovation_parse     翻新解析旧PPT/PDF
      - material_generate    素材生成
      - edit_page_image      编辑页面图片
    """

    # 任务状态: PENDING / PROCESSING / COMPLETED / FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    # 进度 0-100
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 结果数据 (JSONB): 成功时存储结果，失败时存储错误信息
    result: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # 关联页面 (可选，某些任务关联特定页面)
    page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_pages.id", ondelete="SET NULL"), nullable=True
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
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # 关联
    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="tasks")
    page: Mapped["PPTPage"] = relationship("PPTPage")

    def __repr__(self):
        return f"<PPTTask(id={self.id}, task_type={self.task_type}, status={self.status})>"


class PPTMaterial(Base):
    """
    PPT素材表

    存储已上传到OSS的素材文件元数据。
    """
    __tablename__ = "ppt_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # 文件名
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # OSS存储路径
    oss_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # OSS公网访问URL
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # 文件类型: pdf/pptx/ppt/docx/png/jpg/jpeg
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 文件大小 (字节)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    # 素材类型: reference/template/image/text
    material_type: Mapped[str] = mapped_column(String(20), nullable=False, default="reference")

    # 是否已解析 (用于翻新素材)
    is_parsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 解析结果
    parsed_content: Mapped[dict] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联
    user: Mapped["User"] = relationship("User")
    project: Mapped["PPTProject"] = relationship("PPTProject")

    def __repr__(self):
        return f"<PPTMaterial(id={self.id}, filename={self.filename}, material_type={self.material_type})>"


class PPTReferenceFile(Base):
    """
    PPT参考文件表

    存储每个项目关联的参考文件。
    """
    __tablename__ = "ppt_reference_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 文件信息
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    oss_path: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)

    # 解析状态
    parse_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    """pending | processing | completed | failed"""
    parse_error: Mapped[str] = mapped_column(Text, nullable=True)

    # 解析结果 (从旧PPT/PDF提取的大纲/内容)
    parsed_outline: Mapped[dict] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联
    project: Mapped["PPTProject"] = relationship("PPTProject")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<PPTReferenceFile(id={self.id}, filename={self.filename})>"


class PPTSession(Base):
    """
    PPT对话框会话表

    存储Dialog页面的多轮对话历史，支持断点恢复。
    在banana-slides中无对应表，是AIsystem自行实现的功能。
    """
    __tablename__ = "ppt_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 消息角色: user / assistant
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # 消息内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 附加数据 (如AI追问的选项等)
    session_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # 对话轮次
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联
    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="sessions")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<PPTSession(id={self.id}, project_id={self.project_id}, role={self.role}, round={self.round})>"


class PPTProjectIntent(Base):
    """
    项目级教学意图聚合表。

    对话消息负责保留历史，这张表负责保留当前可恢复、可确认的结构化意图状态。
    """

    __tablename__ = "ppt_project_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    topic: Mapped[str] = mapped_column(Text, nullable=True)
    audience: Mapped[str] = mapped_column(Text, nullable=True)
    goal: Mapped[str] = mapped_column(Text, nullable=True)
    duration: Mapped[str] = mapped_column(Text, nullable=True)
    constraints: Mapped[str] = mapped_column(Text, nullable=True)
    style: Mapped[str] = mapped_column(Text, nullable=True)
    interaction: Mapped[str] = mapped_column(Text, nullable=True)
    extra: Mapped[str] = mapped_column(Text, nullable=True)

    confirmed_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    pending_items: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    score_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    score_audience: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    score_structure: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    score_interaction: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=35)

    summary_text: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CLARIFYING")
    clarification_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_source_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("ppt_sessions.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="intent")
    user: Mapped["User"] = relationship("User")
    last_source_session: Mapped["PPTSession"] = relationship("PPTSession")

    def __repr__(self):
        return f"<PPTProjectIntent(project_id={self.project_id}, status={self.status})>"


class UserTemplate(Base):
    """
    用户自定义模板表

    存储用户保存的PPT模板（包含页面结构、样式配置）。
    """
    __tablename__ = "ppt_user_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 模板数据 (JSONB): 包含页面模板结构、主题配置等
    template_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 封面图URL
    cover_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # 模板来源: user (用户创建) / system (预置模板，可复制)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="user")

    # 使用次数
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<UserTemplate(id={self.id}, name={self.name}, user_id={self.user_id})>"


class PageImageVersion(Base):
    """
    页面图片版本表

    每次编辑/重新生成图片时，保存历史版本，支持回滚。
    """
    __tablename__ = "ppt_page_image_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ppt_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 版本号
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # 图片URL
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # 操作类型: generate / edit
    operation: Mapped[str] = mapped_column(String(20), nullable=False, default="generate")

    # 操作描述 (用户输入的自然语言编辑提示词)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)

    # 是否为当前活跃版本
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # 关联
    page: Mapped["PPTPage"] = relationship("PPTPage", back_populates="image_versions")
    user: Mapped["User"] = relationship("User")

    def __repr__(self):
        return f"<PageImageVersion(id={self.id}, page_id={self.page_id}, version={self.version}, is_active={self.is_active})>"
