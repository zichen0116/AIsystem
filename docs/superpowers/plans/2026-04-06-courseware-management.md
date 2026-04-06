# Courseware Management Real Data Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded mock courseware management page with real backend data — aggregating PPT projects, lesson plans, and user-uploaded files into a unified listing with edit/delete/download/favorites/navigation.

**Architecture:** Backend adds new fields to `courseware` table (for uploaded files only), a new aggregation endpoint merging three data sources, Redis cache for PPT covers, upload/download endpoints. Frontend rewrites the Pinia store from mock to API-driven with dual-list strategy, rewires the card UI, and adds action menu with edit/delete/download interactions.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Alembic, Redis (aioredis), Aliyun OSS, Vue 3 Composition API, Pinia, dayjs

**Spec:** `docs/superpowers/specs/2026-04-06-courseware-management-design.md`

---

## File Structure

### Backend — New/Modified Files

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/courseware.py` | Modify | Add file_name, file_size, file_type, tags, remark columns |
| `backend/app/schemas/courseware.py` | Modify | Add CoursewareUploadResponse, CoursewareAggregateItem, CoursewareAggregateResponse, extend CoursewareUpdate |
| `backend/app/api/courseware.py` | Modify | Add /all, /upload, /download endpoints; extend PATCH |
| `backend/app/services/courseware_service.py` | Create | Aggregation logic, Redis cover cache helpers |
| `backend/app/services/redis_service.py` | Create | Shared Redis singleton (extracted from sms.py pattern) |
| `backend/app/generators/ppt/banana_routes.py` | Modify | Add Redis cache invalidation in list_projects cover lookup |

### Frontend — New/Modified Files

| File | Action | Responsibility |
|---|---|---|
| `teacher-platform/src/stores/courseware.js` | Rewrite | API-driven store with dual-list, favorites, CRUD actions |
| `teacher-platform/src/api/courseware.js` | Create | API functions for /courseware/* endpoints |
| `teacher-platform/src/views/CoursewareManage.vue` | Modify | Rewire to store, add action menu, edit modal, time formatting |
| `teacher-platform/src/views/PersonalCenter.vue` | Modify | Adapt to new store shape |
| `teacher-platform/src/views/LessonPrep.vue` | Modify | Parse route query params for tab/projectId/lessonPlanId |
| `teacher-platform/src/views/LessonPlanPage.vue` | Modify | Support loading existing plan by id from route |

---

## Task 1: Extend Courseware Database Model

**Files:**
- Modify: `backend/app/models/courseware.py`

- [ ] **Step 1: Add new columns to Courseware model**

In `backend/app/models/courseware.py`, add after the `file_url` field (line 49). **Use the repo's existing ORM style (`Mapped` + `mapped_column`)**, NOT `Column()`:

```python
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # pdf/ppt/word/video/image
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Update the imports at the top to add `BigInteger` and `Text`:

```python
from sqlalchemy import String, DateTime, ForeignKey, Integer, BigInteger, Text
```

- [ ] **Step 2: Generate Alembic migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "add file fields to courseware table"
```

Expected: New migration file in `backend/alembic/versions/`.

- [ ] **Step 3: Apply migration**

Run:
```bash
cd backend
alembic upgrade head
```

Expected: Migration applies successfully, 5 new columns added.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/courseware.py backend/alembic/versions/
git commit -m "feat(courseware): add file_name, file_size, file_type, tags, remark columns"
```

---

## Task 2: Extend Courseware Schemas

**Files:**
- Modify: `backend/app/schemas/courseware.py`

- [ ] **Step 1: Extend CoursewareUpdate with new writable fields**

In `backend/app/schemas/courseware.py`, replace the existing `CoursewareUpdate` class (lines 20-26):

```python
class CoursewareUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content_json: Optional[dict] = None
    status: Optional[str] = None
    file_url: Optional[str] = None
    tags: Optional[str] = Field(None, max_length=500)
    remark: Optional[str] = None
    file_type: Optional[str] = None

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v):
        if v is not None and v not in ("pdf", "ppt", "word", "video", "image"):
            raise ValueError("file_type must be one of: pdf, ppt, word, video, image")
        return v
```

Add `field_validator` to the pydantic imports:

```python
from pydantic import BaseModel, Field, field_validator
```

- [ ] **Step 2: Add aggregation response schemas**

Append to the end of the file:

```python
class CoursewareAggregateItem(BaseModel):
    id: str                           # prefixed: ppt_123, lp_456, up_789
    source_type: str                  # ppt / lesson_plan / uploaded
    name: str
    file_type: str                    # pdf / ppt / word / video / image
    file_size: Optional[int] = None   # bytes
    status: Optional[str] = None
    cover_image: Optional[str] = None
    updated_at: datetime
    source_id: int                    # raw DB id
    tags: Optional[str] = None
    remark: Optional[str] = None
    file_url: Optional[str] = None
    page_count: Optional[int] = None  # only for PPT

class CoursewareAggregateResponse(BaseModel):
    items: list[CoursewareAggregateItem]
    total: int
```

