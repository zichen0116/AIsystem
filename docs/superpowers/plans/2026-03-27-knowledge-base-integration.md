# Knowledge Base Frontend-Backend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the knowledge base frontend pages (list + detail) to real backend APIs, replacing all mock data, and integrate Alibaba Cloud OSS for file storage.

**Architecture:** Backend-first approach. Add DB migration and model fields first, then OSS service, then update API endpoints, then build Pinia store, then rewire both Vue pages. Each task produces a working, testable unit.

**Tech Stack:** Python/FastAPI, SQLAlchemy, Alembic, oss2, Vue 3, Pinia, Vite

---

## File Structure

### Files to Create
- `backend/alembic/versions/20260327_add_library_tags_updated_at.py` — DB migration
- `backend/app/services/oss_service.py` — OSS upload/delete/download service
- `backend/app/api/upload.py` — File upload endpoint
- `teacher-platform/src/stores/knowledge.js` — Pinia store for knowledge base state

### Files to Modify
- `backend/requirements.txt` — Add `oss2`
- `backend/app/models/knowledge_library.py` — Add `tags`, `updated_at` columns
- `backend/app/schemas/library.py` — Add `tags`, `updated_at`, `asset_count` to response; `tags` to update
- `backend/app/api/libraries.py` — Add tag endpoints, scope=all, search/tag filtering, asset_count
- `backend/app/api/knowledge.py` — System library asset visibility, OSS cleanup on delete
- `backend/app/api/__init__.py` — Register upload router
- `backend/app/tasks.py` — Adapt Celery tasks for OSS file paths
- `teacher-platform/src/views/KnowledgeBase.vue` — Remove mock data, connect to store/API
- `teacher-platform/src/views/KnowledgeDetail.vue` — Remove mock data, connect to API

---

### Task 1: Add `oss2` dependency

**Files:**
- Modify: `backend/requirements.txt:80`

- [ ] **Step 1: Add oss2 to requirements.txt**

Add below the `# 知识图谱` section, before `# 文档导出`:

```
# 阿里云 OSS
oss2>=2.18.0
```

- [ ] **Step 2: Install dependency**

Run: `cd backend && pip install oss2`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add oss2 dependency for Alibaba Cloud OSS integration"
```

---

### Task 2: Database migration — add `tags` and `updated_at` to `knowledge_libraries`

**Files:**
- Modify: `backend/app/models/knowledge_library.py`
- Create: `backend/alembic/versions/20260327_add_library_tags_updated_at.py`

- [ ] **Step 1: Update KnowledgeLibrary model**

In `backend/app/models/knowledge_library.py`, add the imports and columns:

```python
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
```

- [ ] **Step 2: Create migration file**

Create `backend/alembic/versions/20260327_add_library_tags_updated_at.py`:

```python
"""add tags and updated_at to knowledge_libraries

Revision ID: add_lib_tags_001
Revises: 20260319_add_question_papers
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = 'add_lib_tags_001'
down_revision = '20260319_add_question_papers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('knowledge_libraries',
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]')
    )
    op.add_column('knowledge_libraries',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Backfill updated_at from created_at
    op.execute("UPDATE knowledge_libraries SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column('knowledge_libraries', 'updated_at', nullable=False)


def downgrade() -> None:
    op.drop_column('knowledge_libraries', 'updated_at')
    op.drop_column('knowledge_libraries', 'tags')
```

- [ ] **Step 3: Check the down_revision chain is correct**

Read the last migration file to get its revision ID:

Run: `cd backend && python -c "import pathlib; lines=pathlib.Path('alembic/versions/20260319_add_question_papers.py').read_text().splitlines()[:12]; print('\n'.join(lines))"`

Verify the `revision` value matches what we set as `down_revision` above. If the revision ID is different from `20260319_add_question_papers`, update the migration file accordingly.

- [ ] **Step 4: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies successfully, prints "Running upgrade ... -> add_lib_tags_001"

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/knowledge_library.py backend/alembic/versions/20260327_add_library_tags_updated_at.py
git commit -m "feat(db): add tags and updated_at columns to knowledge_libraries"
```

---

### Task 3: OSS service

**Files:**
- Create: `backend/app/services/oss_service.py`

- [ ] **Step 1: Create OSS service**

Create `backend/app/services/oss_service.py`:

```python
"""
阿里云 OSS 文件存储服务
"""
import uuid
import os
import tempfile
import logging
from pathlib import Path
from urllib.parse import urlparse

import oss2
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# 扩展名 → FileType 枚举值映射
EXT_TO_FILE_TYPE = {
    "pdf": "pdf",
    "doc": "word",
    "docx": "word",
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "mp4": "video",
}

# 允许的 MIME 类型
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "video/mp4",
    "image/jpeg",
    "image/png",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _get_bucket() -> oss2.Bucket:
    """获取 OSS Bucket 实例"""
    auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET)


def _url_to_key(url: str) -> str:
    """从 OSS URL 中提取 object key"""
    parsed = urlparse(url)
    return parsed.path.lstrip("/")


def get_file_type(filename: str) -> str | None:
    """从文件名获取 FileType 枚举值，不支持的返回 None"""
    ext = Path(filename).suffix.lstrip(".").lower()
    return EXT_TO_FILE_TYPE.get(ext)


async def upload_file(file: UploadFile, user_id: int) -> dict:
    """
    上传文件到 OSS

    Returns:
        {"url": "https://...", "file_name": "原始名.pdf", "file_type": "pdf"}
    """
    # 校验 MIME
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"不支持的文件类型: {content_type}")

    # 读取文件内容并校验大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制（最大 50MB）")

    # 生成 OSS key
    original_name = file.filename or "unnamed"
    ext = Path(original_name).suffix.lstrip(".").lower()
    file_type = EXT_TO_FILE_TYPE.get(ext)
    if not file_type:
        raise ValueError(f"不支持的文件扩展名: .{ext}")

    object_key = f"knowledge/{user_id}/{uuid.uuid4().hex}.{ext}"

    # 上传
    bucket = _get_bucket()
    bucket.put_object(object_key, content)

    # 构造公开 URL
    # 格式: https://{bucket}.{endpoint_without_scheme}/{key}
    endpoint_host = settings.OSS_ENDPOINT.replace("https://", "").replace("http://", "")
    url = f"https://{settings.OSS_BUCKET}.{endpoint_host}/{object_key}"

    logger.info(f"文件上传成功: {original_name} -> {url}")

    return {
        "url": url,
        "file_name": original_name,
        "file_type": file_type,
    }


def delete_file(url: str) -> None:
    """删除 OSS 文件，URL 不是 OSS 链接时静默跳过"""
    if not url or settings.OSS_BUCKET not in url:
        return
    try:
        key = _url_to_key(url)
        bucket = _get_bucket()
        bucket.delete_object(key)
        logger.info(f"OSS 文件已删除: {key}")
    except Exception as e:
        logger.warning(f"OSS 文件删除失败: {url}, {e}")


def download_to_temp(url: str) -> str:
    """
    从 OSS 下载文件到临时目录

    Returns:
        本地临时文件路径
    """
    key = _url_to_key(url)
    ext = Path(key).suffix
    temp_dir = Path(tempfile.gettempdir()) / "oss_downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    local_path = str(temp_dir / f"{uuid.uuid4().hex}{ext}")

    bucket = _get_bucket()
    bucket.get_object_to_file(key, local_path)
    logger.info(f"OSS 文件下载到: {local_path}")

    return local_path
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && python -c "from app.services.oss_service import upload_file, delete_file, download_to_temp; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/oss_service.py
git commit -m "feat: add OSS service for file upload/delete/download"
```

---

### Task 4: File upload API endpoint

**Files:**
- Create: `backend/app/api/upload.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Create upload endpoint**

Create `backend/app/api/upload.py`:

```python
"""
文件上传路由
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.core.auth import CurrentUser
from app.services import oss_service

