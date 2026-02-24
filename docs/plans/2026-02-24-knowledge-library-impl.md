# Knowledge Library System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为教学平台增加多知识库管理系统，支持用户创建多个隔离知识库、管理员系统级公开库、多库联合检索。

**Architecture:** 单 ChromaDB collection + metadata `library_id` 字段实现命名空间隔离；新增 `KnowledgeLibrary` 数据模型；`vector_status` 从 boolean 升级为枚举字符串；删除知识库走软删除 + Celery 异步清理。

**Tech Stack:** FastAPI, SQLAlchemy async, ChromaDB, Celery, Pydantic v2, PostgreSQL

---

## 前置说明

- 所有命令在 `backend/` 目录下执行
- 现有 `knowledge_base` ChromaDB collection 无需迁移，旧文档 metadata 缺少 `library_id` 时检索会忽略（兼容）
- `main.py:32` 有一处语法错误（`lifespan=lifespan` 后缺逗号），在 Task 1 中顺手修复

---

## Task 1: 修复 main.py 语法错误 + 添加 VectorStatus 枚举

**Files:**
- Modify: `backend/app/main.py:28-34`
- Modify: `backend/app/models/enums.py`

**Step 1: 修复 main.py 语法错误**

`backend/app/main.py` 第 32 行 `lifespan=lifespan` 后缺少逗号，修改为：

```python
app = FastAPI(
    title="多模态 AI 互动式教学智能体",
    description="服务外包大赛 A04 赛题后端 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/doc.html",
    redoc_url="/redoc.html"
)
```

**Step 2: 在 `enums.py` 末尾添加 VectorStatus 枚举**

