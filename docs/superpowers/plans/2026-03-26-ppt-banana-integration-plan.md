# PPT生成模块（banana-slides集成）实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将banana-slides重构为AIsystem的`app/generators/ppt/`子模块，支持通义千问解析大纲、banana-slides providers生成页面描述和图片、OSS存储导出文件、PPTSession对话持久化。

**Architecture:** 作为FastAPI子模块接入，数据存PostgreSQL，文件存OSS，异步任务用Celery，AI分工：通义千问解析大纲，banana-slides原生provider生成页面描述和图片。

**事务风格：** 沿用 AIsystem 现有代码风格（显式 `await db.commit()`），与 `courseware.py` 等现有路由保持一致。

**Tech Stack:** FastAPI, PostgreSQL, 阿里云OSS, Celery, DashScope(通义千问), banana-slides providers(Gemini/OpenAI等)

---

## Chunk 1: 项目骨架搭建

### Task 1: 创建目录结构

**Files:**
- Create: `backend/app/generators/ppt/__init__.py`
- Create: `backend/app/generators/ppt/celery_tasks.py` (空文件，占位)
- Create: `backend/app/generators/ppt/file_service.py` (空文件，占位)

- [ ] **Step 1: 创建目录**

```bash
mkdir -p backend/app/generators/ppt
```

- [ ] **Step 2: 创建 __init__.py**

```python
# backend/app/generators/ppt/__init__.py
from .banana_models import *
from .banana_schemas import *
from .banana_routes import router as ppt_router

__all__ = ["ppt_router"]
```

- [ ] **Step 3: 创建占位文件**

创建空白的 `celery_tasks.py` 和 `file_service.py`

---

### Task 2: 创建SQLAlchemy模型

**Files:**
- Create: `backend/app/generators/ppt/banana_models.py`
- Modify: `backend/app/models/__init__.py` (添加PPTProject, PPTPage等导出)
- Test: `backend/tests/test_banana_models.py` (⚠️ 注意：实际测试目录是 `backend/tests`，不是 `backend/app/tests`)

**Model: PPTProject**

```python
# backend/app/generators/ppt/banana_models.py
from app.core.database import Base  # ⚠️ 复用现有Base，不要新建DeclarativeBase
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY  # ⚠️ 必须用dialects.postgresql的JSONB和ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime

class PPTProject(Base):
    __tablename__ = "ppt_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名PPT")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creation_type: Mapped[str] = mapped_column(String(20), default="dialog", nullable=False)
    outline_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # 项目配置（主题/横竖版等）
    theme: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PLANNING", nullable=False)
    exported_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    exported_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    knowledge_library_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    # ↑ 用户选择的知识库ID列表，Dialog生成时传给 retrieve_context() 做RAG检索
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships（PPTProject侧仅维护子资源，不维护到Courseware的反向FK）
    pages: Mapped[List["PPTPage"]] = relationship("PPTPage", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[List["PPTTask"]] = relationship("PPTTask", back_populates="project", cascade="all, delete-orphan")
    sessions: Mapped[List["PPTSession"]] = relationship("PPTSession", back_populates="project", cascade="all, delete-orphan")
    user: Mapped["User"] = relationship("User", back_populates="ppt_projects")  # ⚠️ User侧也需同步添加ppt_projects关系，见Task 4
```

**Model: PPTPage**

```python
class PPTPage(Base):
    __tablename__ = "ppt_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI生成的页面描述
    image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 生图提示词
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 演讲者笔记
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 图片版本锁
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # 页面布局配置
    description_mode: Mapped[str] = mapped_column(String(20), default="auto", nullable=False)  # auto/manual
    is_description_generating: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_image_generating: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    material_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="pages")
    image_versions: Mapped[List["PageImageVersion"]] = relationship("PageImageVersion", back_populates="page", cascade="all, delete-orphan")
```

**Model: PPTTask**