Ensure `Optional` is imported from `typing`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/courseware.py
git commit -m "feat(courseware): extend schemas with aggregation response and update validation"
```

---

## Task 3: Create Redis Service Singleton

**Files:**
- Create: `backend/app/services/redis_service.py`

- [ ] **Step 1: Create shared Redis module**

Following the same pattern from `sms.py` (lazy singleton via `aioredis.from_url`):

```python
"""Shared async Redis singleton."""

import redis.asyncio as aioredis
from app.core.config import get_settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def get_ppt_cover(project_id: int) -> str | None:
    """Get cached PPT cover URL. Returns None on cache miss."""
    r = await get_redis()
    return await r.get(f"ppt:cover:{project_id}")


async def set_ppt_cover(project_id: int, cover_url: str, ttl: int = 86400):
    """Cache PPT cover URL with TTL (default 24h)."""
    r = await get_redis()
    await r.set(f"ppt:cover:{project_id}", cover_url, ex=ttl)


async def invalidate_ppt_cover(project_id: int):
    """Delete cached PPT cover."""
    r = await get_redis()
    await r.delete(f"ppt:cover:{project_id}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/redis_service.py
git commit -m "feat(redis): add shared redis singleton with PPT cover cache helpers"
```

---

## Task 4: Create Courseware Aggregation Service

**Files:**
- Create: `backend/app/services/courseware_service.py`

- [ ] **Step 1: Create aggregation service**

```python
"""Courseware aggregation service — merges PPT projects, lesson plans, and uploaded files."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.courseware import Courseware
from app.models.lesson_plan import LessonPlan
from app.generators.ppt.banana_models import PPTProject, PPTPage
from app.schemas.courseware import CoursewareAggregateItem, CoursewareAggregateResponse
from app.services.redis_service import get_ppt_cover, set_ppt_cover


async def _get_cover_url(db: AsyncSession, project_id: int) -> str:
    """Get PPT cover URL with Redis cache-aside."""
    cached = await get_ppt_cover(project_id)
    if cached is not None:
        return cached  # "" means no cover (cached negative)

    stmt = (
        select(PPTPage.image_url)
        .where(PPTPage.project_id == project_id, PPTPage.image_url.isnot(None))
        .order_by(PPTPage.page_number)
        .limit(1)
    )
    result = await db.execute(stmt)
    url = result.scalar_one_or_none() or ""
    await set_ppt_cover(project_id, url)
    return url


async def _get_page_count(db: AsyncSession, project_id: int) -> int:
    stmt = select(func.count()).select_from(PPTPage).where(PPTPage.project_id == project_id)
    result = await db.execute(stmt)
    return result.scalar_one()


def _apply_date_filter(dt: datetime, date_range: Optional[str]) -> bool:
    if not date_range:
        return True
    now = datetime.now(timezone.utc)
    if date_range == "week":
        return dt >= now - timedelta(days=7)
    elif date_range == "month":
        return dt >= now - timedelta(days=30)
    elif date_range == "year":
        return dt >= now - timedelta(days=365)
    return True


async def get_aggregated_courseware(
    db: AsyncSession,
    user_id: int,
    source_type: Optional[str] = None,
    file_type: Optional[str] = None,
    date_range: Optional[str] = None,
) -> CoursewareAggregateResponse:
    items: list[CoursewareAggregateItem] = []

    # --- PPT Projects ---
    if source_type in (None, "all", "ppt"):
        if file_type in (None, "ppt"):
            stmt = select(PPTProject).where(PPTProject.user_id == user_id)
            result = await db.execute(stmt)
            for p in result.scalars().all():
                updated = p.updated_at or p.created_at
                if not _apply_date_filter(updated, date_range):
                    continue
                cover = await _get_cover_url(db, p.id)
                page_count = await _get_page_count(db, p.id)
                items.append(CoursewareAggregateItem(
                    id=f"ppt_{p.id}",
                    source_type="ppt",
                    name=p.title or p.outline_text or "未命名PPT",
                    file_type="ppt",
                    file_size=None,
                    status=p.status or "DRAFT",
                    cover_image=cover or None,
                    updated_at=updated,
                    source_id=p.id,
                    tags=None,
                    remark=None,
                    file_url=p.exported_file_url,
                    page_count=page_count,
                ))

    # --- Lesson Plans ---
    if source_type in (None, "all", "lesson_plan"):
        if file_type in (None, "word"):
            stmt = select(LessonPlan).where(LessonPlan.user_id == user_id)
            result = await db.execute(stmt)
            for lp in result.scalars().all():
                updated = lp.updated_at or lp.created_at
                if not _apply_date_filter(updated, date_range):
                    continue
                items.append(CoursewareAggregateItem(
                    id=f"lp_{lp.id}",
                    source_type="lesson_plan",
                    name=lp.title or "未命名教案",
                    file_type="word",
                    file_size=None,
                    status=lp.status or "draft",
                    cover_image=None,
                    updated_at=updated,
                    source_id=lp.id,
                    tags=None,
                    remark=None,
                    file_url=None,
                    page_count=None,
                ))

    # --- Uploaded Files (from courseware table) ---
    if source_type in (None, "all", "uploaded"):
        stmt = select(Courseware).where(Courseware.user_id == user_id)
        result = await db.execute(stmt)
        for c in result.scalars().all():
            # Skip courseware linked to PPT projects (those are AI-generated, shown via ppt_projects)
            if c.ppt_project_id is not None:
                continue
            c_file_type = c.file_type or "pdf"
            if file_type and c_file_type != file_type:
                continue
            updated = c.updated_at or c.created_at
            if not _apply_date_filter(updated, date_range):
                continue
            items.append(CoursewareAggregateItem(
                id=f"up_{c.id}",
                source_type="uploaded",
                name=c.title or c.file_name or "未命名文件",
                file_type=c_file_type,
                file_size=c.file_size,
                status=c.status,
                cover_image=None,
                updated_at=updated,
                source_id=c.id,
                tags=c.tags,
                remark=c.remark,
                file_url=c.file_url,
                page_count=None,
            ))

    # Sort all items by updated_at DESC
    items.sort(key=lambda x: x.updated_at, reverse=True)

    return CoursewareAggregateResponse(items=items, total=len(items))
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/courseware_service.py
git commit -m "feat(courseware): add aggregation service merging PPT, lesson plans, uploaded files"
```

---

## Task 5: Add Backend API Endpoints

**Files:**
- Modify: `backend/app/api/courseware.py`

- [ ] **Step 1: Add aggregation endpoint and upload endpoint**

Add imports at the top of `backend/app/api/courseware.py`:

```python
from fastapi import UploadFile, File, Form
from fastapi.responses import RedirectResponse, FileResponse
from app.services.courseware_service import get_aggregated_courseware
from app.services.oss_service import upload_file as oss_upload, delete_file as oss_delete
from app.schemas.courseware import CoursewareAggregateResponse, CoursewareAggregateItem
```

Add these endpoints after the existing ones (after line 159):

```python
@router.get("/all", response_model=CoursewareAggregateResponse)
async def list_all_courseware(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    source_type: str | None = None,
    file_type: str | None = None,
    date_range: str | None = None,
):
    """聚合列出用户所有课件：PPT项目 + 教案 + 上传文件"""
    return await get_aggregated_courseware(
        db, current_user.id, source_type, file_type, date_range
    )


@router.post("/upload", status_code=201)
async def upload_courseware(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    remark: str | None = Form(None),
):
    """上传课件文件到OSS并创建记录"""
    # Read file size BEFORE oss_upload (which consumes the stream)
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # reset for oss_upload to read

    oss_result = await oss_upload(file, current_user.id)

    # Derive file_type from oss_service result
    file_type_val = oss_result.get("file_type", "pdf")

    # Use provided title or strip extension from original filename
    original_name = oss_result.get("file_name", file.filename or "未命名文件")
    display_title = title or original_name.rsplit(".", 1)[0]

    courseware = Courseware(
        user_id=current_user.id,
        title=display_title,
        type="UPLOADED",
        status="COMPLETED",
        file_url=oss_result["url"],
        file_name=original_name,
        file_size=file_size,
        file_type=file_type_val,
        tags=tags,
        remark=remark,
    )
    db.add(courseware)
    await db.commit()
    await db.refresh(courseware)

    return CoursewareAggregateItem(
        id=f"up_{courseware.id}",
        source_type="uploaded",
        name=courseware.title,
        file_type=courseware.file_type or "pdf",
        file_size=courseware.file_size,
        status=courseware.status,
        cover_image=None,
        updated_at=courseware.updated_at or courseware.created_at,
        source_id=courseware.id,
        tags=courseware.tags,
        remark=courseware.remark,
        file_url=courseware.file_url,
        page_count=None,
    )


@router.get("/download")
async def download_courseware(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    source_type: str = Query(...),
    source_id: int = Query(...),
):
    """统一下载入口"""
    if source_type == "uploaded":
        stmt = select(Courseware).where(
            Courseware.id == source_id, Courseware.user_id == current_user.id
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item or not item.file_url:
            raise HTTPException(404, "文件不存在")
        return RedirectResponse(url=item.file_url)

    elif source_type == "ppt":
        stmt = select(PPTProject).where(
            PPTProject.id == source_id, PPTProject.user_id == current_user.id
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(404, "PPT项目不存在")
        if project.exported_file_url:
            return RedirectResponse(url=project.exported_file_url)
        raise HTTPException(400, "该PPT尚未导出，请先在备课页面导出")

    elif source_type == "lesson_plan":
        stmt = select(LessonPlan).where(
            LessonPlan.id == source_id, LessonPlan.user_id == current_user.id
        )
        result = await db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            raise HTTPException(404, "教案不存在")
        # Generate DOCX in-memory using existing logic
        from app.api.lesson_plan import _export_docx_from_content
        return _export_docx_from_content(plan.title or "教案", plan.content or "")

    raise HTTPException(400, "无效的 source_type")
```

Add the `Query` import:

```python
from fastapi import Query
```

Add model imports:

```python
from app.generators.ppt.banana_models import PPTProject
from app.models.lesson_plan import LessonPlan
```

- [ ] **Step 2: Extend update_courseware to handle new fields**

Replace the existing `update_courseware` function body (lines 99-133) so it also updates tags, remark, file_type:

In the update loop section (around line 116-126), after the existing field updates, add:

```python
    for field in ["title", "content_json", "status", "file_url", "tags", "remark", "file_type"]:
        value = getattr(data, field, None)
        if value is not None:
            setattr(courseware, field, value)
```

This replaces the existing per-field if-checks.

- [ ] **Step 3: Add OSS cleanup on delete**

In the existing `delete_courseware` function, before `await db.delete(courseware)`, add:

```python
    # Clean up OSS file for uploaded files
    if courseware.file_url:
        try:
            oss_delete(courseware.file_url)
        except Exception:
            pass  # OSS cleanup is best-effort
```

- [ ] **Step 4: Extract lesson plan DOCX export helper**

In `backend/app/api/lesson_plan.py`, the existing `export_docx` endpoint creates a DOCX from request body content. We need a reusable helper. Add this function before the `export_docx` route:

```python
def _export_docx_from_content(title: str, content: str) -> FileResponse:
    """Generate a DOCX file from title and markdown content, return as FileResponse."""
    import tempfile
    from docx import Document as DocxDocument

    doc = DocxDocument()
    doc.add_heading(title, level=1)
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        else:
            doc.add_paragraph(line)

    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    doc.save(tmp.name)
    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{title}.docx",
    )
```

- [ ] **Step 5: Ensure /all endpoint is registered BEFORE /{id}**

FastAPI matches routes in order. The existing `GET /{courseware_id}` will catch `/all` as a path parameter if `/all` is defined after it. Move the `/all` endpoint definition to be **before** the `/{courseware_id}` GET route (before line 75), or use a more specific path.

The simplest fix: place the `list_all_courseware` and `download_courseware` and `upload_courseware` endpoints **before** the `get_courseware` (line 75) route in the file.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/courseware.py backend/app/api/lesson_plan.py
git commit -m "feat(courseware): add /all aggregation, /upload, /download endpoints"
```

---

## Task 6: Add Redis Cache Invalidation to PPT Routes

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py`

- [ ] **Step 1: Add cache invalidation on image generation complete**

Find the `generate_images` related code. After image generation succeeds (where `PPTPage.image_url` is updated), add:

```python
from app.services.redis_service import invalidate_ppt_cover

# After updating page image_url:
await invalidate_ppt_cover(project_id)
```

- [ ] **Step 2: Add cache invalidation on project delete**

In `delete_project` (line 533-549), before `await db.delete(project)`, add:

```python
    await invalidate_ppt_cover(project_id)
```

- [ ] **Step 3: Add cache invalidation on page delete and reorder**

In `delete_page` and `reorder_pages` functions, add `await invalidate_ppt_cover(project_id)` after the DB changes.

- [ ] **Step 4: Use cache in list_projects**

In `list_projects` (line 431-472), replace the cover image N+1 subquery loop with cache-aside:

```python
from app.services.redis_service import get_ppt_cover, set_ppt_cover

# Replace the inner page query + cover detection with:
cover_url = await get_ppt_cover(project.id)
if cover_url is None:
    page_result = await db.execute(
        select(PPTPage.image_url)
        .where(PPTPage.project_id == project.id, PPTPage.image_url.isnot(None))
        .order_by(PPTPage.page_number)
        .limit(1)
    )
    cover_url = page_result.scalar_one_or_none() or ""
    await set_ppt_cover(project.id, cover_url)

# Still need page_count separately:
page_count_result = await db.execute(
    select(func.count()).select_from(PPTPage).where(PPTPage.project_id == project.id)
)
page_count = page_count_result.scalar_one()
```

Add `func` import: `from sqlalchemy import select, func`

- [ ] **Step 5: Commit**

```bash
git add backend/app/generators/ppt/banana_routes.py
git commit -m "feat(ppt): add Redis cover cache with invalidation on image/page changes"
```

---

## Task 7: Create Frontend API Module

**Files:**
- Create: `teacher-platform/src/api/courseware.js`

- [ ] **Step 1: Create courseware API module**

```javascript
import { apiRequest, authFetch, resolveApiUrl } from './http.js'

const API = '/api/v1/courseware'

/**
 * 聚合获取所有课件（PPT + 教案 + 上传文件）
 * @param {Object} filters - { source_type, file_type, date_range }
 */
export async function fetchAllCourseware(filters = {}) {
  const params = new URLSearchParams()
  if (filters.source_type) params.append('source_type', filters.source_type)
  if (filters.file_type) params.append('file_type', filters.file_type)
  if (filters.date_range) params.append('date_range', filters.date_range)
  const query = params.toString()
  const url = `${API}/all${query ? '?' + query : ''}`
  return await apiRequest(url)
}

/**
 * 上传课件文件
 * @param {File} file
 * @param {Object} meta - { title, tags, remark }
 */
export async function uploadCourseware(file, meta = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (meta.title) formData.append('title', meta.title)
  if (meta.tags) formData.append('tags', meta.tags)
  if (meta.remark) formData.append('remark', meta.remark)

  const resp = await authFetch(`${API}/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || '上传失败')
  }
  return await resp.json()
}

/**
 * 更新上传课件信息
 */
export async function updateCourseware(id, data) {
  return await apiRequest(`${API}/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

/**
 * 删除上传课件
 */
export async function deleteCoursewareItem(id) {
  return await apiRequest(`${API}/${id}`, { method: 'DELETE' })
}

/**
 * 下载课件
 * @param {string} sourceType - uploaded / ppt / lesson_plan
 * @param {number} sourceId
 */
export function getDownloadUrl(sourceType, sourceId) {
  return resolveApiUrl(`${API}/download?source_type=${sourceType}&source_id=${sourceId}`)
}
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/api/courseware.js
git commit -m "feat(frontend): add courseware API module"
```

---

## Task 8: Rewrite Courseware Pinia Store

**Files:**
- Rewrite: `teacher-platform/src/stores/courseware.js`

- [ ] **Step 1: Rewrite store with dual-list strategy**

```javascript
import { defineStore } from 'pinia'
import {
  fetchAllCourseware,
  uploadCourseware as apiUpload,
  updateCourseware as apiUpdate,
  deleteCoursewareItem as apiDelete,
  getDownloadUrl,
} from '../api/courseware.js'
import { apiRequest } from '../api/http.js'
import { deleteProject } from '../api/ppt.js'

export const useCoursewareStore = defineStore('courseware', {
  state: () => ({
    allCoursewareList: [],       // full unfiltered list (for favorites)
    filteredCoursewareList: [],  // current filtered view
    loading: false,
    error: null,
    favorites: new Set(),        // in-memory only
  }),

  getters: {
    favoritedList(state) {
      return state.allCoursewareList.filter(item => state.favorites.has(item.id))
    },
  },

  actions: {
    async fetchAll() {
      try {
        const data = await fetchAllCourseware()
        this.allCoursewareList = data.items || []
      } catch (e) {
        console.error('fetchAll failed:', e)
      }
    },

    async fetchFiltered(filters = {}) {
      this.loading = true
      this.error = null
      try {
        const data = await fetchAllCourseware(filters)
        this.filteredCoursewareList = data.items || []
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },

    toggleFavorite(id) {
      if (this.favorites.has(id)) {
        this.favorites.delete(id)
      } else {
        this.favorites.add(id)
      }
      // Trigger reactivity (Set is not reactive by default in Pinia)
      this.favorites = new Set(this.favorites)
    },

    async deleteCourseware(id) {
      const [prefix, rawId] = _parseId(id)
      if (prefix === 'ppt') {
        await deleteProject(Number(rawId))
      } else if (prefix === 'lp') {
        await apiRequest(`/api/v1/lesson-plan/${rawId}`, { method: 'DELETE' })
      } else {
        await apiDelete(Number(rawId))
      }
      // Remove from both lists
      this.allCoursewareList = this.allCoursewareList.filter(i => i.id !== id)
      this.filteredCoursewareList = this.filteredCoursewareList.filter(i => i.id !== id)
      this.favorites.delete(id)
      this.favorites = new Set(this.favorites)
    },

    async updateCoursewareItem(id, data) {
      const [prefix, rawId] = _parseId(id)
      if (prefix === 'ppt') {
        await apiRequest(`/api/v1/ppt/projects/${rawId}`, {
          method: 'PUT',
          body: JSON.stringify({ title: data.title }),
        })
      } else if (prefix === 'lp') {
        await apiRequest(`/api/v1/lesson-plan/${rawId}`, {
          method: 'PATCH',
          body: JSON.stringify({ title: data.title }),
        })
      } else {
        await apiUpdate(Number(rawId), data)
      }
      // Update in both lists
      const updateItem = (item) => {
        if (item.id !== id) return item
        return { ...item, ...data, name: data.title || item.name }
      }
      this.allCoursewareList = this.allCoursewareList.map(updateItem)
      this.filteredCoursewareList = this.filteredCoursewareList.map(updateItem)
    },

    async uploadCourseware(file, meta) {
      const newItem = await apiUpload(file, meta)
      this.allCoursewareList.unshift(newItem)
      this.filteredCoursewareList.unshift(newItem)
      return newItem
    },

    downloadCourseware(item) {
      const [prefix, rawId] = _parseId(item.id)
      const sourceType = prefix === 'ppt' ? 'ppt' : prefix === 'lp' ? 'lesson_plan' : 'uploaded'
      const url = getDownloadUrl(sourceType, Number(rawId))
      window.open(url, '_blank')
    },
  },
})

function _parseId(id) {
  const idx = id.indexOf('_')
  return [id.slice(0, idx), id.slice(idx + 1)]
}
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/stores/courseware.js
git commit -m "feat(frontend): rewrite courseware store with API integration and dual-list"
```

---

## Task 9: Rewrite CoursewareManage.vue

**Files:**
- Modify: `teacher-platform/src/views/CoursewareManage.vue`

- [ ] **Step 1: Replace script setup with API-driven logic**

Replace the entire `<script setup>` block with:

```javascript
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCoursewareStore } from '../stores/courseware'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const router = useRouter()
const coursewareStore = useCoursewareStore()

// --- Filters ---
const filterType = ref('all')
const filterDate = ref('all')
const viewMode = ref('grid')

// --- Upload modal ---
const showAddModal = ref(false)
const fileInputRef = ref(null)
const selectedFiles = ref([])
const uploadTitle = ref('')
const uploadTags = ref('')
const uploadRemark = ref('')
const isUploading = ref(false)

// --- Edit modal ---
const showEditModal = ref(false)
const editItem = ref(null)
const editForm = ref({ title: '', tags: '', remark: '', file_type: '' })

// --- Action menu ---
const activeMenuId = ref(null)

// --- Delete confirm ---
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)

// --- Toast ---
const toastMessage = ref('')
const toastVisible = ref(false)

function showToast(msg) {
  toastMessage.value = msg
  toastVisible.value = true
  setTimeout(() => { toastVisible.value = false }, 3000)
}

// --- Data loading ---
const filteredList = computed(() => coursewareStore.filteredCoursewareList)
const loading = computed(() => coursewareStore.loading)

function buildFilters() {
  const filters = {}
  if (filterType.value !== 'all') filters.file_type = filterType.value
  if (filterDate.value !== 'all') filters.date_range = filterDate.value
  return filters
}

watch([filterType, filterDate], () => {
  coursewareStore.fetchFiltered(buildFilters())
})

onMounted(async () => {
  await Promise.all([
    coursewareStore.fetchAll(),
    coursewareStore.fetchFiltered(buildFilters()),
  ])
})

// --- Time formatting ---
function formatTime(isoStr) {
  if (!isoStr) return '—'
  const d = dayjs(isoStr)
  const now = dayjs()
  const diffDays = now.diff(d, 'day')
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return d.format('YYYY年M月D日')
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// --- Card click ---
function handleCardClick(item) {
  if (item.source_type === 'ppt') {
    router.push({ path: '/lesson-prep', query: { tab: 'ppt', projectId: item.source_id } })
  } else if (item.source_type === 'lesson_plan') {
    router.push({ path: '/lesson-prep', query: { tab: 'lesson-plan', lessonPlanId: item.source_id } })
  } else {
    showToast('该课件为手动上传，暂不支持在线编辑')
  }
}

// --- Action menu ---
function toggleMenu(id, event) {
  event.stopPropagation()
  activeMenuId.value = activeMenuId.value === id ? null : id
}

function closeMenu() {
  activeMenuId.value = null
}

// --- Edit ---
function openEdit(item, event) {
  event.stopPropagation()
  closeMenu()
  editItem.value = item
  editForm.value = {
    title: item.name || '',
    tags: item.tags || '',
    remark: item.remark || '',
    file_type: item.file_type || '',
  }
  showEditModal.value = true
}

async function saveEdit() {
  if (!editItem.value) return
  try {
    const data = { title: editForm.value.title }
    if (editItem.value.source_type === 'uploaded') {
      data.tags = editForm.value.tags
      data.remark = editForm.value.remark
      data.file_type = editForm.value.file_type
    }
    await coursewareStore.updateCoursewareItem(editItem.value.id, data)
    showEditModal.value = false
    showToast('修改成功')
  } catch (e) {
    showToast('修改失败: ' + e.message)
  }
}

// --- Delete ---
function confirmDelete(item, event) {
  event.stopPropagation()
  closeMenu()
  deleteTarget.value = item
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    await coursewareStore.deleteCourseware(deleteTarget.value.id)
    showDeleteConfirm.value = false
    showToast('删除成功')
  } catch (e) {
    showToast('删除失败: ' + e.message)
  }
}

// --- Download ---
function handleDownload(item, event) {
  event.stopPropagation()
  closeMenu()
  coursewareStore.downloadCourseware(item)
}

// --- Upload ---
function triggerFileSelect() {
  fileInputRef.value?.click()
}

function onFileSelected(event) {
  const files = Array.from(event.target.files || [])
  selectedFiles.value = files
}

async function doUpload() {
  if (selectedFiles.value.length === 0) return
  isUploading.value = true
  try {
    for (const file of selectedFiles.value) {
      await coursewareStore.uploadCourseware(file, {
        title: uploadTitle.value || undefined,
        tags: uploadTags.value || undefined,
        remark: uploadRemark.value || undefined,
      })
    }
    showAddModal.value = false
    selectedFiles.value = []
    uploadTitle.value = ''
    uploadTags.value = ''
    uploadRemark.value = ''
    showToast('上传成功')
  } catch (e) {
    showToast('上传失败: ' + e.message)
  } finally {
    isUploading.value = false
  }
}

// --- Favorite ---
function toggleFavorite(item, event) {
  event.stopPropagation()
  coursewareStore.toggleFavorite(item.id)
}

function isFavorited(item) {
  return coursewareStore.favorites.has(item.id)
}

// --- Thumbnail ---
function getThumbnailBg(fileType) {
  const colors = {
    pdf: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)',
    ppt: 'linear-gradient(135deg, #f39c12 0%, #e67e22 100%)',
    video: 'linear-gradient(135deg, #a29bfe 0%, #6c5ce7 100%)',
    word: 'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)',
    image: 'linear-gradient(135deg, #55efc4 0%, #00b894 100%)',
  }
  return colors[fileType] || colors.pdf
}

function getSourceLabel(sourceType) {
  return sourceType === 'uploaded' ? '手动上传' : 'AI生成'
}
```

- [ ] **Step 2: Replace template**

Replace the `<template>` section. Keep the same structure/classes but rewire data bindings:

Key changes in template:
- Replace `paginatedCourseware` with `filteredList`
- Replace `item.name` usage (already correct)
- Replace `item.subject + '·' + item.grade` with `getSourceLabel(item.source_type)`
- Replace `item.modifyDate` with `formatTime(item.updated_at)`
- Replace `item.size` with `formatSize(item.file_size)`
- Add `cover_image` display: `<img v-if="item.cover_image" :src="item.cover_image" />` in thumbnail
- Add `⋮` action menu button in each card
- Add edit modal (Teleport)
- Add delete confirm dialog (Teleport)
- Remove pagination controls
- Replace `item.favorited` with `isFavorited(item)`
- Upload modal: add title/tags/remark input fields

- [ ] **Step 3: Install dayjs**

```bash
cd teacher-platform
npm install dayjs
```

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/views/CoursewareManage.vue teacher-platform/package.json teacher-platform/package-lock.json
git commit -m "feat(frontend): rewrite CoursewareManage with real API data, action menu, edit/delete/download"
```

---

## Task 10: Update PersonalCenter.vue

**Files:**
- Modify: `teacher-platform/src/views/PersonalCenter.vue`

- [ ] **Step 1: Adapt to new store shape**

In `PersonalCenter.vue`, update the favorites computed properties:

Replace `favoritesList` (around line 280):
```javascript
const favoritesList = computed(() => coursewareStore.favoritedList)
```
This still works — the getter name hasn't changed.

Update the card template to use new field names. In the favorites card rendering (around lines 560-583):
- Replace `item.name` → `item.name` (same)
- Replace `item.type` → `item.file_type`
- Replace `item.size` → format with `formatSize(item.file_size)` (add helper or inline)
- Replace `item.modifyDate` → format `item.updated_at` with dayjs
- Replace `item.subject + '·' + item.grade` → `getSourceLabel(item.source_type)`
- Replace `item.favorited` class check → `true` (always favorited since it's in favoritedList)

Add `onMounted` to load data:
```javascript
onMounted(async () => {
  await coursewareStore.fetchAll()
})
```

Add necessary imports:
```javascript
import dayjs from 'dayjs'
```

Update `favoriteFilters` computed to use `file_type` instead of `type`:
```javascript
const favoriteFilters = computed(() => {
  const list = favoritesList.value
  return [
    { id: 'all', label: '全部', count: list.length },
    { id: 'pdf', label: 'PDF', count: list.filter(i => i.file_type === 'pdf').length },
    { id: 'ppt', label: 'PPT', count: list.filter(i => i.file_type === 'ppt').length },
    { id: 'video', label: '视频', count: list.filter(i => i.file_type === 'video').length },
    { id: 'word', label: 'Word', count: list.filter(i => i.file_type === 'word').length },
  ]
})
```

Update `filteredFavorites` to use `file_type`:
```javascript
const filteredFavorites = computed(() => {
  if (favoriteFilter.value === 'all') return favoritesList.value
  return favoritesList.value.filter(i => i.file_type === favoriteFilter.value)
})
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/views/PersonalCenter.vue
git commit -m "feat(frontend): adapt PersonalCenter favorites to new courseware store shape"
```

---

## Task 11: Add Card Navigation — LessonPrep Route Params

**Files:**
- Modify: `teacher-platform/src/views/LessonPrep.vue`
- Modify: `teacher-platform/src/views/LessonPlanPage.vue`

- [ ] **Step 1: Add route query param handling to LessonPrep.vue**

In `LessonPrep.vue`, the `activeTab` computed (line 33-37) already reads `route.query.tab`. We need to also forward `projectId` and `lessonPlanId` to child components.

Add reactive refs:
```javascript
const routeProjectId = computed(() => route.query.projectId || null)
const routeLessonPlanId = computed(() => route.query.lessonPlanId || null)
```

Pass to child components in the template. Change the `<component>` tag:
```html
<component
  :is="currentComponent"
  :reset-key="currentResetKey"
  :initial-project-id="routeProjectId"
  :initial-lesson-plan-id="routeLessonPlanId"
/>
```

The PPT component (`PptIndex → PptHistory`) and `LessonPlanPage` will receive these as props.

- [ ] **Step 2: Handle projectId in PptIndex/PptHistory flow**

In `LessonPrep.vue`, add a watcher for PPT projectId:

```javascript
import { usePptStore } from '../stores/ppt'

const pptStore = usePptStore()

watch(routeProjectId, async (newId) => {
  if (newId && activeTab.value === 'ppt') {
    // Load project and go to appropriate phase
    // Replicates PptHistory.vue's openProject() + getProjectPhase() logic
    await pptStore.fetchProject(Number(newId))
    await pptStore.fetchPages(Number(newId))

    // Determine phase using same logic as PptHistory.getProjectPhase():
    // - has pages with images → preview
    // - has pages but no images → outline
    // - dialog creation type with no pages → dialog
    // - default → outline
    const pages = pptStore.outlinePages || []
    const hasImages = pages.some(p => p.imageUrl)
    let phase = 'outline'
    if (hasImages) {
      phase = 'preview'
    } else if (pages.length === 0 && pptStore.projectData?.creation_type === 'dialog') {
      phase = 'dialog'
    }
    pptStore.setPhase(phase)

    // Clear query params to avoid re-triggering
    router.replace({ query: { tab: 'ppt' } })
  }
}, { immediate: true })
```

- [ ] **Step 3: Handle lessonPlanId in LessonPlanPage**

In `LessonPlanPage.vue`, add a prop and watcher:

Add props:
```javascript
const props = defineProps({
  resetKey: { type: Number, default: 0 },
  initialLessonPlanId: { type: [String, Number], default: null },
})
```

In `onMounted`, check for initial lesson plan:
```javascript
onMounted(async () => {
  isFirstMount = true
  if (props.initialLessonPlanId) {
    await loadHistorySession({ id: props.initialLessonPlanId })
    // Switch to writer mode to show the editor
    if (currentMarkdown.value) {
      enterWriterMode()
    }
  } else {
    startNewConversation()
  }
})
```

This reuses the existing `loadHistorySession` function which fetches plan detail + messages.

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/views/LessonPrep.vue teacher-platform/src/views/LessonPlanPage.vue
git commit -m "feat(frontend): add route param handling for card navigation to PPT/lesson plan"
```

---

## Task 12: Final Integration Testing & Polish

**Files:**
- All modified files

- [ ] **Step 1: Start backend and verify aggregation API**

```bash
cd backend
python run.py
```

In another terminal, test:
```bash
# Login first to get token, then:
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/courseware/all
```

Expected: JSON with `items` array containing PPT projects, lesson plans, and uploaded files.

- [ ] **Step 2: Test upload API**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -F "file=@test.pdf" -F "title=测试课件" -F "tags=测试,demo" \
  http://localhost:8000/api/v1/courseware/upload
```

Expected: 201 with CoursewareAggregateItem response.

- [ ] **Step 3: Start frontend and verify page**

```bash
cd teacher-platform
npm run dev
```

Navigate to `/courseware`:
- Verify real data loads (PPT projects with covers, lesson plans, uploaded files)
- Test type filter and date filter
- Test card click navigation (PPT → preview, lesson plan → editor, uploaded → toast)
- Test action menu: edit, delete, download
- Test upload modal
- Test favorites (star toggle, check PersonalCenter)
- Test grid/list view toggle

- [ ] **Step 4: Fix any issues found**

Address any bugs discovered during testing.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "fix(courseware): integration fixes after manual testing"
```