```python
class VectorStatus(str, Enum):
    """向量化状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

**Step 3: 验证语法无误**

```bash
python -c "from app.models.enums import VectorStatus; print(VectorStatus.COMPLETED)"
```

Expected: `VectorStatus.completed`

**Step 4: Commit**

```bash
git add backend/app/main.py backend/app/models/enums.py
git commit -m "feat: add VectorStatus enum, fix main.py syntax error"
```

---

## Task 2: 新建 KnowledgeLibrary 模型 + 修改 User / KnowledgeAsset 模型

**Files:**
- Create: `backend/app/models/knowledge_library.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/knowledge_asset.py`

**Step 1: 新建 `knowledge_library.py`**

```python
"""
知识库模型
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, Text
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
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

**Step 2: 修改 `user.py`，添加 `is_admin` 字段和关联**

在 `full_name` 字段后添加：
```python
is_admin: Mapped[bool] = mapped_column(
    Boolean,
    default=False,
    nullable=False,
    comment="是否为系统管理员"
)
```

在 `knowledge_assets` 关联后添加：
```python
knowledge_libraries: Mapped[list["KnowledgeLibrary"]] = relationship(
    "KnowledgeLibrary",
    back_populates="owner",
    cascade="all, delete-orphan"
)
```

**Step 3: 修改 `knowledge_asset.py`**

添加 `library_id` 外键（`user_id` 字段后）：
```python
library_id: Mapped[int | None] = mapped_column(
    Integer,
    ForeignKey("knowledge_libraries.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    comment="所属知识库"
)
```

将 `vector_status` 从 `bool` 改为字符串枚举：
```python
# 删除原来的 bool 定义，替换为：
vector_status: Mapped[str] = mapped_column(
    String(20),
    default="pending",
    nullable=False,
    comment="向量化状态: pending/processing/completed/failed"
)
```

在 `user` 关联后添加：
```python
library: Mapped["KnowledgeLibrary | None"] = relationship(
    "KnowledgeLibrary",
    back_populates="assets"
)
```

**Step 4: 验证模型导入无误**

```bash
python -c "from app.models.knowledge_library import KnowledgeLibrary; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add KnowledgeLibrary model, is_admin to User, library_id to KnowledgeAsset"
```

---

## Task 3: 更新 models/__init__.py 导出

**Files:**
- Modify: `backend/app/models/__init__.py`

**Step 1: 更新 `__init__.py`**

```python
"""
数据库模型导出
"""
from app.models.user import User
from app.models.courseware import Courseware
from app.models.chat_history import ChatHistory
from app.models.knowledge_library import KnowledgeLibrary
from app.models.knowledge_asset import KnowledgeAsset
from app.models.enums import (
    CoursewareType,
    CoursewareStatus,
    ChatRole,
    FileType,
    VectorStatus,
)

__all__ = [
    "User",
    "Courseware",
    "ChatHistory",
    "KnowledgeLibrary",
    "KnowledgeAsset",
    "CoursewareType",
    "CoursewareStatus",
    "ChatRole",
    "FileType",
    "VectorStatus",
]
```

**Step 2: 验证**

```bash
python -c "from app.models import KnowledgeLibrary, VectorStatus; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/models/__init__.py
git commit -m "feat: export KnowledgeLibrary and VectorStatus from models"
```

---

## Task 4: 数据库表结构更新

**Step 1: 让 `init_db` 创建新表**

项目使用 `Base.metadata.create_all` 自动建表。新增的 `knowledge_libraries` 表会在应用启动时自动创建。

对于已存在的 `users` 和 `knowledge_assets` 表需要手动 ALTER，在 PostgreSQL 执行：

```sql
-- 添加 is_admin 到 users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- 添加 library_id 到 knowledge_assets
ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS library_id INTEGER REFERENCES knowledge_libraries(id) ON DELETE SET NULL;

-- 修改 vector_status 从 bool 改为 varchar
ALTER TABLE knowledge_assets ALTER COLUMN vector_status TYPE VARCHAR(20) USING CASE WHEN vector_status THEN 'completed' ELSE 'pending' END;
ALTER TABLE knowledge_assets ALTER COLUMN vector_status SET DEFAULT 'pending';
```

**Step 2: 执行迁移**

连接到数据库执行上述 SQL，或通过 Alembic：

```bash
alembic revision --autogenerate -m "add knowledge_library, is_admin, library_id, vector_status_string"
alembic upgrade head
```

**Step 3: 验证**

```bash
python -c "
import asyncio
from app.core.database import init_db
asyncio.run(init_db())
print('DB init OK')
"
```

Expected: `DB init OK`

**Step 4: Commit（如果用了 Alembic）**

```bash
git add alembic/versions/
git commit -m "feat: db migration for knowledge library system"
```

---

## Task 5: 添加管理员依赖 + 更新 auth.py

**Files:**
- Modify: `backend/app/core/auth.py`

**Step 1: 在文件末尾添加 `get_admin_user` 依赖和类型别名**

```python
async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """要求当前用户为管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# 类型别名
AdminUser = Annotated[User, Depends(get_admin_user)]
```

**Step 2: 验证**

```bash
python -c "from app.core.auth import AdminUser; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/core/auth.py
git commit -m "feat: add AdminUser dependency for admin-only endpoints"
```

---

## Task 6: 新建 schemas/library.py + 更新 schemas/knowledge.py

**Files:**
- Create: `backend/app/schemas/library.py`
- Modify: `backend/app/schemas/knowledge.py`

**Step 1: 新建 `schemas/library.py`**

```python
"""
知识库相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class KnowledgeLibraryCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_system: bool = False
    is_public: bool = False


class KnowledgeLibraryUpdate(BaseModel):
    """更新知识库请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool | None = None


class KnowledgeLibraryResponse(BaseModel):
    """知识库响应"""
    id: int
    owner_id: int
    name: str
    description: str | None
    is_system: bool
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeLibraryListResponse(BaseModel):
    """知识库列表响应"""
    items: list[KnowledgeLibraryResponse]
    total: int