```python
class PPTTask(Base):
    __tablename__ = "ppt_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)  # Celery task UUID
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # generate_image/export_pptx/...
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING/PROCESSING/COMPLETED/FAILED
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # 成功结果或错误信息
    page_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ppt_pages.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="tasks")
```

**Model: PPTMaterial, PPTReferenceFile, PPTSession, UserTemplate, PageImageVersion**

后续创建。

---

### Task 3: 创建Pydantic Schemas

**Files:**
- Create: `backend/app/generators/ppt/banana_schemas.py`

```python
# backend/app/generators/ppt/banana_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PPTProjectCreate(BaseModel):
    title: str = Field(default="未命名PPT", max_length=255)
    description: Optional[str] = None
    creation_type: str = Field(default="dialog", pattern="^(dialog|file|renovation)$")
    theme: Optional[str] = Field(default=None, max_length=50)
    outline_text: Optional[str] = None
    settings: Optional[dict] = None
    knowledge_library_ids: Optional[List[int]] = Field(default_factory=list)
    """用户选择的知识库ID列表，Dialog生成时做RAG检索用"""

class PPTProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    outline_text: Optional[str] = None
    theme: Optional[str] = Field(default=None, max_length=50)
    settings: Optional[dict] = None
    status: Optional[str] = None
    exported_file_url: Optional[str] = None
    exported_at: Optional[datetime] = None
    knowledge_library_ids: Optional[List[int]] = None

class PPTProjectResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    creation_type: str
    outline_text: Optional[str]
    settings: dict
    theme: Optional[str]
    knowledge_library_ids: List[int]
    status: str
    exported_file_url: Optional[str]
    exported_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
```

后续补充Page、Task等schemas。

class ChatMessageRequest(BaseModel):
    content: str  # ⚠️ 注意：banana-schemas 用 content，不是 message
    round: Optional[int] = None
    metadata: Optional[dict] = None

class PageReorderRequest(BaseModel):
    page_ids: List[int]

---

### Task 4: Courseware添加ppt_project_id外键

**Files:**
- Modify: `backend/app/models/courseware.py`
- Modify: `backend/app/models/user.py` (⚠️ 添加 ppt_projects 关系到 User)
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/xxx_add_ppt_project_fk.py`

```python
# backend/app/models/courseware.py
# 在 Courseware 类中添加:
ppt_project_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("ppt_projects.id", ondelete="SET NULL"), nullable=True, unique=True  # ⚠️ 1:1 约束
)
# ⚠️ 单向关系，不使用 back_populates（避免要求 PPTProject 侧维护反向 FK）
ppt_project: Mapped[Optional["PPTProject"]] = relationship(
    "PPTProject", foreign_keys=[ppt_project_id]
)
```

```python
# backend/app/models/user.py
# 在 User 类中添加:
ppt_projects: Mapped[list["PPTProject"]] = relationship(
    "PPTProject", back_populates="user", cascade="all, delete-orphan"
)
```

```python
# backend/app/models/__init__.py
from .courseware import Courseware
from .user import User
# 添加 ppt_project / ppt_projects 导入
```

---

## Chunk 2: 路由与核心服务

### Task 5: 创建Banana路由

**Files:**
- Create: `backend/app/generators/ppt/banana_routes.py`

```python
# backend/app/generators/ppt/banana_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from .banana_models import PPTProject, PPTPage, PPTTask, PPTSession
from .banana_schemas import (
    PPTProjectCreate, PPTProjectUpdate, PPTProjectResponse,
    PPTPageResponse, ChatMessageRequest
)

router = APIRouter(prefix="/ppt", tags=["PPT生成"])