router = APIRouter(prefix="/upload", tags=["文件上传"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    current_user: CurrentUser,
):
    """
    上传文件到 OSS。

    - 鉴权：必须登录
    - 限制：≤50MB，MIME 白名单
    - 返回：{ url, file_name, file_type }
    """
    try:
        result = await oss_service.upload_file(file, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return result
```

- [ ] **Step 2: Register upload router**

In `backend/app/api/__init__.py`, add the import and include:

Add after the existing imports:
```python
from app.api import upload
```

Add after the last `api_router.include_router(...)` line:
```python
api_router.include_router(upload.router)
```

- [ ] **Step 3: Verify endpoint registers**

Run: `cd backend && python -c "from app.api import api_router; routes = [r.path for r in api_router.routes]; print([p for p in routes if 'upload' in p])"`
Expected: Output includes `/upload`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/upload.py backend/app/api/__init__.py
git commit -m "feat(api): add POST /upload endpoint for OSS file upload"
```

---

### Task 5: Update library schemas

**Files:**
- Modify: `backend/app/schemas/library.py`

- [ ] **Step 1: Add tags, updated_at, asset_count to schemas**

Replace the entire content of `backend/app/schemas/library.py`:

```python
"""
知识库相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime


class KnowledgeLibraryCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    is_system: bool = False
    is_public: bool = False


class KnowledgeLibraryUpdate(BaseModel):
    """更新知识库请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    is_public: bool | None = None


class KnowledgeLibraryResponse(BaseModel):
    """知识库响应"""
    id: int
    owner_id: int
    name: str
    description: str | None
    is_system: bool
    is_public: bool
    tags: list[str] = Field(default_factory=list)
    asset_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeLibraryListResponse(BaseModel):
    """知识库列表响应"""
    items: list[KnowledgeLibraryResponse]
    total: int


class TagRenameRequest(BaseModel):
    """标签重命名请求"""
    old_name: str = Field(..., min_length=1)
    new_name: str = Field(..., min_length=1)


class TagRenameResponse(BaseModel):
    """标签重命名响应"""
    updated_count: int


class AddToGraphRequest(BaseModel):
    """添加到知识图谱请求"""
    asset_ids: list[int] = Field(..., min_length=1, description="知识资产 ID 列表")


class AddToGraphResponse(BaseModel):
    """添加到知识图谱响应"""
    task_id: str
    message: str
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/library.py
git commit -m "feat(schemas): add tags, updated_at, asset_count to library schemas"
```

---

### Task 6: Update libraries API — scope=all, search, tag filtering, asset_count, tag endpoints

**Files:**
- Modify: `backend/app/api/libraries.py`

- [ ] **Step 1: Rewrite libraries.py with all new features**

Replace the entire content of `backend/app/api/libraries.py`:

```python
"""
知识库路由
"""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import sqlalchemy as sa

from app.core.database import get_db
from app.core.auth import CurrentUser, AdminUser
from app.models.knowledge_library import KnowledgeLibrary
from app.models.knowledge_asset import KnowledgeAsset
from app.schemas.library import (
    KnowledgeLibraryCreate,
    KnowledgeLibraryUpdate,
    KnowledgeLibraryResponse,
    KnowledgeLibraryListResponse,
    TagRenameRequest,
    TagRenameResponse,
    AddToGraphRequest,
    AddToGraphResponse,
)

router = APIRouter(prefix="/libraries", tags=["知识库"])


def _library_to_response(library: KnowledgeLibrary, asset_count: int = 0) -> dict:
    """将 ORM 对象转换为响应 dict，附加 asset_count"""
    return {
        "id": library.id,
        "owner_id": library.owner_id,
        "name": library.name,
        "description": library.description,
        "is_system": library.is_system,
        "is_public": library.is_public,
        "tags": library.tags or [],
        "asset_count": asset_count,
        "created_at": library.created_at,
        "updated_at": library.updated_at,
    }


@router.post("", response_model=KnowledgeLibraryResponse, status_code=status.HTTP_201_CREATED)
async def create_library(
    data: KnowledgeLibraryCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """创建知识库。is_system/is_public 仅管理员可设置。"""
    is_system = False
    is_public = False
    if current_user.is_admin:
        is_system = data.is_system
        is_public = data.is_public

    library = KnowledgeLibrary(
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        tags=data.tags or [],
        is_system=is_system,
        is_public=is_public,
    )
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return _library_to_response(library, 0)


@router.get("", response_model=KnowledgeLibraryListResponse)
async def list_libraries(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Literal["all", "personal", "system"] = Query("all"),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    列出知识库。
    scope=all: 用户自己的库 + 所有公开系统库
    scope=personal: 当前用户自己创建的库
    scope=system: 所有公开的系统级库
    """
    base_conditions = [KnowledgeLibrary.is_deleted == False]

    if scope == "personal":
        base_conditions.append(KnowledgeLibrary.owner_id == current_user.id)
    elif scope == "system":
        base_conditions.append(KnowledgeLibrary.is_system == True)
        base_conditions.append(KnowledgeLibrary.is_public == True)
    else:  # all
        base_conditions.append(
            or_(
                KnowledgeLibrary.owner_id == current_user.id,
                (KnowledgeLibrary.is_system == True) & (KnowledgeLibrary.is_public == True)
            )
        )

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        base_conditions.append(
            or_(
                KnowledgeLibrary.name.ilike(search_pattern),
                KnowledgeLibrary.description.ilike(search_pattern),
            )
        )

    # Tag filter — use text LIKE as workaround for JSON (not JSONB) column
    if tag:
        # tags 列是 JSON 类型（非 JSONB），不支持 @> 操作符
        # 使用 CAST + LIKE 进行文本匹配
        base_conditions.append(
            func.cast(KnowledgeLibrary.tags, sa.Text).contains(f'"{tag}"')
        )

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeLibrary).where(*base_conditions)
    )
    total = count_result.scalar()

    # Query libraries
    result = await db.execute(
        select(KnowledgeLibrary).where(*base_conditions)
        .order_by(KnowledgeLibrary.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    libraries = result.scalars().all()

    # Batch load asset counts
    lib_ids = [lib.id for lib in libraries]
    asset_counts: dict[int, int] = {}
    if lib_ids:
        count_rows = await db.execute(
            select(
                KnowledgeAsset.library_id,
                func.count().label("cnt")
            )
            .where(KnowledgeAsset.library_id.in_(lib_ids))
            .group_by(KnowledgeAsset.library_id)
        )
        for row in count_rows:
            asset_counts[row.library_id] = row.cnt

    items = [
        _library_to_response(lib, asset_counts.get(lib.id, 0))
        for lib in libraries
    ]

    return KnowledgeLibraryListResponse(items=items, total=total)


@router.get("/tags")
async def get_user_tags(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取当前用户的标签池（所有库 tags 去重合集）"""
    result = await db.execute(
        select(KnowledgeLibrary.tags).where(
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    all_tags_lists = result.scalars().all()
    tag_set = set()
    for tags in all_tags_lists:
        if tags:
            tag_set.update(tags)
    return sorted(tag_set)


@router.patch("/tags/rename", response_model=TagRenameResponse)
async def rename_tag(
    data: TagRenameRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """全局重命名标签：遍历用户所有库，将 old_name 替换为 new_name"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    libraries = result.scalars().all()

    updated = 0
    for lib in libraries:
        tags = list(lib.tags or [])
        if data.old_name in tags:
            idx = tags.index(data.old_name)
            tags[idx] = data.new_name
            lib.tags = tags
            updated += 1

    await db.commit()
    return TagRenameResponse(updated_count=updated)


@router.patch("/{library_id}", response_model=KnowledgeLibraryResponse)
async def update_library(
    library_id: int,
    data: KnowledgeLibraryUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新知识库名称/描述/标签。is_public 仅管理员可修改。"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

    if data.name is not None:
        library.name = data.name
    if data.description is not None:
        library.description = data.description
    if data.tags is not None:
        library.tags = data.tags
    if data.is_public is not None:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可修改公开状态")
        library.is_public = data.is_public

    await db.commit()
    await db.refresh(library)

    # Get asset count
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeAsset).where(
            KnowledgeAsset.library_id == library_id
        )
    )
    asset_count = count_result.scalar()

    return _library_to_response(library, asset_count)


@router.delete("/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(
    library_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """软删除知识库，Celery 异步清理向量和文件。"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

    library.is_deleted = True
    await db.commit()

    from app.tasks import cleanup_library as cleanup_task
    cleanup_task.delay(library_id)

    return None


@router.post(
    "/{library_id}/add-to-graph",
    response_model=AddToGraphResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def add_to_graph(
    library_id: int,
    data: AddToGraphRequest,
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """将知识资产添加到知识图谱（仅管理员，仅系统知识库）。"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.is_system == True,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系统知识库不存在",
        )

    from app.tasks import build_graph_index
    task = build_graph_index.delay(library_id, data.asset_ids)

    return AddToGraphResponse(
        task_id=task.id,
        message=f"图索引构建任务已提交，共 {len(data.asset_ids)} 个资产",
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/libraries.py
git commit -m "feat(api): add scope=all, search, tag filter, asset_count, tag endpoints to libraries API"
```

---

### Task 7: Update knowledge API — system library visibility + OSS cleanup

**Files:**
- Modify: `backend/app/api/knowledge.py:66-92` (list_knowledge_assets)
- Modify: `backend/app/api/knowledge.py:251-278` (delete_knowledge_asset)

- [ ] **Step 1: Update list_knowledge_assets for system library visibility**

In `backend/app/api/knowledge.py`, replace the `list_knowledge_assets` function (lines 66-92):

```python
@router.get("", response_model=KnowledgeAssetListResponse)
async def list_knowledge_assets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    library_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """列出知识资产，可按知识库过滤。系统公开库对所有用户可见。"""
    conditions = []

    if library_id is not None:
        # Check if it's a system public library
        lib_result = await db.execute(
            select(KnowledgeLibrary).where(
                KnowledgeLibrary.id == library_id,
                KnowledgeLibrary.is_deleted == False,
            )
        )
        library = lib_result.scalar_one_or_none()
        if not library:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

        if library.is_system and library.is_public:
            # System public library: all users can see assets
            conditions.append(KnowledgeAsset.library_id == library_id)
        else:
            # Personal library: only owner can see
            conditions.append(KnowledgeAsset.library_id == library_id)
            conditions.append(KnowledgeAsset.user_id == current_user.id)
    else:
        conditions.append(KnowledgeAsset.user_id == current_user.id)

    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeAsset).where(*conditions)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(KnowledgeAsset).where(*conditions)
        .order_by(KnowledgeAsset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return KnowledgeAssetListResponse(items=items, total=total)
```

- [ ] **Step 2: Update delete_knowledge_asset to include OSS cleanup**

Replace the `delete_knowledge_asset` function (lines 251-278):

```python
@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """删除知识资产及其 ChromaDB 向量和 OSS 文件。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")

    # 删除 ChromaDB 中该文件的向量
    try:
        from app.services.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_asset_documents(asset_id=asset_id, library_id=asset.library_id)
    except Exception:
        pass

    # 删除 OSS 文件
    try:
        from app.services.oss_service import delete_file
        delete_file(asset.file_path)
    except Exception:
        pass

    await db.delete(asset)
    await db.commit()
    return None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/knowledge.py
git commit -m "feat(api): system library asset visibility + OSS cleanup on delete"
```

---

### Task 8: Adapt Celery tasks for OSS

**Files:**
- Modify: `backend/app/tasks.py`

- [ ] **Step 1: Update process_knowledge_asset to handle OSS URLs**

In `backend/app/tasks.py`, update the `KnowledgeAssetProcessor.process` method. Replace lines 107-109 (the file_path check):

```python
            file_path = Path(asset.file_path)
            if not file_path.exists():
                raise ValueError(f"文件不存在: {file_path}")
```

with:

```python
            file_path_str = asset.file_path
            temp_file = None

            try:
                # If file_path is an OSS URL, download to temp first
                if file_path_str.startswith("http"):
                    from app.services.oss_service import download_to_temp
                    temp_file = download_to_temp(file_path_str)
                    file_path = Path(temp_file)
                else:
                    file_path = Path(file_path_str)
                    if not file_path.exists():
                        raise ValueError(f"文件不存在: {file_path}")
```

Then, wrap the rest of the process method body (parsing + vectorization + db.commit) in this try block, and add a `finally` block at the end for cleanup:

```python
            finally:
                # Clean up temp file if downloaded from OSS (always runs, even on failure)
                if temp_file:
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
```

This ensures temp files are cleaned up on both success and failure paths (parsing failure, vectorization failure, etc.).

- [ ] **Step 2: Update cleanup_library to delete OSS files**

In `backend/app/tasks.py`, in the `cleanup_library` function, replace the local file deletion block (lines 343-348):

```python
        # 3. 删除本地文件
        for asset in assets:
            try:
                if asset.file_path and os.path.exists(asset.file_path):
                    os.remove(asset.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {asset.file_path}, {e}")
```

with:

```python
        # 3. 删除文件（OSS 或本地）
        from app.services.oss_service import delete_file as oss_delete
        for asset in assets:
            try:
                if asset.file_path:
                    if asset.file_path.startswith("http"):
                        oss_delete(asset.file_path)
                    elif os.path.exists(asset.file_path):
                        os.remove(asset.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {asset.file_path}, {e}")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/tasks.py
git commit -m "feat(tasks): adapt Celery tasks for OSS file paths"
```

---

### Task 9: Create Pinia knowledge store

**Files:**
- Create: `teacher-platform/src/stores/knowledge.js`

- [ ] **Step 1: Create the store**

Create `teacher-platform/src/stores/knowledge.js`:

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiRequest, authFetch } from '../api/http'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const libraries = ref([])
  const total = ref(0)
  const userTags = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchLibraries({ scope = 'all', search = '', tag = '', page = 1, pageSize = 50 } = {}) {
    loading.value = true
    error.value = null
    try {
      const params = new URLSearchParams()
      params.set('scope', scope)
      params.set('page', String(page))
      params.set('page_size', String(pageSize))
      if (search) params.set('search', search)
      if (tag) params.set('tag', tag)

      const data = await apiRequest(`/api/v1/libraries?${params}`)
      libraries.value = data.items
      total.value = data.total
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createLibrary({ name, description, tags }) {
    const body = JSON.stringify({ name, description, tags: tags || [] })
    const data = await apiRequest('/api/v1/libraries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    return data
  }

  async function updateLibrary(id, { name, description, tags }) {
    const payload = {}
    if (name !== undefined) payload.name = name
    if (description !== undefined) payload.description = description
    if (tags !== undefined) payload.tags = tags
    const body = JSON.stringify(payload)
    const data = await apiRequest(`/api/v1/libraries/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    return data
  }

  async function deleteLibrary(id) {
    await apiRequest(`/api/v1/libraries/${id}`, { method: 'DELETE' })
  }

  async function fetchUserTags() {
    try {
      const data = await apiRequest('/api/v1/libraries/tags')
      userTags.value = data
    } catch {
      userTags.value = []
    }
  }

  async function renameTag(oldName, newName) {
    const body = JSON.stringify({ old_name: oldName, new_name: newName })
    const data = await apiRequest('/api/v1/libraries/tags/rename', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    return data
  }

  async function uploadFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await authFetch('/api/v1/upload', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}))
      throw new Error(detail.detail || `上传失败 (${res.status})`)
    }
    return await res.json()
  }

  async function createAsset({ fileName, fileType, filePath, libraryId }) {
    const body = JSON.stringify({
      file_name: fileName,
      file_type: fileType,
      file_path: filePath,
      library_id: libraryId,
    })
    return await apiRequest('/api/v1/knowledge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
  }

  async function fetchAssets(libraryId, { page = 1, pageSize = 50 } = {}) {
    const params = new URLSearchParams()
    params.set('library_id', String(libraryId))
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    return await apiRequest(`/api/v1/knowledge?${params}`)
  }

  async function deleteAsset(assetId) {
    await apiRequest(`/api/v1/knowledge/${assetId}`, { method: 'DELETE' })
  }

  async function getAssetStatus(assetId) {
    return await apiRequest(`/api/v1/knowledge/${assetId}/status`)
  }

  return {
    libraries,
    total,
    userTags,
    loading,
    error,
    fetchLibraries,
    createLibrary,
    updateLibrary,
    deleteLibrary,
    fetchUserTags,
    renameTag,
    uploadFile,
    createAsset,
    fetchAssets,
    deleteAsset,
    getAssetStatus,
  }
})
```

- [ ] **Step 2: Verify store loads**

Run: `cd teacher-platform && npx vite build --mode development`
Expected: No import errors related to knowledge store

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/stores/knowledge.js
git commit -m "feat(store): add Pinia knowledge store with full API integration"
```

---

### Task 10: Rewire KnowledgeBase.vue — remove mock data, connect to API

**Files:**
- Modify: `teacher-platform/src/views/KnowledgeBase.vue`

- [ ] **Step 1: Replace the entire `<script setup>` section**

Replace the `<script setup>` block (lines 1-307) with:

```javascript
<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useKnowledgeStore } from '../stores/knowledge'

const router = useRouter()
const userStore = useUserStore()
const store = useKnowledgeStore()
const isAdmin = computed(() => userStore.userInfo?.is_admin === true)

// ---- Filter state ----
const activeFilter = ref('all')
const searchQuery = ref('')
const selectedTagFilter = ref('')

// ---- Fetch data ----
async function loadData() {
  await Promise.all([
    store.fetchLibraries({
      scope: activeFilter.value,
      search: searchQuery.value,
      tag: selectedTagFilter.value,
    }),
    store.fetchUserTags(),
  ])
}

onMounted(loadData)

// Debounced search
let searchTimer = null
watch(searchQuery, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    store.fetchLibraries({
      scope: activeFilter.value,
      search: searchQuery.value,
      tag: selectedTagFilter.value,
    })
  }, 300)
})

watch(activeFilter, () => {
  store.fetchLibraries({
    scope: activeFilter.value,
    search: searchQuery.value,
    tag: selectedTagFilter.value,
  })
})

watch(selectedTagFilter, () => {
  store.fetchLibraries({
    scope: activeFilter.value,
    search: searchQuery.value,
    tag: selectedTagFilter.value,
  })
})

// ---- Computed ----
const filteredResources = computed(() => {
  return store.libraries.map(lib => ({
    id: lib.id,
    type: lib.is_system ? 'system' : 'personal',
    title: lib.name,
    desc: lib.description || '',
    tags: lib.tags || [],
    time: lib.updated_at ? new Date(lib.updated_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) + '更新' : '',
    iconColor: lib.is_system ? '#2563EB' : '#F59E0B',
    fileCount: lib.asset_count || 0,
    charCount: 0,
    _raw: lib,
  }))
})

// ---- Tag filter dropdown ----
const showTagFilterDropdown = ref(false)

function selectTagFilter(tag) {
  selectedTagFilter.value = tag
  showTagFilterDropdown.value = false
}

// ---- More menu (card actions) ----
const activeMenuId = ref(null)

function toggleMenu(id, e) {
  e.stopPropagation()
  activeMenuId.value = activeMenuId.value === id ? null : id
}

function closeAllMenus() {
  activeMenuId.value = null
  showTagFilterDropdown.value = false
}

// ---- Tag Popover ----
const activeTagPopoverId = ref(null)
const tagSearchQuery = ref('')

function toggleTagPopover(id, e) {
  e.stopPropagation()
  if (activeTagPopoverId.value === id) {
    activeTagPopoverId.value = null
  } else {
    activeTagPopoverId.value = id
    tagSearchQuery.value = ''
  }
}

const filteredTagOptions = computed(() => {
  const q = tagSearchQuery.value.trim().toLowerCase()
  if (!q) return store.userTags
  return store.userTags.filter(t => t.toLowerCase().includes(q))
})

async function addTagToResource(resource, tag) {
  const currentTags = [...(resource.tags || [])]
  if (currentTags.includes(tag)) return
  currentTags.push(tag)
  await store.updateLibrary(resource.id, { tags: currentTags })
  await loadData()
}

async function createAndAddTag(resource) {
  const name = tagSearchQuery.value.trim()
  if (!name) return
  const currentTags = [...(resource.tags || [])]
  if (!currentTags.includes(name)) currentTags.push(name)
  await store.updateLibrary(resource.id, { tags: currentTags })
  tagSearchQuery.value = ''
  await loadData()
}

async function removeTagFromResource(resource, tag) {
  const currentTags = (resource.tags || []).filter(t => t !== tag)
  await store.updateLibrary(resource.id, { tags: currentTags })
  await loadData()
}

// ---- Tag Management Modal ----
const showTagManager = ref(false)
const tagManagerSearch = ref('')
const editingTag = ref(null)
const editingTagName = ref('')

const filteredManagerTags = computed(() => {
  const q = tagManagerSearch.value.trim().toLowerCase()
  if (!q) return store.userTags
  return store.userTags.filter(t => t.toLowerCase().includes(q))
})

function openTagManager() {
  activeTagPopoverId.value = null
  showTagManager.value = true
  tagManagerSearch.value = ''
}

function startRenameTag(tag) {
  editingTag.value = tag
  editingTagName.value = tag
}

async function confirmRenameTag() {
  const oldName = editingTag.value
  const newName = editingTagName.value.trim()
  editingTag.value = null
  if (!newName || newName === oldName) return
  await store.renameTag(oldName, newName)
  if (selectedTagFilter.value === oldName) selectedTagFilter.value = newName
  await loadData()
}

async function deleteGlobalTag(tag) {
  // 删除标签：从该用户所有包含此标签的库中移除
  // 遍历当前列表中含有该标签的库，逐个更新
  const libsWithTag = store.libraries.filter(lib => (lib.tags || []).includes(tag))
  for (const lib of libsWithTag) {
    const newTags = lib.tags.filter(t => t !== tag)
    await store.updateLibrary(lib.id, { tags: newTags })
  }
  if (selectedTagFilter.value === tag) selectedTagFilter.value = ''
  await loadData()
}

function createTagFromManager() {
  // 标签只有在添加到具体知识库时才会创建，管理页面无需单独创建
  // 此函数保留为空操作以避免模板报错
  tagManagerSearch.value = ''
}

// ---- Add/Edit Modal ----
const showAddModal = ref(false)
const addForm = ref({ title: '', desc: '', tags: '' })
const isEditMode = ref(false)
const editingId = ref(null)

function openAddModal() {
  isEditMode.value = false
  editingId.value = null
  addForm.value = { title: '', desc: '', tags: '' }
  showAddModal.value = true
}

function openEditModal(resource, e) {
  if (e) e.stopPropagation()
  activeMenuId.value = null
  isEditMode.value = true
  editingId.value = resource.id
  addForm.value = {
    title: resource.title,
    desc: resource.desc || '',
    tags: (resource.tags || []).join(', ')
  }
  showAddModal.value = true
}

async function submitAdd() {
  const { title, desc, tags } = addForm.value
  if (!title.trim()) return
  const parsedTags = tags ? tags.split(/[,，\s]+/).filter(Boolean) : []

  try {
    if (isEditMode.value && editingId.value != null) {
      await store.updateLibrary(editingId.value, {
        name: title.trim(),
        description: desc.trim() || null,
        tags: parsedTags,
      })
    } else {
      await store.createLibrary({
        name: title.trim(),
        description: desc.trim() || null,
        tags: parsedTags,
      })
    }
    showAddModal.value = false
    await loadData()
  } catch (e) {
    alert(e.message || '操作失败')
  }
}

async function deleteResource(resource, e) {
  if (e) e.stopPropagation()
  activeMenuId.value = null
  if (!confirm(`确定要删除知识库「${resource.title}」吗？`)) return
  try {
    await store.deleteLibrary(resource.id)
    await loadData()
  } catch (e) {
    alert(e.message || '删除失败')
  }
}

function openDetail(resource) {
  router.push({
    path: `/knowledge-base/${resource.id}`,
    query: { title: resource.title }
  })
}

// ---- Click outside handler ----
function handleDocClick() {
  if (activeMenuId.value !== null) activeMenuId.value = null
  if (activeTagPopoverId.value !== null) activeTagPopoverId.value = null
  if (showTagFilterDropdown.value) showTagFilterDropdown.value = false
}

onMounted(() => document.addEventListener('click', handleDocClick))
onBeforeUnmount(() => document.removeEventListener('click', handleDocClick))

function getIconLetter(title) {
  return (title || 'K').charAt(0).toUpperCase()
}
</script>
```

- [ ] **Step 2: Update template — remove file input from Add/Edit modal**

In the template, remove the file-related lines from the Add/Edit Modal section. Replace the modal-box content (lines 508-536) — specifically remove the file select button and the `addTarget` radio since libraries are always personal for normal users:

Find this block in the template:
```html
            <label>选择本地文件（选填）</label>
            <input
              ref="addModalFileInputRef"
              type="file"
              multiple
              class="file-input-hidden"
              @change="onAddModalFileChange"
            />
            <button type="button" class="select-file-btn" @click="triggerAddModalFileSelect">选择文件</button>
            <span v-if="addModalFiles.length" class="selected-files">已选 {{ addModalFiles.length }} 个文件</span>
```

And remove it entirely (file upload is done in the detail page, not during library creation).

- [ ] **Step 3: Verify the page loads without errors**

Run: `cd teacher-platform && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/views/KnowledgeBase.vue
git commit -m "feat(frontend): replace KnowledgeBase mock data with real API calls"
```

---

### Task 11: Rewire KnowledgeDetail.vue — remove mock data, connect to API

**Files:**
- Modify: `teacher-platform/src/views/KnowledgeDetail.vue`

- [ ] **Step 1: Replace the entire `<script setup>` section**

Replace the `<script setup>` block (lines 1-82) with:

```javascript
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useKnowledgeStore } from '../stores/knowledge'

const route = useRoute()
const router = useRouter()
const store = useKnowledgeStore()

const libraryId = computed(() => Number(route.params.id))
const kbTitle = computed(() => route.query.title || '知识库详情')

const allDocs = ref([])
const searchText = ref('')
const uploading = ref(false)

const docs = computed(() =>
  allDocs.value.filter(d =>
    !searchText.value ||
    d.name.toLowerCase().includes(searchText.value.toLowerCase())
  )
)

const fileInputRef = ref(null)

async function loadDocs() {
  try {
    const data = await store.fetchAssets(libraryId.value)
    allDocs.value = data.items.map(a => ({
      id: a.id,
      name: a.file_name,
      words: a.chunk_count || 0,
      uploads: a.image_count || 0,
      time: new Date(a.created_at).toLocaleString('zh-CN'),
      status: a.vector_status,
      filePath: a.file_path,
    }))
  } catch {
    allDocs.value = []
  }
}

onMounted(loadDocs)

// Poll for pending/processing assets
let pollTimer = null

function startPolling() {
  pollTimer = setInterval(async () => {
    const pending = allDocs.value.filter(d => d.status === 'pending' || d.status === 'processing')
    if (!pending.length) return
    for (const doc of pending) {
      try {
        const st = await store.getAssetStatus(doc.id)
        doc.status = st.vector_status
        doc.words = st.chunk_count || 0
        doc.uploads = st.image_count || 0
      } catch { /* ignore */ }
    }
  }, 5000)
}

onMounted(startPolling)
onBeforeUnmount(() => clearInterval(pollTimer))

function goBack() {
  router.push('/knowledge-base')
}

function triggerAddFile() {
  fileInputRef.value?.click()
}

async function handleFilesSelected(e) {
  const files = e.target.files
  if (!files || !files.length) return
  e.target.value = ''

  uploading.value = true
  try {
    for (const file of Array.from(files)) {
      // Step 1: Upload to OSS
      const uploadResult = await store.uploadFile(file)
      // Step 2: Create knowledge asset
      await store.createAsset({
        fileName: uploadResult.file_name,
        fileType: uploadResult.file_type,
        filePath: uploadResult.url,
        libraryId: libraryId.value,
      })
    }
    await loadDocs()
  } catch (err) {
    alert(err.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function deleteDoc(doc) {
  if (!confirm(`确定要删除文档「${doc.name}」吗？`)) return
  try {
    await store.deleteAsset(doc.id)
    allDocs.value = allDocs.value.filter(d => d.id !== doc.id)
  } catch (err) {
    alert(err.message || '删除失败')
  }
}

function downloadDoc(doc) {
  if (!doc.filePath) {
    alert('文件路径不可用')
    return
  }
  window.open(doc.filePath, '_blank')
}
</script>
```

- [ ] **Step 2: Update the template**

Replace the template section to match the new data structure. Key changes:

1. Replace `doc.uploads` column header from `引用数` to `图片数`
2. Update status display to show vector_status
3. Remove the `renameDoc` button (not implemented in backend)
4. Add uploading indicator

Replace the template (lines 84-135):

```html
<template>
  <div class="kb-detail-page">
    <div class="kb-detail-header">
      <div class="kb-detail-title-wrap">
        <button type="button" class="back-btn" @click="goBack">← 返回知识库</button>
        <h2 class="kb-detail-title">{{ kbTitle }}</h2>
      </div>
      <div class="kb-detail-actions">
          <input v-model="searchText" class="search-input" type="text" placeholder="搜索文档" />
          <button type="button" class="primary-btn" :disabled="uploading" @click="triggerAddFile">
            {{ uploading ? '上传中...' : '添加文件' }}
          </button>
          <input
            ref="fileInputRef"
            type="file"
            class="hidden-file-input"
            multiple
            accept=".pdf,.doc,.docx,.mp4,.jpg,.jpeg,.png"
            @change="handleFilesSelected"
          />
      </div>
    </div>

    <div class="kb-detail-table">
      <div class="kb-table-header">
        <div class="col col-index">#</div>
        <div class="col col-name">名称</div>
        <div class="col col-words">文本块数</div>
        <div class="col col-calls">图片数</div>
        <div class="col col-time">上传时间</div>
        <div class="col col-status">状态</div>
        <div class="col col-ops">操作</div>
      </div>
      <div v-for="(doc, idx) in docs" :key="doc.id" class="kb-table-row">
        <div class="col col-index">{{ idx + 1 }}</div>
        <div class="col col-name">
          <span class="file-icon">📄</span>
          <span class="file-name">{{ doc.name }}</span>
        </div>
        <div class="col col-words">{{ doc.words }}</div>
        <div class="col col-calls">{{ doc.uploads }}</div>
        <div class="col col-time">{{ doc.time }}</div>
        <div class="col col-status">
          <span class="status-dot" :class="doc.status"></span>
          <span>{{ { pending: '等待处理', processing: '处理中', completed: '可用', failed: '失败' }[doc.status] || doc.status }}</span>
        </div>
        <div class="col col-ops">
          <button type="button" class="link-btn" @click="downloadDoc(doc)">下载</button>
          <button type="button" class="link-btn danger" @click="deleteDoc(doc)">删除</button>
        </div>
      </div>
      <div v-if="docs.length === 0" class="kb-empty-row">
        <span>暂无文档，点击"添加文件"上传</span>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Update styles — add status dot variants and empty row**

Add to the `<style scoped>` section:

```css
.status-dot.completed {
  background: #22c55e;
}
.status-dot.processing {
  background: #f59e0b;
}
.status-dot.pending {
  background: #94a3b8;
}
.status-dot.failed {
  background: #ef4444;
}
.kb-empty-row {
  text-align: center;
  padding: 40px 16px;
  color: #94a3b8;
  font-size: 14px;
}
```

- [ ] **Step 4: Verify build**

Run: `cd teacher-platform && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add teacher-platform/src/views/KnowledgeDetail.vue
git commit -m "feat(frontend): replace KnowledgeDetail mock data with real API + OSS upload"
```

---

### Task 12: End-to-end verification

- [ ] **Step 1: Start backend**

Run: `cd backend && python run.py`
Expected: FastAPI starts without errors, Swagger docs available at `/doc.html`

- [ ] **Step 2: Verify new endpoints in Swagger**

Open `http://localhost:8000/doc.html` and verify these endpoints exist:
- `POST /api/v1/upload`
- `GET /api/v1/libraries?scope=all`
- `GET /api/v1/libraries/tags`
- `PATCH /api/v1/libraries/tags/rename`
- `PATCH /api/v1/libraries/{library_id}` (with tags field)

- [ ] **Step 3: Start frontend**

Run: `cd teacher-platform && npm run dev`
Expected: Vite dev server starts

- [ ] **Step 4: Verify knowledge base list page**

Navigate to `/knowledge-base`:
- Page loads without errors
- Empty state shows if no libraries exist
- "创建知识库" button opens modal
- Creating a library adds it to the list
- Scope filter (全部/系统/个人) works
- Search filters by name/description
- Tag filter dropdown shows user's tags

- [ ] **Step 5: Verify knowledge detail page**

Click a library card → navigates to detail page:
- "添加文件" → file picker → upload to OSS → document appears in table
- Status shows "等待处理" → "处理中" → "可用" (if Celery running)
- Delete button removes document
- Download button opens OSS URL

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete knowledge base frontend-backend integration with OSS"
```