```

**Step 2: 更新 `schemas/knowledge.py`**

- `KnowledgeAssetCreate` 添加 `library_id` 字段
- `KnowledgeAssetUpdate` 将 `vector_status` 类型改为 `str | None`
- `KnowledgeAssetResponse` 添加 `library_id`，`vector_status` 改为 `str`
- 新增 `KnowledgeAssetStatusResponse`

```python
"""
知识资产相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.enums import FileType


class KnowledgeAssetCreate(BaseModel):
    """创建知识资产请求"""
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: FileType
    file_path: str = Field(..., max_length=500)
    library_id: int


class KnowledgeAssetUpdate(BaseModel):
    """更新知识资产请求"""
    vector_status: str | None = None


class KnowledgeAssetResponse(BaseModel):
    """知识资产响应"""
    id: int
    user_id: int
    library_id: int | None
    file_name: str
    file_type: FileType
    file_path: str
    vector_status: str
    chunk_count: int
    image_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeAssetStatusResponse(BaseModel):
    """知识资产状态响应（轻量）"""
    id: int
    vector_status: str
    chunk_count: int
    image_count: int

    model_config = {"from_attributes": True}


class KnowledgeAssetListResponse(BaseModel):
    """知识资产列表响应"""
    items: list[KnowledgeAssetResponse]
    total: int
```

**Step 3: 验证**

```bash
python -c "from app.schemas.library import KnowledgeLibraryCreate; from app.schemas.knowledge import KnowledgeAssetStatusResponse; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add library schemas, update knowledge schemas for library_id and string vector_status"
```

---

## Task 7: 新建 api/libraries.py

**Files:**
- Create: `backend/app/api/libraries.py`

**Step 1: 创建 `api/libraries.py`**

```python
"""
知识库路由
"""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.auth import CurrentUser, AdminUser
from app.models.knowledge_library import KnowledgeLibrary
from app.schemas.library import (
    KnowledgeLibraryCreate,
    KnowledgeLibraryUpdate,
    KnowledgeLibraryResponse,
    KnowledgeLibraryListResponse,
)
from app.tasks import cleanup_library

router = APIRouter(prefix="/libraries", tags=["知识库"])


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
        is_system=is_system,
        is_public=is_public,
    )
    db.add(library)
    await db.commit()
    await db.refresh(library)
    return library


@router.get("", response_model=KnowledgeLibraryListResponse)
async def list_libraries(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Literal["personal", "system"] = Query("personal"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    列出知识库。
    scope=personal: 当前用户自己创建的库
    scope=system: 所有公开的系统级库
    """
    if scope == "personal":
        condition = (
            KnowledgeLibrary.owner_id == current_user.id,
            KnowledgeLibrary.is_deleted == False,
        )
    else:  # system
        condition = (
            KnowledgeLibrary.is_system == True,
            KnowledgeLibrary.is_public == True,
            KnowledgeLibrary.is_deleted == False,
        )

    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeLibrary).where(*condition)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(KnowledgeLibrary).where(*condition)
        .order_by(KnowledgeLibrary.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return KnowledgeLibraryListResponse(items=items, total=total)


@router.patch("/{library_id}", response_model=KnowledgeLibraryResponse)
async def update_library(
    library_id: int,
    data: KnowledgeLibraryUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """更新知识库名称/描述。is_public 仅管理员可修改。"""
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
    if data.is_public is not None:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可修改公开状态")
        library.is_public = data.is_public

    await db.commit()
    await db.refresh(library)
    return library


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

    # 软删除：立即对前端透明，后台异步清理
    library.is_deleted = True
    await db.commit()

    # 触发 Celery 异步清理
    cleanup_library.delay(library_id)

    return None
```

**Step 2: 验证导入**

```bash
python -c "from app.api.libraries import router; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/api/libraries.py
git commit -m "feat: add knowledge library CRUD API with soft delete"
```

---

## Task 8: 更新 api/knowledge.py

**Files:**
- Modify: `backend/app/api/knowledge.py`

**Step 1: 重写 `knowledge.py`**

主要变更：
- 创建资产时校验 `library_id` 归属
- 列表支持按 `library_id` 过滤
- 新增 `GET /{id}/status` 轻量端点
- 删除时同步删除 ChromaDB 向量
- `vector_status` 统一使用字符串

```python
"""
知识资产路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.auth import CurrentUser
from app.models.knowledge_asset import KnowledgeAsset
from app.models.knowledge_library import KnowledgeLibrary
from app.schemas.knowledge import (
    KnowledgeAssetCreate,
    KnowledgeAssetResponse,
    KnowledgeAssetStatusResponse,
    KnowledgeAssetListResponse,
)
from app.tasks import process_knowledge_asset

router = APIRouter(prefix="/knowledge", tags=["知识资产"])


async def _get_owned_library(library_id: int, user_id: int, db: AsyncSession) -> KnowledgeLibrary:
    """校验用户拥有该知识库"""
    result = await db.execute(
        select(KnowledgeLibrary).where(
            KnowledgeLibrary.id == library_id,
            KnowledgeLibrary.owner_id == user_id,
            KnowledgeLibrary.is_deleted == False,
        )
    )
    library = result.scalar_one_or_none()
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在或无权限")
    return library


@router.post("", response_model=KnowledgeAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_asset(
    data: KnowledgeAssetCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """上传知识资产，立即返回，Celery 后台向量化。"""
    # 校验 library 归属
    await _get_owned_library(data.library_id, current_user.id, db)

    asset = KnowledgeAsset(
        user_id=current_user.id,
        library_id=data.library_id,
        file_name=data.file_name,
        file_type=data.file_type,
        file_path=data.file_path,
        vector_status="pending"
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    # 触发 Celery 后台任务
    process_knowledge_asset.delay(asset.id, current_user.id, data.library_id)

    return asset


@router.get("", response_model=KnowledgeAssetListResponse)
async def list_knowledge_assets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    library_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """列出知识资产，可按知识库过滤。"""
    conditions = [KnowledgeAsset.user_id == current_user.id]
    if library_id is not None:
        conditions.append(KnowledgeAsset.library_id == library_id)

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


@router.get("/{asset_id}/status", response_model=KnowledgeAssetStatusResponse)
async def get_asset_status(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """轻量状态查询，前端轮询用。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")
    return asset


@router.get("/{asset_id}", response_model=KnowledgeAssetResponse)
async def get_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取知识资产详情。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_asset(
    asset_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """删除知识资产及其 ChromaDB 向量。"""
    result = await db.execute(
        select(KnowledgeAsset).where(
            KnowledgeAsset.id == asset_id,
            KnowledgeAsset.user_id == current_user.id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识资产不存在")

    # 删除 ChromaDB 中该文件的向量（按 source 元数据过滤）
    try:
        from app.services.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_asset_documents(asset_id=asset_id, library_id=asset.library_id)
    except Exception:
        pass  # 向量删除失败不阻断 DB 删除

    await db.delete(asset)
    await db.commit()
    return None
```

**Step 2: 验证导入**

```bash
python -c "from app.api.knowledge import router; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/api/knowledge.py
git commit -m "feat: update knowledge API with library_id, status endpoint, vector cleanup on delete"
```

---

## Task 9: 注册 libraries 路由

**Files:**
- Modify: `backend/app/api/__init__.py`

**Step 1: 更新 `__init__.py`**

```python
"""
API 路由导出
"""
from fastapi import APIRouter
from app.api import auth, courseware, chat, knowledge, libraries

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(courseware.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(libraries.router)

__all__ = ["api_router"]
```

**Step 2: 验证应用启动**

```bash
python -c "from app.main import app; print('Routes:', [r.path for r in app.routes])"
```

Expected: 输出包含 `/api/v1/libraries`

**Step 3: Commit**

```bash
git add backend/app/api/__init__.py
git commit -m "feat: register libraries router"
```

---

## Task 10: 更新 VectorStore — 支持 library_id + 按库删除

**Files:**
- Modify: `backend/app/services/rag/vector_store.py`

**Step 1: 修改 `add_documents`，metadata 加入 `library_id`**

将 `add_documents` 方法签名改为：

```python
def add_documents(self, chunks: list[ParsedChunk], user_id: int, library_id: int | None = None) -> int:
```

在构建 metadata 时增加：
```python
metadata = {
    **chunk.metadata,
    "user_id": user_id,
    "chunk_index": i,
}
if library_id is not None:
    metadata["library_id"] = library_id
```

**Step 2: 修改 `similarity_search`，支持 library_ids 过滤**

```python
def similarity_search(
    self,
    query: str,
    user_id: int,
    k: int = 4,
    library_ids: list[int] | None = None
) -> list[Document]:
    if library_ids:
        if len(library_ids) == 1:
            filter_dict = {"library_id": library_ids[0]}
        else:
            filter_dict = {"library_id": {"$in": library_ids}}
    else:
        filter_dict = {"user_id": user_id}

    results = self.vectorstore.similarity_search(
        query=query,
        k=k,
        filter=filter_dict
    )
    logger.info(f"相似性搜索: query={query}, library_ids={library_ids}, 结果数={len(results)}")
    return results
```

**Step 3: 新增 `delete_library_documents` 和 `delete_asset_documents` 方法**

```python
def delete_library_documents(self, library_id: int) -> bool:
    """删除某知识库的所有向量"""
    try:
        self.vectorstore._collection.delete(where={"library_id": library_id})
        logger.info(f"删除知识库 {library_id} 的所有向量")
        return True
    except Exception as e:
        logger.error(f"删除知识库向量失败: {e}")
        return False

def delete_asset_documents(self, asset_id: int, library_id: int | None = None) -> bool:
    """删除某文件的向量（按 source 元数据过滤）"""
    try:
        where = {"asset_id": asset_id} if library_id is None else {
            "$and": [{"asset_id": asset_id}, {"library_id": library_id}]
        }
        self.vectorstore._collection.delete(where=where)
        logger.info(f"删除资产 {asset_id} 的向量")
        return True
    except Exception as e:
        logger.error(f"删除资产向量失败: {e}")
        return False
```

> **注意**：`delete_asset_documents` 依赖 metadata 中有 `asset_id` 字段。在 Task 12 的 `tasks.py` 更新中，写入向量时需同步加入 `asset_id` 字段。

**Step 4: 验证**

```bash
python -c "from app.services.rag.vector_store import VectorStore; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/services/rag/vector_store.py
git commit -m "feat: vectorstore supports library_id metadata, delete by library/asset"
```

---

## Task 11: 更新 HybridRetriever — library_id 键 + 多库检索

**Files:**
- Modify: `backend/app/services/rag/hybrid_retriever.py`

**Step 1: 将 `BM25Index._indices` 的 key 从 `user_id` 改为 `library_id`**

将所有 `user_id` 参数改为 `library_id`（仅在 `BM25Index` 类内部）：

```python
class BM25Index:
    def __init__(self):
        # key = library_id
        self._indices: dict[int, dict] = {}

    def build_index(self, library_id: int, documents: list[Document]):
        ...
        self._indices[library_id] = {...}

    def search(self, library_id: int, query: str, top_k: int = 10):
        if library_id not in self._indices:
            return []
        ...

    def clear_library_index(self, library_id: int):
        if library_id in self._indices:
            del self._indices[library_id]
```

**Step 2: 修改 `HybridRetriever.search`，支持 `library_ids` 列表**

```python
def search(
    self,
    query: str,
    user_id: int,
    k: int = 10,
    library_ids: list[int] | None = None,
    vector_k: int = None,
    bm25_k: int = None
) -> list[Document]:
    vector_k = vector_k or k * 2
    bm25_k = bm25_k or k * 2

    # 1. 向量检索（支持多库 $in 过滤）
    vector_results = self.vector_store.similarity_search(
        query=query,
        user_id=user_id,
        k=vector_k,
        library_ids=library_ids
    )

    # 2. BM25 检索（对每个 library 分别检索，合并）
    bm25_results = []
    if library_ids:
        for lib_id in library_ids:
            bm25_results.extend(
                self.bm25_index.search(library_id=lib_id, query=query, top_k=bm25_k)
            )
    else:
        bm25_results = self.bm25_index.search(library_id=user_id, query=query, top_k=bm25_k)

    # 3. 融合
    if self.fusion_method == "rrf":
        return self._rrf_fusion(vector_results, bm25_results, k)
    else:
        return self._weighted_fusion(vector_results, bm25_results, k)
```

**Step 3: 修改 `build_bm25_index` 和 `add_documents` 使用 `library_id`**

```python
def build_bm25_index(self, library_id: int, documents: list[Document]):
    self._user_docs[library_id] = documents
    self.bm25_index.build_index(library_id, documents)

def add_documents(self, chunks: list, user_id: int, library_id: int | None = None, document_ids: list[str] = None):
    key = library_id if library_id is not None else user_id
    ...
    self.bm25_index.build_index(key, self._user_docs[key])
```

**Step 4: 验证**

```bash
python -c "from app.services.rag.hybrid_retriever import HybridRetriever; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add backend/app/services/rag/hybrid_retriever.py
git commit -m "feat: hybrid retriever supports library_ids multi-library search"
```

---

## Task 12: 更新 tasks.py

**Files:**
- Modify: `backend/app/tasks.py`

**变更清单：**
1. 修复缺失的 `split_documents_semantic` 导入
2. `process_knowledge_asset` 接受 `library_id` 参数，写入 metadata
3. `vector_status` 改用字符串值（`"processing"` / `"completed"` / `"failed"`）
4. 新增 `cleanup_library` Celery 任务

**Step 1: 修复导入**

在文件顶部 import 区块添加：
```python
from app.services.rag.text_splitter import split_documents_semantic, split_documents
```
并删除原有的 `from app.services.rag.text_splitter import split_documents`。

**Step 2: 修改 `KnowledgeAssetProcessor.process` 接受 `library_id`**

```python
def process(self, asset_id: int, user_id: int, library_id: int | None = None) -> dict:
```

在 `vectorstore.add_documents` 调用处传入 `library_id` 和 `asset_id`：
```python
doc_count = vectorstore.add_documents(
    split_chunks,
    user_id=user_id,
    library_id=library_id,
    asset_id=asset_id      # 新增，供按资产删除用
)
```

将 `vector_status=True` 改为 `vector_status="completed"`：
```python
.values(
    vector_status="completed",
    chunk_count=len(split_chunks),
    image_count=image_count
)
```

**Step 3: 修改 `process_knowledge_asset` Celery 任务签名**

```python
@celery_app.task(...)
def process_knowledge_asset(self, asset_id: int, user_id: int, library_id: int | None = None):
    ...
    # 在失败处理中：
    db.execute(
        update(KnowledgeAsset)
        .where(KnowledgeAsset.id == asset_id)
        .values(vector_status="failed")  # 原来是 False
    )
```

在 `process` 方法开头添加状态更新为 `"processing"`：
```python
db.execute(
    update(KnowledgeAsset)
    .where(KnowledgeAsset.id == asset_id)
    .values(vector_status="processing")
)
db.commit()
```

**Step 4: 新增 `cleanup_library` 任务**

```python
@celery_app.task(
    bind=True,
    name="app.tasks.cleanup_library",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5}
)
def cleanup_library(self, library_id: int):
    """
    异步清理知识库：删除向量 + 物理文件 + DB 记录
    软删除之后由此任务执行实际清理
    """
    from app.models.knowledge_library import KnowledgeLibrary
    from app.models.knowledge_asset import KnowledgeAsset
    from app.services.rag.vector_store import VectorStore
    import os

    db = get_sync_db()
    try:
        # 1. 删除 ChromaDB 向量
        vs = VectorStore()
        vs.delete_library_documents(library_id)

        # 2. 获取所有关联文件路径
        result = db.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.library_id == library_id)
        )
        assets = result.scalars().all()

        # 3. 删除本地文件
        for asset in assets:
            try:
                if asset.file_path and os.path.exists(asset.file_path):
                    os.remove(asset.file_path)
            except Exception as e:
                logger.warning(f"删除文件失败: {asset.file_path}, {e}")

        # 4. 物理删除 DB 记录（KnowledgeAsset 级联删除，再删 Library）
        db.execute(
            delete(KnowledgeAsset).where(KnowledgeAsset.library_id == library_id)
        )
        db.execute(
            delete(KnowledgeLibrary).where(KnowledgeLibrary.id == library_id)
        )
        db.commit()

        logger.info(f"知识库 {library_id} 清理完成")
        return {"status": "success", "library_id": library_id}

    finally:
        db.close()
```

> 在文件顶部补充 `from sqlalchemy import delete` 导入（原来只有 `create_engine, select, update`）。

**Step 5: 同步更新 `VectorStore.add_documents` 以支持 `asset_id` metadata**

在 Task 10 的 `add_documents` metadata 构建中加入：
```python
if asset_id is not None:
    metadata["asset_id"] = asset_id
```
并将方法签名改为：
```python
def add_documents(self, chunks, user_id, library_id=None, asset_id=None) -> int:
```

**Step 6: 验证**

```bash
python -c "from app.tasks import process_knowledge_asset, cleanup_library; print('OK')"
```

Expected: `OK`

**Step 7: Commit**

```bash
git add backend/app/tasks.py backend/app/services/rag/vector_store.py
git commit -m "feat: tasks support library_id, string vector_status, add cleanup_library task"
```

---

## Task 13: 端到端冒烟测试

**Step 1: 启动服务**

```bash
python start_dev.py
```

**Step 2: 测试知识库 CRUD**

```bash
# 注册/登录获取 token（用现有 auth 端点）
TOKEN="your_jwt_token"

# 创建知识库
curl -X POST http://localhost:8000/api/v1/libraries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "语文备课库", "description": "测试库"}'

# 列出个人库
curl http://localhost:8000/api/v1/libraries?scope=personal \
  -H "Authorization: Bearer $TOKEN"

# 列出系统公开库
curl http://localhost:8000/api/v1/libraries?scope=system \
  -H "Authorization: Bearer $TOKEN"
```

**Step 3: 测试文件上传和状态轮询**

```bash
LIBRARY_ID=1

# 上传文件（library_id 必填）
curl -X POST http://localhost:8000/api/v1/knowledge \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_name":"test.pdf","file_type":"pdf","file_path":"/path/test.pdf","library_id":'"$LIBRARY_ID"'}'

# 轮询状态
curl http://localhost:8000/api/v1/knowledge/1/status \
  -H "Authorization: Bearer $TOKEN"
```

**Step 4: 测试删除知识库（软删除 + 异步清理）**

```bash
curl -X DELETE http://localhost:8000/api/v1/libraries/1 \
  -H "Authorization: Bearer $TOKEN"
# 预期：204 立即返回，Celery 后台清理
```

---

## Task 14: 更新 DEVELOP.md

**Files:**
- Modify: `DEVELOP.md`

在文件末尾追加本次开发总结：

```markdown
## 知识库系统开发（2026-02-24）

**新增功能：**
- `KnowledgeLibrary` 模型：用户可创建多个知识库，管理员库可公开
- User 增加 `is_admin` 字段，管理员由数据库直接写入
- `VectorStatus` 枚举：`pending / processing / completed / failed`
- `library_id` 注入 ChromaDB metadata，实现单 collection 多库隔离
- `GET /libraries?scope=personal|system` 分区展示
- `GET /knowledge/{id}/status` 轻量轮询端点
- `cleanup_library` Celery 任务：软删除 + 异步清理向量/文件/DB

**架构决策：**
- 采用单 ChromaDB collection + metadata `$in` 过滤（非多 collection），
  原因：多库联合检索只需一次向量查询，避免跨 collection 合并重排
- 删除知识库用软删除（`is_deleted=True`）立即返回，Celery 异步清理，
  避免多组件级联删除的部分失败脏数据问题
```

**Commit**

```bash
git add DEVELOP.md
git commit -m "docs: update DEVELOP.md with knowledge library system summary"
```