@router.post("/projects", response_model=PPTProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: PPTProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = PPTProject(
        user_id=current_user.id,
        creation_type=data.creation_type,
        title=data.title,
        outline_text=data.outline_text,
        status="DRAFT"
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.get("/projects", response_model=List[PPTProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PPTProject).where(PPTProject.user_id == current_user.id).order_by(PPTProject.created_at.desc())
    )
    return result.scalars().all()

@router.post("/projects/{project_id}/chat")
async def chat(
    project_id: int,
    data: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 保存用户消息
    session = PPTSession(
        project_id=project_id,
        user_id=current_user.id,
        role="user",
        content=data.message
    )
    db.add(session)
    await db.commit()
    # TODO: 调用 AI 服务获取回复
    return {"message": "AI回复暂未实现"}

@router.post("/projects/{project_id}/pages/reorder")
async def reorder_pages(
    project_id: int,
    page_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 按 page_ids 顺序更新 order_index
    for idx, page_id in enumerate(page_ids):
        result = await db.execute(
            select(PPTPage).where(PPTPage.id == page_id, PPTPage.project_id == project_id)
        )
        page = result.scalar_one_or_none()
        if page:
            page.order_index = idx
    await db.commit()
    return {"status": "ok"}

@router.post("/projects/{project_id}/outline/generate/stream")
async def generate_outline_stream(project_id: int, ...):
    # SSE 流式返回大纲，与 descriptions/stream 格式一致
    ...
```

---

### Task 6: 迁移AIService（去Flask依赖）

**Files:**
- Create: `backend/app/generators/ppt/banana_service.py`
- Modify: `backend/app/generators/ppt/prompts.py` (沿用banana-slides的prompts.py)

从 `D:\banana-slides\backend\services\ai_service.py` 迁移核心逻辑，去除：
- `from flask import current_app` 的引用
- `db.session` 的直接使用
- `ProjectContext` 保留，构造时注入依赖

---

### Task 7: 大纲解析接入通义千问（新增Task）

**前置条件**：DashScopeService 无流式接口，需先在 `dashscope_service.py` 中新增流式适配方法，或在 `banana_service.py` 中通过非流式调用实现大纲解析。

**Files:**
- Modify: `backend/app/services/ai/dashscope_service.py` (如需流式)
- Modify: `backend/app/generators/ppt/banana_service.py`

> **方案选择**：`parse_outline_text` 优先使用 `DashScopeService.chat()` 非流式同步调用（避免改动过大），后续如需 SSE 流式返回再扩展流式接口。

**方案A（非流式，同步）**：
```python
# banana_service.py
async def parse_outline_text(self, project_context, language="zh"):
    prompt = get_outline_parsing_prompt_markdown(project_context, language)
    response = await self.dashscope.chat(prompt)  # 非流式
    return self._parse_json_response(response)
```

**方案B（流式，SSE）**：需先在 `DashScopeService` 新增 `chat_stream()` 方法，再在 `banana_service.py` 中使用流式解析。

---

## Chunk 3: 任务系统与SSE流式

### Task 8: Celery Task封装

**Files:**
- Modify: `backend/app/generators/ppt/celery_tasks.py`
- Modify: `backend/app/celery.py` (添加include)
- Create: `backend/alembic/versions/xxx_add_ppt_tables.py` (⚠️ 注意：实际Alembic迁移目录是 `backend/alembic/versions`)

**⚠️ Celery注册闭环**：当前 `celery.py` 只 `include=["app.tasks"]`，新增任务不会自动被发现。需要在 `celery.py` 中添加：

```python
# backend/app/celery.py
celery_app = Celery(
    "ai_teaching",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks", "app.generators.ppt.celery_tasks"]  # 添加新的task模块
)

# 添加入口队列
celery_app.conf.task_routes = {
    "banana-slides.*": {"queue": "default"},
    "app.tasks.*": {"queue": "default"},
}
```

**Worker启动示例**：
```bash
# 共用现有worker，无需额外启动参数（默认监听 default 队列）
celery -A app.celery worker -l info
```

```python
# backend/app/generators/ppt/celery_tasks.py
from app.celery import celery_app
from app.generators.ppt.banana_service import BananaAIService
from app.services.ai.dashscope_service import get_dashscope_service
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.generators.ppt.banana_models import PPTProject

@celery_app.task(bind=True, name="banana-slides.generate_descriptions")
def generate_descriptions_task(self, project_id: int, language: str = "zh"):
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PPTProject).where(PPTProject.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                return {"error": "Project not found"}
            dashscope = get_dashscope_service()
            banana_svc = BananaAIService(dashscope)
            # ... 生成逻辑
    # 同步调用异步函数
    import asyncio
    return asyncio.run(_run())
```

---

### Task 9: SSE流式路由

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

> **SSE 协议**：统一使用 `event: message`，所有事件通过 `data.type` 字段区分。前端按 `data.type` 分流，不依赖 event 名。

```python
from fastapi.responses import StreamingResponse
import json

@router.post("/projects/{project_id}/descriptions/generate/stream")
async def generate_descriptions_stream(project_id: int, ...):
    async def event_generator():
        async for page_data in banana_service.generate_descriptions_stream(...):
            # event 名固定为 message，通过 data.type 分流
            yield f"event: message\ndata: {json.dumps({'type': 'page', **page_data})}\n\n"
        yield f"event: message\ndata: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

> **SSE格式**：`event: message\ndata: {"type": "...", ...}\n\n`，一个空行分隔每帧。

---

## Chunk 4: OSS存储与导出

### Task 10: OSS文件服务

**Files:**
- Modify: `backend/app/generators/ppt/file_service.py`

```python
# backend/app/generators/ppt/file_service.py
import oss2
from app.core.config import settings

class OSSFileService:
    def __init__(self):
        self.bucket = oss2.Bucket(
            oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET),
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET  # ⚠️ 实际字段名是 OSS_BUCKET，不是 OSS_BUCKET_NAME
        )

    def upload_file(self, local_path: str, oss_key: str) -> str:
        self.bucket.put_object_from_file(oss_key, local_path)
        # ⚠️ 无 OSS_PUBLIC_ENDPOINT 字段，公网URL通过拼接获取
        return f"https://{settings.OSS_BUCKET}.{settings.OSS_ENDPOINT}/{oss_key}"

    def upload_bytes(self, data: bytes, oss_key: str) -> str:
        self.bucket.put_object(oss_key, data)
        # ⚠️ 统一返回签名URL（兼容私有bucket）
        return self.get_signed_url(oss_key)

    def get_signed_url(self, oss_key: str, expires: int = 3600) -> str:
        return self.bucket.sign_url("GET", oss_key, expires)
```

---

### Task 11: 导出服务适配OSS

**Files:**
- Create/Modify: `backend/app/generators/ppt/export_service.py` (沿用banana-slides的export_service.py)

修改 `create_pptx_from_images` 方法，输出从本地文件改为OSS上传：

```python
def export_pptx_to_oss(project_id: int, image_paths: List[str], filename: str) -> str:
    # 生成PPTX
    pptx_bytes = ExportService.create_pptx_from_images(image_paths)
    # 上传到OSS
    oss_key = f"ppt/{project_id}/exports/{filename}"
    oss_service.upload_bytes(pptx_bytes, oss_key)
    return oss_service.get_signed_url(oss_key)
```

---

## Chunk 5: 对话持久化

### Task 12: PPTSession模型与路由

**Files:**
- Modify: `backend/app/generators/ppt/banana_models.py` (添加PPTSession)
- Modify: `backend/app/generators/ppt/banana_schemas.py` (添加PPTSessionSchema)
- Modify: `backend/app/generators/ppt/banana_routes.py` (添加session路由)

```python
# PPTSession Model
class PPTSession(Base):
    __tablename__ = "ppt_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("ppt_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["PPTProject"] = relationship("PPTProject", back_populates="sessions")
```

> **Dialog 自研接口补充**：`POST /projects/{id}/dialog/generate-outline` 在此 Task 中一并实现，负责从 PPTSession 对话历史生成结构化 outline（调用 DashScope），写入 `PPTProject.outline_text`。

---

## Chunk 6: 收尾与集成

### Task 13: 注册路由到主应用

**Files:**
- Modify: `backend/app/api/__init__.py` (当前实际路由聚合文件)

```python
from app.generators.ppt import ppt_router

api_router.include_router(ppt_router)
```

---

### Task 14: requirements.txt添加依赖

**Files:**
- Modify: `backend/requirements.txt`

**最小可运行依赖清单**：

```txt
# 必须新增
oss2>=2.18.0        # 阿里云OSS SDK

# 必须从banana-slides沿用（确认AIsystem requirements中是否已存在）
google-genai>=1.52.0
openai>=1.0.0
anthropic>=0.30.0
python-pptx>=1.0.0
img2pdf>=0.5.1
PyMuPDF>=1.24.0
tenacity>=9.0.0
pillow>=12.0.0
```

> **实施建议**：先将 banana-slides 的 `pyproject.toml` 中所有依赖与 AIsystem 的 `requirements.txt` 做 diff，标记出重复和新增项，确保迁移后 `pip install -r requirements.txt` 能完整安装所有依赖。

---

## Chunk 7: 前端配套接口

> 以下 Task 为配合前端实现而新增的接口

### Task 15: 素材管理接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`
- Modify: `backend/app/generators/ppt/banana_schemas.py`

| 接口 | 说明 |
|---|---|
| `GET /projects/{id}/materials` | 获取项目素材列表 |
| `POST /projects/{id}/materials/upload` | 上传素材 |
| `DELETE /projects/{id}/materials/{material_id}` | 删除素材 |
| `GET /materials` | 获取全局素材中心列表 |

---

### Task 16: 模板管理接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `GET /templates/presets` | 获取预设模板列表 |
| `GET /templates/user` | 获取用户模板列表 |

---

### Task 17: 导出任务接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `GET /projects/{id}/export-tasks` | 获取导出任务列表 |
| `GET /export-tasks/{task_id}` | 获取单个任务状态 |

---

### Task 18: 图片版本管理接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`
- Modify: `backend/app/generators/ppt/banana_models.py` (PageImageVersion)

| 接口 | 说明 |
|---|---|
| `GET /projects/{id}/pages/{page_id}/versions` | 获取图片版本历史 |
| `POST /projects/{id}/pages/{page_id}/versions` | 创建新版本 |

---

### Task 19: 项目设置接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `PUT /projects/{id}/settings` | 更新项目设置（横竖版/导出方式/额外要求等） |

---

### Task 20: 参考文件确认接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/{id}/reference-files/{file_id}/confirm` | 确认参考文件解析完成 |

---

### Task 21: 批量删除项目接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/batch-delete` | 批量删除项目 |

---

### Task 22: 自然语言修改接口（banana-slides原生）

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`
- Modify: `backend/app/generators/ppt/banana_service.py`
- Modify: `backend/app/generators/ppt/celery_tasks.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/{id}/refine/outline` | 自然语言修改大纲 |
| `POST /projects/{id}/refine/descriptions` | 自然语言批量修改页面描述 |
| `POST /projects/{id}/pages/{page_id}/edit/image` | 单页图片自然语言编辑（异步任务） |

**实现要点**：
- `refine_outline` 调用 `banana_service.refine_outline()`，请求体字段：`user_requirement`（自然语言修改要求）+ `language`（输出语言），返回修改后的 pages
- `refine_descriptions` 调用 `banana_service.refine_descriptions()`，请求体字段：`user_requirement`（自然语言修改要求）+ `language`（输出语言）
- 两者均为同步调用（不走 Celery），直接返回修改后的结果
- 单页图片编辑 `edit/image` 为异步任务（Celery），调用 `edit_page_image_task`，返回 `task_id`，编辑前自动保存版本到 `PageImageVersion`
- 前端使用 `AiRefineInput` 组件，带历史记录展示和 Ctrl+Enter 提交

---

### Task 23: PPT翻新项目接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/renovation` | 创建PPT翻新项目（上传PDF/PPTX，异步解析） |

**实现要点**：
- 接收 `multipart/form-data` 上传 PDF/PPTX/PPT/DOCX 文件
- 创建 `creation_type='renovation'` 的 PPTProject，banana 内部映射为 `creation_type='ppt_renovation'`
- 提取 PDF 图片并关联到项目（每页一张图片）
- 提交 Celery 异步任务 `process_ppt_renovation_task`
- 返回 `{ project_id, task_id }`，前端轮询任务状态

---

### Task 24: 参考文件管理接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/{id}/reference-files` | 上传参考文件 |
| `POST /projects/{id}/reference-files/{file_id}/parse` | 触发参考文件解析（Celery异步） |
| `GET /projects/{id}/reference-files/{file_id}` | 获取参考文件详情（含 parse_status） |
| `GET /reference-files/{file_id}` | 获取参考文件预览URL |

**实现要点**：
- 参考文件上传到 OSS，返回 `file_id` + `parse_status='pending'`
- 解析任务通过 Celery 执行，结果写回 `markdown_content`
- 支持 PDF/DOCX/PPTX/图片等格式

---

### Task 25: 素材管理接口（扩展）

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`
- Modify: `backend/app/generators/ppt/celery_tasks.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/{id}/materials/generate` | 生成素材图片（Celery异步，返回 task_id） |
| `GET /materials` | 获取全局素材中心列表（所有用户的素材） |

**实现要点**：
- `generate_material_image_task`：接收 prompt + 参考图片，调用图片生成 provider
- `GET /materials` 不需要 project_id 过滤，返回所有用户的公开素材

---

### Task 26: 大纲页辅助接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/{id}/refine/outline` | 自然语言修改大纲（banana-slides原生，见 Task 22） |
| `POST /projects/{id}/pages` | 添加页面（支持批量追加） |
| `DELETE /projects/{id}/pages/{page_id}` | 删除页面 |
| `POST /projects/{id}/pages/{page_id}/regenerate-renovation` | 翻新模式单页重新解析 |

**实现要点**：
- `refine/outline` 见 Task 22
- 翻新单页重新生成：提取原PDF对应页图片，重新生成大纲+描述

---

### Task 27: 描述页辅助接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`
- Modify: `backend/app/models/settings.py`（或新建 PPTProjectSettings）

| 接口 | 说明 |
|---|---|
| `PUT /projects/{id}/settings` | 更新项目生成设置（详细程度/生成模式/额外字段） |
| `GET /projects/{id}/settings` | 获取项目生成设置 |

**实现要点**：
- `description_generation_mode`：'streaming' | 'parallel'
- `description_extra_fields`：启用哪些额外字段的列表（含顺序）
- `image_prompt_extra_fields`：传入生图 prompt 的字段子集
- `detail_level`：'concise' | 'default' | 'detailed'
- 可存储在 PPTProject 或独立的 settings 表

---

### Task 28: 预览页辅助接口

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `POST /projects/{id}/pages/{page_id}/versions/{version_id}/set-current` | 切换页面当前图片版本 |
| `DELETE /projects/{id}/pages/{page_id}` | 删除页面 |
| `POST /projects/{id}/template` | 上传项目模板图片 |

---

### Task 29: 模板管理接口（扩展）

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

| 接口 | 说明 |
|---|---|
| `GET /templates/presets` | 获取预设模板列表（含分类标签） |
| `POST /projects/{id}/template` | 上传项目模板图片（覆盖当前项目模板） |
| `GET /templates/user` | 获取用户上传的模板列表 |
| `POST /user-templates` | 上传用户模板 |
| `DELETE /user-templates/{id}` | 删除用户模板 |

---

## Chunk 9: 前端历史项目与详情页

### Task 30: CoursewareManage PPT Tab

**Files:**
- Modify: `teacher-platform/src/views/CoursewareManage.vue`

**功能：**
- 在 CoursewareManage tab 栏新增「PPT」Tab
- 调用 `GET /ppt/projects` 展示用户所有历史 PPTProject
- 项目卡片：标题/创建时间/状态 badge
- 「新建PPT」按钮 → 跳转 `/lesson-prep?tab=ppt`
- 点击项目卡片 → 跳转 `/lesson-prep?tab=ppt&projectId={id}`
- 支持删除项目（单个 + 批量）

---

### Task 31: LessonPrepPptDetail 详情页（4-Tab）

**Files:**
- Modify: `teacher-platform/src/views/LessonPrep.vue`（支持 `projectId` query 参数）
- Create: `teacher-platform/src/views/LessonPrepPptDetail.vue`

**路由方案（方案A）：**
```
/lesson-prep?tab=ppt                        → LessonPrepPpt.vue（新建项目流程）
/lesson-prep?tab=ppt&projectId={id}        → LessonPrepPptDetail.vue（4-Tab 详情页）
```

**4-Tab：Dialog | Outline | Description | Preview**

| Tab | 说明 |
|-----|------|
| Dialog | 只读展示对话历史，调用 `GET /ppt/projects/{id}/sessions` |
| Outline | 13.2 大纲编辑功能（复用/适配） |
| Description | 13.3 描述编辑功能（复用/适配） |
| Preview | 13.4 预览编辑功能（复用/适配） |

**进入时：** 调用 `GET /ppt/projects/{id}` 加载完整项目数据
**Header：** 项目标题 + 「返回项目列表」按钮

---

### Task 32: Dialog Tab 对话历史展示

**Files:**
- Modify: `LessonPrepPptDetail.vue`

**功能：**
- `GET /ppt/projects/{id}/sessions` 获取所有 PPTSession 记录
- 按 `round` 分组展示对话气泡
- 用户消息（左侧）+ AI回复（右侧）
- AI回复包含追问选项时，渲染选项按钮（只读）

---

### Task 33: 欢迎页知识库选择器

**Files:**
- Modify: `teacher-platform/src/views/LessonPrepPpt.vue`
- Modify: `backend/app/generators/ppt/banana_schemas.py`（PPTProjectCreate 添加 knowledge_library_ids）

**功能：**
- 主题输入框下方新增「选择知识库」按钮/下拉框
- 调用 `GET /api/v1/libraries?scope=personal` + `GET /api/v1/libraries?scope=system` 获取知识库列表，合并后多选
- 选择后，将 `knowledge_library_ids` 传入创建项目的请求
- `POST /ppt/projects` 时传入 `knowledge_library_ids`
- Dialog 对话生成时，`banana_service` 使用 `knowledge_library_ids` 调用 `VectorStore.similarity_search` 做 RAG 检索

**API：**

| 接口 | 说明 |
|------|------|
| `GET /api/v1/libraries?scope=personal|system` | 获取知识库列表（已有接口，需两次调用合并） |
| `POST /ppt/projects` | 新增 `knowledge_library_ids` 参数 |

**Dialog RAG 检索参考实现**（`lesson_plan_service.py retrieve_context`）：
```python
# 检索指定知识库
results = await retriever.search(query=query, user_id=user_id, k=5, library_ids=library_ids)
```

---

## 实施顺序

1. **Chunk 1** (Task 1-4): 骨架搭建，模型创建，Courseware关联
2. **Chunk 2** (Task 5-7): 路由创建，AIService迁移，接入通义千问
3. **Chunk 3** (Task 8-9): Celery任务封装，SSE流式接口
4. **Chunk 4** (Task 10-11): OSS文件服务，导出适配OSS
5. **Chunk 5** (Task 12): PPTSession对话持久化 + Dialog generate-outline
6. **Chunk 6** (Task 13-14): 路由注册，依赖添加
7. **Chunk 7** (Task 15-27): 前端配套接口（素材/模板/导出任务/图片版本/设置/参考文件/翻新/自然语言修改/大纲辅助/描述辅助/预览辅助）
8. **Chunk 8** (Task 28-29): 模板管理扩展 + 预览页辅助接口
9. **Chunk 9** (Task 30-32): 前端历史项目列表 + 4-Tab详情页
10. **Task 33**: 欢迎页知识库选择器 + Dialog RAG检索
