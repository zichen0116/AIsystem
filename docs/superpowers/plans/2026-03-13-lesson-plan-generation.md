# Lesson Plan Generation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lesson plan generation tab to the LessonPrep page with AI chat + Tiptap editor + TOC sidebar, backed by PostgreSQL persistence and SSE streaming.

**Architecture:** Two-phase backend (RAG retrieval then streaming LLM generation), all state persisted to PostgreSQL (LessonPlan + LessonPlanReference + ChatHistory). Vue 3 frontend with Tiptap rich-text editor, markdown-it streaming preview, SSE real-time delivery. Tab lifecycle managed via keep-alive with DB reload.

**Tech Stack:** FastAPI, DashScope/OpenAI-compatible LLM (streaming via httpx), HybridRetriever (RAG), SQLAlchemy async + Alembic, Tiptap + tiptap-markdown, markdown-it, html2pdf.js, pypandoc

**Spec:** `docs/superpowers/specs/2026-03-13-lesson-plan-generation-design.md`

---

## File Structure

### Backend (Create)

| File | Responsibility |
|------|---------------|
| `backend/app/models/lesson_plan.py` | LessonPlan SQLAlchemy model |
| `backend/app/models/lesson_plan_reference.py` | LessonPlanReference SQLAlchemy model |
| `backend/app/schemas/lesson_plan.py` | Pydantic request/response schemas (6 endpoints) |
| `backend/app/services/lesson_plan_service.py` | Business logic: LLM streaming, RAG retrieval, DB ops |
| `backend/app/api/lesson_plan.py` | 6 REST/SSE endpoints |

### Backend (Modify)

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Import LessonPlan + LessonPlanReference |
| `backend/app/api/__init__.py` | Register lesson-plan router |
| `backend/requirements.txt` | Add pypandoc |
| `backend/app/services/ai/graph/nodes.py` | Fix should_retry return value |

### Frontend (Create)

| File | Responsibility |
|------|---------------|
| `teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue` | Tiptap editor + FloatingMenu + BubbleMenu + toolbar + streaming preview |
| `teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue` | Collapsible TOC sidebar with IntersectionObserver |
| `teacher-platform/src/components/lesson-plan/LessonPlanChat.vue` | Chat panel + knowledge picker + file upload + voice |
| `teacher-platform/src/views/LessonPrepLessonPlan.vue` | Main container: SSE streaming, DB lifecycle, three-column layout |

### Frontend (Modify)

| File | Change |
|------|--------|
| `teacher-platform/src/api/http.js` | Export getToken |
| `teacher-platform/src/views/LessonPrep.vue` | Add lesson-plan tab to tabs array + component map |
| `teacher-platform/src/components/LayoutWithNav.vue` | Add sidebar entry |

---

## Chunk 0: Pre-fixes

### Task 0: Fix Prerequisites

**Files:**
- Modify: `teacher-platform/src/api/http.js` (line 10)
- Modify: `backend/app/services/ai/graph/nodes.py` (should_retry function)

- [ ] **Step 1: Export `getToken` from http.js**

The `getToken` function at line 10 of `http.js` is not exported but our new components need it for SSE fetch calls with auth. Change:

```javascript
// old
function getToken() {
// new
export function getToken() {
```

- [ ] **Step 2: Fix `should_retry` in LangGraph nodes**

Read `backend/app/services/ai/graph/nodes.py` and find the `should_retry` function (~line 479-497). It returns `"end"` when grading passes, but the workflow conditional edge only maps `{"agent", "outline_approval"}`. Change the return value from `"end"` to `"outline_approval"` when the generation passes grading.

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/api/http.js backend/app/services/ai/graph/nodes.py
git commit -m "fix: export getToken from http.js and fix should_retry return value in LangGraph"
```

---

## Chunk 1: Dependencies + Database Foundation

### Task 1: Feature Branch + Install Dependencies

**Files:**
- Modify: `teacher-platform/package.json`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Create feature branch**

```bash
git checkout -b feature/lesson-plan
```

- [ ] **Step 2: Install frontend dependencies**

```bash
cd teacher-platform
npm install @tiptap/vue-3 @tiptap/starter-kit @tiptap/extension-placeholder @tiptap/extension-heading @tiptap/extension-table @tiptap/extension-table-row @tiptap/extension-table-cell @tiptap/extension-table-header @tiptap/extension-task-list @tiptap/extension-task-item @tiptap/extension-highlight @tiptap/extension-text-align @tiptap/extension-underline @tiptap/extension-floating-menu @tiptap/extension-bubble-menu @tiptap/extension-character-count @tiptap/pm tiptap-markdown markdown-it markdown-it-task-lists html2pdf.js
```

- [ ] **Step 3: Install backend dependency**

```bash
cd backend
pip install pypandoc
```

Add `pypandoc` to `backend/requirements.txt`.

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/package.json teacher-platform/package-lock.json backend/requirements.txt
git commit -m "build: add tiptap, markdown-it, html2pdf.js, pypandoc dependencies"
```

---

### Task 2: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/lesson_plan.py`
- Create: `backend/app/models/lesson_plan_reference.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create LessonPlan model**

Uses `Mapped[T] = mapped_column(...)` style matching existing models (`chat_history.py`, `user.py`).

```python
# backend/app/models/lesson_plan.py
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名教案")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft / generating / completed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
```

- [ ] **Step 2: Create LessonPlanReference model**

```python
# backend/app/models/lesson_plan_reference.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LessonPlanReference(Base):
    __tablename__ = "lesson_plan_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_plan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lesson_plans.id", ondelete="CASCADE"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    parsed_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

Note: `lesson_plan_id` is **nullable** -- this is a deliberate deviation from the spec (`nullable=False`) to support file upload before the first generate call creates a LessonPlan. Files are associated via `file_ids` in generate/modify requests.

- [ ] **Step 3: Register models in `__init__.py`**

Read `backend/app/models/__init__.py`. Add imports AND update `__all__`:

```python
# Add imports after existing ones
from app.models.lesson_plan import LessonPlan
from app.models.lesson_plan_reference import LessonPlanReference
```

Add to the `__all__` list:

```python
"LessonPlan",
"LessonPlanReference",
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/lesson_plan.py backend/app/models/lesson_plan_reference.py backend/app/models/__init__.py
git commit -m "feat(lesson-plan): add LessonPlan and LessonPlanReference SQLAlchemy models"
```

---

### Task 3: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/<auto>.py` (auto-generated)

- [ ] **Step 1: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add lesson_plans and lesson_plan_references tables"
```

- [ ] **Step 2: Apply migration**

```bash
alembic upgrade head
```

Verify in PostgreSQL that `lesson_plans` and `lesson_plan_references` tables exist with correct columns and foreign keys.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(lesson-plan): add database migration for lesson plan tables"
```

---

### Task 4: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/lesson_plan.py`

- [ ] **Step 1: Create schema file**

```python
# backend/app/schemas/lesson_plan.py
from typing import Optional

from pydantic import BaseModel, ConfigDict


# --- Request schemas ---

class LessonPlanGenerateRequest(BaseModel):
    query: str
    library_ids: list[int] = []
    file_ids: list[int] = []
    session_id: Optional[str] = None  # omit to auto-create


class LessonPlanModifyRequest(BaseModel):
    lesson_plan_id: int
    instruction: str
    current_content: str
    file_ids: list[int] = []
    library_ids: list[int] = []


class LessonPlanSaveRequest(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None


class LessonPlanExportRequest(BaseModel):
    content: str
    title: str = "教案"


# --- Response schemas ---

class LessonPlanInfo(BaseModel):
    id: int
    session_id: str
    title: str
    content: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class MessageInfo(BaseModel):
    role: str
    content: str


class FileInfo(BaseModel):
    id: int
    filename: str


class LessonPlanLatestResponse(BaseModel):
    lesson_plan: Optional[LessonPlanInfo] = None
    messages: list[MessageInfo] = []
    files: list[FileInfo] = []


class LessonPlanSaveResponse(BaseModel):
    id: int
    updated_at: str


class LessonPlanUploadResponse(BaseModel):
    file_id: int
    filename: str
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/lesson_plan.py
git commit -m "feat(lesson-plan): add pydantic schemas for all lesson plan endpoints"
```

---

## Chunk 2: Backend Service + API

### Task 5: Lesson Plan Service

**Files:**
- Create: `backend/app/services/lesson_plan_service.py`

This service provides: LLM streaming, RAG context retrieval, chat history retrieval, and post-streaming DB persistence. The API layer (Task 6) consumes these functions and wraps them in SSE format.

Key references:
- LLM streaming pattern: `backend/app/services/html_llm.py` (lines 151-212)
- RAG retrieval: `backend/app/services/rag/hybrid_retriever.py` - `get_hybrid_retriever().search()`
- Config: `backend/app/core/config.py` - `DASHSCOPE_API_KEY`, `LLM_MODEL`, `HTML_LLM_*` as fallback

- [ ] **Step 1: Create the service file**

```python
# backend/app/services/lesson_plan_service.py
import json
import logging
import uuid
from typing import AsyncGenerator

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.chat_history import ChatHistory
from app.models.lesson_plan import LessonPlan
from app.models.lesson_plan_reference import LessonPlanReference

logger = logging.getLogger(__name__)
settings = get_settings()

LESSON_PLAN_SYSTEM_PROMPT = """你是一位经验丰富的教学设计专家。

**重要规则（必须遵守）：**
在生成教案之前，请先评估用户提供的信息是否充分。如果缺少以下关键信息中的任何一项，你必须先提出澄清问题，不要直接生成教案：
- 年级/学段
- 学科
- 课题/单元主题

只有在上述关键信息都已明确时，才按照以下 Markdown 结构生成完整教案：

# {课程名称} — 教案

## 课程导入
（设计引入方式，激发学生兴趣）

## 教学目标
（知识与技能、过程与方法、情感态度与价值观）

## 知识点清单
- [ ] 知识点1
- [ ] 知识点2
（列出本课所有核心知识点，使用任务列表格式）

## 教学方法
（讲授法、讨论法、探究法等）

## 教学过程
| 环节 | 时间 | 内容 | 教师活动 | 学生活动 |
|------|------|------|---------|---------|
（使用表格详细列出每个教学环节）

## 课堂活动设计
（具体的互动活动、小组讨论等）

## 板书设计
（板书的结构和内容安排）

## 课后作业
（布置的作业内容和要求）

## 教学反思
（预设的教学反思要点）

## 课时安排
（总课时和各环节时间分配）

要求：
1. 内容要专业、准确、符合教学规范
2. 严格输出 Markdown 格式，不要输出其他格式
3. 表格必须完整，不要省略
4. 知识点清单使用 - [ ] 格式"""

LESSON_PLAN_MODIFY_PROMPT = """你是一位教学设计专家。用户提供了一份现有教案（Markdown 格式）和修改要求。
请根据修改要求对教案进行调整，输出修改后的**完整教案**（不是只输出修改部分）。
保持原有的 Markdown 结构和格式不变，仅修改用户指定的内容。
严格输出 Markdown 格式。"""


def _get_llm_config() -> tuple[str, str, str] | None:
    """Return (api_key, base_url, model) or None if not configured."""
    if settings.DASHSCOPE_API_KEY:
        return (
            settings.DASHSCOPE_API_KEY,
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            settings.LLM_MODEL,
        )
    if getattr(settings, "HTML_LLM_API_KEY", None):
        return (
            settings.HTML_LLM_API_KEY,
            (settings.HTML_LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/"),
            settings.HTML_LLM_MODEL or "gpt-4",
        )
    return None


async def stream_llm(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream LLM response using OpenAI-compatible API."""
    cfg = _get_llm_config()
    if not cfg:
        return
    api_key, base_url, model = cfg

    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "max_tokens": 8000, "stream": True}

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        content = (obj.get("choices") or [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"LLM stream error: {e}")


async def retrieve_context(
    db: AsyncSession,
    query: str,
    library_ids: list[int],
    file_ids: list[int],
    user_id: int,
) -> str:
    """Retrieve context from knowledge libraries (RAG) and uploaded reference files (DB)."""
    parts: list[str] = []

    # 1. RAG from knowledge libraries
    if library_ids:
        try:
            from app.services.rag.hybrid_retriever import get_hybrid_retriever
            retriever = get_hybrid_retriever()
            results = await retriever.search(query=query, user_id=user_id, k=5, library_ids=library_ids)
            for doc in results:
                text = doc.page_content if hasattr(doc, "page_content") else str(doc)
                parts.append(text)
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # 2. Reference file contents from DB
    if file_ids:
        try:
            result = await db.execute(
                select(LessonPlanReference).where(
                    LessonPlanReference.id.in_(file_ids),
                    LessonPlanReference.user_id == user_id,
                )
            )
            for ref in result.scalars().all():
                if ref.parsed_content:
                    parts.append(f"[参考资料: {ref.filename}]\n{ref.parsed_content}")
        except Exception as e:
            logger.warning(f"File content retrieval failed: {e}")

    return "\n\n---\n\n".join(parts) if parts else ""


async def get_chat_history(db: AsyncSession, session_id, limit: int = 10) -> list[dict]:
    """Read recent chat messages from ChatHistory table."""
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    # Reverse to chronological order
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


async def save_after_stream(plan_id: int, session_id: str, user_id: int, content: str):
    """Save AI response to DB after streaming completes. Uses a NEW session (the request session is closed)."""
    from datetime import datetime, timezone
    try:
        async with AsyncSessionLocal() as db:
            try:
                now = datetime.now(timezone.utc)
                # Update lesson plan - only write content if it looks like a lesson plan
                if content.strip().startswith("#"):
                    title = content.strip().split("\n")[0].lstrip("# ").split("—")[0].strip() or "未命名教案"
                    await db.execute(
                        update(LessonPlan)
                        .where(LessonPlan.id == plan_id)
                        .values(content=content, title=title, status="completed", updated_at=now)
                    )
                else:
                    await db.execute(
                        update(LessonPlan)
                        .where(LessonPlan.id == plan_id)
                        .values(status="draft", updated_at=now)
                    )

                # Always save AI response to ChatHistory
                db.add(ChatHistory(
                    session_id=uuid.UUID(session_id),
                    user_id=user_id,
                    role="assistant",
                    content=content,
                ))
                await db.commit()
            except Exception:
                await db.rollback()
                raise
    except Exception as e:
        logger.error(f"Failed to save after streaming: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/lesson_plan_service.py
git commit -m "feat(lesson-plan): add service with LLM streaming, RAG retrieval, and DB persistence"
```

---

### Task 6: API Routes

**Files:**
- Create: `backend/app/api/lesson_plan.py`

Key references:
- SSE response pattern: `backend/app/api/html_chat.py` (lines 51-84)
- Auth: `backend/app/core/auth.py` (line 75, `CurrentUser`)
- DB session: `backend/app/core/database.py` (line 42, `get_db`)
- Parser: `backend/app/services/parsers/factory.py` (`ParserFactory.parse_file`)

- [ ] **Step 1: Create the API route file**

```python
# backend/app/api/lesson_plan.py
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.core.auth import CurrentUser
from app.core.database import get_db
from app.models.chat_history import ChatHistory
from app.models.lesson_plan import LessonPlan
from app.models.lesson_plan_reference import LessonPlanReference
from app.schemas.lesson_plan import (
    LessonPlanExportRequest,
    LessonPlanGenerateRequest,
    LessonPlanLatestResponse,
    LessonPlanModifyRequest,
    LessonPlanSaveRequest,
    LessonPlanSaveResponse,
    LessonPlanUploadResponse,
    LessonPlanInfo,
    MessageInfo,
    FileInfo,
)
from app.services.lesson_plan_service import (
    LESSON_PLAN_MODIFY_PROMPT,
    LESSON_PLAN_SYSTEM_PROMPT,
    get_chat_history,
    retrieve_context,
    save_after_stream,
    stream_llm,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lesson-plan", tags=["lesson-plan"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


# --------------- SSE helpers ---------------

async def _sse_generate(plan_id: int, session_id: str, user_id: int, messages: list[dict]):
    """SSE generator: emit metadata, stream LLM tokens, then persist to DB."""
    yield f"data: {json.dumps({'meta': {'lesson_plan_id': plan_id, 'session_id': session_id}}, ensure_ascii=False)}\n\n"

    full = ""
    try:
        async for chunk in stream_llm(messages):
            full += chunk
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    yield "data: [DONE]\n\n"
    await save_after_stream(plan_id, session_id, user_id, full)


def _sse_response(generator):
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# --------------- 1. Generate ---------------

@router.post("/generate")
async def generate_lesson_plan(req: LessonPlanGenerateRequest, user: CurrentUser, db: DbSession):
    """Create or reuse a LessonPlan, retrieve context, stream LLM generation."""

    # 1. Create or find LessonPlan
    lesson_plan = None
    if req.session_id:
        result = await db.execute(
            select(LessonPlan).where(LessonPlan.session_id == uuid.UUID(req.session_id), LessonPlan.user_id == user.id)
        )
        lesson_plan = result.scalar_one_or_none()

    if not lesson_plan:
        lesson_plan = LessonPlan(user_id=user.id, status="generating")
        db.add(lesson_plan)
        await db.flush()

    # 2. Write user message to ChatHistory
    db.add(ChatHistory(session_id=lesson_plan.session_id, user_id=user.id, role="user", content=req.query))

    # 3. Retrieve context (RAG + reference files)
    context = await retrieve_context(db, req.query, req.library_ids, req.file_ids, user.id)

    # 4. Read existing chat history for multi-turn
    history = await get_chat_history(db, lesson_plan.session_id, limit=10)

    await db.commit()

    # 5. Build LLM messages
    messages = [{"role": "system", "content": LESSON_PLAN_SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    user_content = req.query
    if context:
        user_content = f"以下是参考资料：\n\n{context}\n\n---\n\n用户要求：{req.query}"
    # Replace last user message with enriched version (context included)
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] = user_content
    else:
        messages.append({"role": "user", "content": user_content})

    return _sse_response(_sse_generate(lesson_plan.id, str(lesson_plan.session_id), user.id, messages))


# --------------- 2. Modify ---------------

@router.post("/modify")
async def modify_lesson_plan(req: LessonPlanModifyRequest, user: CurrentUser, db: DbSession):
    """Modify existing lesson plan: read history from DB, stream LLM."""

    # Verify ownership
    result = await db.execute(
        select(LessonPlan).where(LessonPlan.id == req.lesson_plan_id, LessonPlan.user_id == user.id)
    )
    lesson_plan = result.scalar_one_or_none()
    if not lesson_plan:
        raise HTTPException(404, "教案不存在")

    # Write user instruction to ChatHistory
    db.add(ChatHistory(session_id=lesson_plan.session_id, user_id=user.id, role="user", content=req.instruction))

    # Read recent history from DB
    history = await get_chat_history(db, lesson_plan.session_id, limit=10)

    # Retrieve optional reference context
    context = await retrieve_context(db, req.instruction, req.library_ids, req.file_ids, user.id)

    await db.commit()

    # Build LLM messages
    messages = [{"role": "system", "content": LESSON_PLAN_MODIFY_PROMPT}]
    for msg in history[:-1]:  # history minus current instruction (already in prompt)
        messages.append({"role": msg["role"], "content": msg["content"]})

    user_msg = f"当前教案内容：\n\n{req.current_content}\n\n"
    if context:
        user_msg += f"参考资料：\n\n{context}\n\n"
    user_msg += f"修改要求：{req.instruction}"
    messages.append({"role": "user", "content": user_msg})

    return _sse_response(_sse_generate(lesson_plan.id, str(lesson_plan.session_id), user.id, messages))


# --------------- 3. Upload ---------------

@router.post("/upload", response_model=LessonPlanUploadResponse)
async def upload_reference_file(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    lesson_plan_id: Optional[int] = Form(None),
):
    """Upload a reference file, parse content, store in LessonPlanReference."""
    from app.services.parsers.factory import ParserFactory

    # Save to disk
    upload_dir = Path("uploads/lesson_plan")
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4()}{Path(file.filename).suffix}"
    content_bytes = await file.read()
    dest.write_bytes(content_bytes)

    # Parse
    parsed = ""
    try:
        result = await ParserFactory.parse_file(str(dest))
        if result and result.chunks:
            parsed = "\n\n".join(c.content for c in result.chunks)
    except Exception as e:
        logger.warning(f"Parse failed for {file.filename}: {e}")
        parsed = content_bytes.decode("utf-8", errors="ignore")

    # Persist
    ref = LessonPlanReference(
        user_id=user.id,
        lesson_plan_id=lesson_plan_id,
        filename=file.filename,
        file_path=str(dest),
        parsed_content=parsed,
    )
    db.add(ref)
    await db.flush()

    return LessonPlanUploadResponse(file_id=ref.id, filename=ref.filename)


# --------------- 4. Save (auto-save) ---------------

@router.patch("/{lesson_plan_id}", response_model=LessonPlanSaveResponse)
async def save_lesson_plan(lesson_plan_id: int, req: LessonPlanSaveRequest, user: CurrentUser, db: DbSession):
    """Auto-save editor content (called on blur / 30s timer)."""
    result = await db.execute(
        select(LessonPlan).where(LessonPlan.id == lesson_plan_id, LessonPlan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "教案不存在")

    if req.content is not None:
        plan.content = req.content
    if req.title is not None:
        plan.title = req.title
    await db.flush()

    return LessonPlanSaveResponse(id=plan.id, updated_at=plan.updated_at.isoformat() if plan.updated_at else "")


# --------------- 5. Load latest ---------------

@router.get("/latest", response_model=LessonPlanLatestResponse)
async def get_latest_lesson_plan(user: CurrentUser, db: DbSession):
    """Load the most recent lesson plan with its chat history and reference files."""
    result = await db.execute(
        select(LessonPlan)
        .where(LessonPlan.user_id == user.id)
        .order_by(LessonPlan.updated_at.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return LessonPlanLatestResponse()

    # Chat history
    hist_result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_id == plan.session_id)
        .order_by(ChatHistory.created_at)
    )
    msgs = [MessageInfo(role=h.role, content=h.content) for h in hist_result.scalars().all()]

    # Reference files
    files_result = await db.execute(
        select(LessonPlanReference)
        .where(LessonPlanReference.lesson_plan_id == plan.id)
    )
    files = [FileInfo(id=f.id, filename=f.filename) for f in files_result.scalars().all()]

    return LessonPlanLatestResponse(
        lesson_plan=LessonPlanInfo(
            id=plan.id,
            session_id=str(plan.session_id),
            title=plan.title,
            content=plan.content,
            status=plan.status,
        ),
        messages=msgs,
        files=files,
    )


# --------------- 6. Export DOCX ---------------

@router.post("/export/docx")
async def export_docx(req: LessonPlanExportRequest, user: CurrentUser):
    """Convert Markdown to DOCX via pypandoc."""
    import pypandoc

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name

    try:
        try:
            pypandoc.convert_text(req.content, "docx", format="md", outputfile=tmp_path)
        except OSError:
            pypandoc.download_pandoc()
            pypandoc.convert_text(req.content, "docx", format="md", outputfile=tmp_path)

        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{req.title}.docx",
            background=BackgroundTask(lambda: Path(tmp_path).unlink(missing_ok=True)),
        )
    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(500, f"DOCX 导出失败: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/lesson_plan.py
git commit -m "feat(lesson-plan): add 6 API endpoints (generate, modify, upload, save, latest, export)"
```

---

### Task 7: Register Router + Smoke Test

**Files:**
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Register the router**

Read `backend/app/api/__init__.py`. Follow the existing pattern for including routers. Add:

```python
from app.api import lesson_plan
api_router.include_router(lesson_plan.router)
```

Note: The prefix `/lesson-plan` is already set in the router definition (`APIRouter(prefix="/lesson-plan")`). If other routers in the file set prefix in `include_router()` instead, match that pattern and remove the prefix from the router definition.

- [ ] **Step 2: Smoke test**

```bash
cd backend && python run.py
```

Test with curl (replace `<token>` with a valid JWT):

```bash
# Latest (should return empty)
curl -s http://localhost:8000/api/v1/lesson-plan/latest \
  -H "Authorization: Bearer <token>" | python -m json.tool

# Generate (SSE stream)
curl -N http://localhost:8000/api/v1/lesson-plan/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我生成一份高一数学函数与方程的教案"}'
```

Verify: SSE events arrive with `meta` first, then `content` chunks, then `[DONE]`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/__init__.py
git commit -m "feat(lesson-plan): register lesson-plan router in API"
```

---

## Chunk 3: Frontend Editor + TOC

### Task 8: LessonPlanEditor Component

**Files:**
- Create: `teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue`

This is the right 2/3 panel containing:
- FloatingMenu (empty-line block type picker, Notion-like "+" menu)
- BubbleMenu (selection inline format toolbar)
- Tiptap editor with tiptap-markdown for bidirectional Markdown support
- Markdown streaming preview overlay (markdown-it)
- Top toolbar (fullscreen, copy, download MD/DOCX/PDF)

Key references:
- Existing color palette: primary blue `#2563eb`, light blue `#dbeafe`, grays `#f1f5f9`
- Download pattern: `resolveApiUrl` + `getToken` from `api/http.js`

- [ ] **Step 1: Create the editor component**

```vue
<!-- teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue -->
<template>
  <div :class="['editor-panel', { 'editor-fullscreen': isFullscreen }]">
    <!-- Toolbar -->
    <div class="editor-toolbar" v-if="hasContent || isStreaming">
      <div class="toolbar-left">
        <span class="char-count" v-if="charCount > 0">{{ charCount }} 字</span>
      </div>
      <div class="toolbar-right">
        <button class="toolbar-btn" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏'">
          {{ isFullscreen ? '退出全屏' : '全屏' }}
        </button>
        <button class="toolbar-btn" @click="copyContent" :disabled="!hasContent">复制</button>
        <div class="download-group" v-if="hasContent">
          <button class="toolbar-btn" @click="showDownloadMenu = !showDownloadMenu">下载 ▾</button>
          <div class="download-menu" v-if="showDownloadMenu">
            <button @click="downloadMd">Markdown</button>
            <button @click="downloadDocx">Word 文档</button>
            <button @click="downloadPdf">PDF</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Streaming preview overlay (markdown-it rendered) -->
    <div class="streaming-preview" v-if="isStreaming" v-html="previewHtml"></div>

    <!-- Tiptap editor (hidden during streaming) -->
    <div class="editor-container" v-show="!isStreaming && editorReady">
      <!-- FloatingMenu: appears on empty lines -->
      <floating-menu :editor="editor" :tippy-options="{ duration: 100 }" v-if="editor">
        <div class="floating-menu">
          <button @click="editor.chain().focus().toggleHeading({ level: 2 }).run()">H2</button>
          <button @click="editor.chain().focus().toggleHeading({ level: 3 }).run()">H3</button>
          <button @click="editor.chain().focus().toggleBulletList().run()">列表</button>
          <button @click="editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()">表格</button>
          <button @click="editor.chain().focus().toggleTaskList().run()">清单</button>
        </div>
      </floating-menu>

      <!-- BubbleMenu: appears on text selection -->
      <bubble-menu :editor="editor" :tippy-options="{ duration: 100 }" v-if="editor">
        <div class="bubble-menu">
          <button @click="editor.chain().focus().toggleBold().run()" :class="{ active: editor.isActive('bold') }">B</button>
          <button @click="editor.chain().focus().toggleItalic().run()" :class="{ active: editor.isActive('italic') }">I</button>
          <button @click="editor.chain().focus().toggleUnderline().run()" :class="{ active: editor.isActive('underline') }">U</button>
          <button @click="editor.chain().focus().toggleHighlight().run()" :class="{ active: editor.isActive('highlight') }">高亮</button>
        </div>
      </bubble-menu>

      <editor-content :editor="editor" class="tiptap-content" />
    </div>

    <!-- Empty state -->
    <div class="editor-empty" v-if="!hasContent && !isStreaming && editorReady">
      <p class="empty-title">教案将在此处显示</p>
      <p class="empty-desc">在左侧对话框中描述您的教学需求，AI 将为您生成教案</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, onDeactivated, shallowRef } from 'vue'
import { EditorContent, FloatingMenu, BubbleMenu, Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import Highlight from '@tiptap/extension-highlight'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import CharacterCount from '@tiptap/extension-character-count'
import { Markdown } from 'tiptap-markdown'
import MarkdownIt from 'markdown-it'
import taskListPlugin from 'markdown-it-task-lists'

const md = new MarkdownIt().use(taskListPlugin)

const props = defineProps({
  isStreaming: { type: Boolean, default: false },
  streamingMarkdown: { type: String, default: '' },
})

const emit = defineEmits(['update:markdown', 'update:headings', 'blur'])

const isFullscreen = ref(false)
const showDownloadMenu = ref(false)
const editor = shallowRef(null)
const editorReady = ref(false)

const editorExtensions = [
  StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
  Placeholder.configure({ placeholder: '教案内容将在这里显示...' }),
  Table.configure({ resizable: true }),
  TableRow,
  TableCell,
  TableHeader,
  TaskList,
  TaskItem.configure({ nested: true }),
  Highlight,
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  Underline,
  CharacterCount,
  Markdown,
]

function createEditor(content = '') {
  if (editor.value) editor.value.destroy()
  editor.value = new Editor({
    extensions: editorExtensions,
    content,
    editable: true,
    onUpdate: () => {
      const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
      emit('update:markdown', mkdown)
      extractHeadings()
    },
    onBlur: () => emit('blur'),
  })
  editorReady.value = true
}

onMounted(() => createEditor())

const hasContent = computed(() => editor.value ? !editor.value.isEmpty : false)
const charCount = computed(() => editor.value?.storage.characterCount.characters() || 0)
const previewHtml = computed(() => md.render(props.streamingMarkdown || ''))

// When streaming ends, inject final markdown into Tiptap
watch(() => props.isStreaming, (now, was) => {
  if (was && !now && props.streamingMarkdown) {
    editor.value?.commands.setContent(props.streamingMarkdown)
    editor.value?.setEditable(true)
    extractHeadings()
  }
})

// Lock editor when streaming starts
watch(() => props.isStreaming, (streaming) => {
  if (streaming) editor.value?.setEditable(false)
})

function extractHeadings() {
  if (!editor.value) return
  const headings = []
  editor.value.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      headings.push({ level: node.attrs.level, text: node.textContent, pos })
    }
  })
  emit('update:headings', headings)
}

function toggleFullscreen() { isFullscreen.value = !isFullscreen.value }

async function copyContent() {
  const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
  await navigator.clipboard.writeText(mkdown)
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function downloadMd() {
  showDownloadMenu.value = false
  const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
  downloadBlob(new Blob([mkdown], { type: 'text/markdown;charset=utf-8' }), '教案.md')
}

async function downloadDocx() {
  showDownloadMenu.value = false
  const { resolveApiUrl, getToken } = await import('@/api/http.js')
  const mkdown = editor.value?.storage.markdown.getMarkdown() || ''
  const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/export/docx'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify({ content: mkdown, title: '教案' }),
  })
  if (!res.ok) return
  downloadBlob(await res.blob(), '教案.docx')
}

async function downloadPdf() {
  showDownloadMenu.value = false
  const html2pdf = (await import('html2pdf.js')).default
  const el = document.querySelector('.tiptap-content .ProseMirror')
  if (!el) return
  html2pdf().set({ margin: 10, filename: '教案.pdf', html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a4' } }).from(el).save()
}

// --- Exposed methods for parent ---
function getMarkdown() { return editor.value?.storage.markdown.getMarkdown() || '' }
function loadContent(markdown) { createEditor(markdown) }
function scrollToPos(pos) {
  const view = editor.value?.view
  if (!view) return
  const coords = view.coordsAtPos(pos)
  const container = view.dom.closest('.editor-container')
  if (container) container.scrollTo({ top: coords.top - container.getBoundingClientRect().top + container.scrollTop - 20, behavior: 'smooth' })
}

onDeactivated(() => { editor.value?.destroy(); editor.value = null; editorReady.value = false })
onBeforeUnmount(() => { editor.value?.destroy() })

defineExpose({ getMarkdown, loadContent, scrollToPos })
</script>

<style scoped>
.editor-panel { display: flex; flex-direction: column; height: 100%; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; }
.editor-fullscreen { position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000; border-radius: 0; }
.editor-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; flex-shrink: 0; }
.toolbar-left, .toolbar-right { display: flex; align-items: center; gap: 8px; }
.char-count { font-size: 0.8rem; color: #94a3b8; }
.toolbar-btn { padding: 4px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; font-size: 0.85rem; color: #475569; cursor: pointer; }
.toolbar-btn:hover { background: #f1f5f9; }
.toolbar-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.download-group { position: relative; }
.download-menu { position: absolute; top: 100%; right: 0; margin-top: 4px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 10; overflow: hidden; }
.download-menu button { display: block; width: 100%; padding: 8px 20px; border: none; background: none; font-size: 0.85rem; color: #334155; cursor: pointer; text-align: left; white-space: nowrap; }
.download-menu button:hover { background: #f1f5f9; }

.streaming-preview { flex: 1; overflow-y: auto; padding: 24px 32px; font-size: 0.95rem; line-height: 1.7; color: #1e293b; }
.streaming-preview :deep(h1) { font-size: 1.5rem; font-weight: 700; margin: 1.5em 0 0.5em; }
.streaming-preview :deep(h2) { font-size: 1.25rem; font-weight: 600; margin: 1.2em 0 0.4em; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }
.streaming-preview :deep(table) { border-collapse: collapse; width: 100%; margin: 1em 0; }
.streaming-preview :deep(th), .streaming-preview :deep(td) { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
.streaming-preview :deep(th) { background: #f1f5f9; font-weight: 600; }

.editor-container { flex: 1; overflow-y: auto; }
.tiptap-content :deep(.ProseMirror) { padding: 24px 32px; min-height: 100%; outline: none; font-size: 0.95rem; line-height: 1.7; color: #1e293b; }
.tiptap-content :deep(.ProseMirror h1) { font-size: 1.5rem; font-weight: 700; margin: 1.5em 0 0.5em; color: #0f172a; }
.tiptap-content :deep(.ProseMirror h2) { font-size: 1.25rem; font-weight: 600; margin: 1.2em 0 0.4em; color: #1e293b; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }
.tiptap-content :deep(.ProseMirror h3) { font-size: 1.1rem; font-weight: 600; margin: 1em 0 0.3em; color: #334155; }
.tiptap-content :deep(.ProseMirror table) { border-collapse: collapse; width: 100%; margin: 1em 0; }
.tiptap-content :deep(.ProseMirror th), .tiptap-content :deep(.ProseMirror td) { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
.tiptap-content :deep(.ProseMirror th) { background: #f1f5f9; font-weight: 600; }
.tiptap-content :deep(.ProseMirror ul[data-type="taskList"]) { list-style: none; padding-left: 0; }
.tiptap-content :deep(.ProseMirror ul[data-type="taskList"] li) { display: flex; align-items: flex-start; gap: 8px; }
.tiptap-content :deep(.ProseMirror p.is-editor-empty:first-child::before) { content: attr(data-placeholder); color: #94a3b8; pointer-events: none; float: left; height: 0; }

.floating-menu { display: flex; gap: 4px; padding: 4px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.floating-menu button { padding: 4px 10px; border: none; background: none; font-size: 0.8rem; color: #64748b; cursor: pointer; border-radius: 4px; }
.floating-menu button:hover { background: #f1f5f9; color: #2563eb; }

.bubble-menu { display: flex; gap: 2px; padding: 4px; background: #1e293b; border-radius: 8px; }
.bubble-menu button { padding: 4px 8px; border: none; background: none; color: #e2e8f0; cursor: pointer; font-size: 0.8rem; border-radius: 4px; font-weight: 600; }
.bubble-menu button:hover, .bubble-menu button.active { background: #475569; color: #fff; }

.editor-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #94a3b8; padding: 40px; }
.empty-title { font-size: 1.1rem; font-weight: 500; color: #64748b; margin-bottom: 8px; }
.empty-desc { font-size: 0.9rem; color: #94a3b8; text-align: center; }
</style>
```

- [ ] **Step 2: Verify Tiptap renders**

```bash
cd teacher-platform && npm run dev
```

Temporarily import the editor in any existing page to verify Tiptap initializes without errors and FloatingMenu/BubbleMenu appear.

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue
git commit -m "feat(lesson-plan): add Tiptap editor with FloatingMenu, BubbleMenu, toolbar, streaming preview"
```

---

### Task 9: LessonPlanTOC Component

**Files:**
- Create: `teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue`

Features: collapsible sidebar, Intersection Observer for active heading highlight, pauses during streaming.

- [ ] **Step 1: Create the TOC component**

```vue
<!-- teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue -->
<template>
  <div :class="['toc-panel', { 'toc-collapsed': collapsed }]">
    <div class="toc-header">
      <span v-if="!collapsed" class="toc-title">目录</span>
      <button class="toc-toggle" @click="collapsed = !collapsed" :title="collapsed ? '展开目录' : '收起目录'">
        {{ collapsed ? '▶' : '◀' }}
      </button>
    </div>
    <ul class="toc-list" v-if="!collapsed && headings.length > 0">
      <li
        v-for="(h, idx) in headings"
        :key="idx"
        :class="['toc-item', `toc-level-${h.level}`, { active: activeIndex === idx }]"
        @click="$emit('scroll-to', h.pos)"
      >
        {{ h.text }}
      </li>
    </ul>
    <p class="toc-empty" v-if="!collapsed && headings.length === 0">暂无目录</p>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, onDeactivated } from 'vue'

const props = defineProps({
  headings: { type: Array, default: () => [] },
  isStreaming: { type: Boolean, default: false },
})
defineEmits(['scroll-to'])

const collapsed = ref(false)
const activeIndex = ref(-1)
let observer = null

function setupObserver() {
  if (observer) observer.disconnect()
  if (props.isStreaming || props.headings.length === 0) return

  // Find all heading elements in the editor
  const editorEl = document.querySelector('.tiptap-content .ProseMirror')
  if (!editorEl) return

  const headingEls = editorEl.querySelectorAll('h1, h2, h3')
  if (headingEls.length === 0) return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const idx = Array.from(headingEls).indexOf(entry.target)
          if (idx !== -1) activeIndex.value = idx
        }
      }
    },
    { root: editorEl.closest('.editor-container'), rootMargin: '-10% 0px -80% 0px', threshold: 0 }
  )

  headingEls.forEach((el) => observer.observe(el))
}

// Re-setup observer when headings change (but not during streaming)
watch(() => [props.headings, props.isStreaming], () => {
  if (!props.isStreaming) {
    // Small delay to let DOM update
    setTimeout(setupObserver, 100)
  }
}, { deep: true })

onMounted(() => setupObserver())
onDeactivated(() => { if (observer) observer.disconnect() })
onBeforeUnmount(() => { if (observer) observer.disconnect() })
</script>

<style scoped>
.toc-panel { width: 180px; border-right: 1px solid #e2e8f0; background: #f8fafc; display: flex; flex-direction: column; flex-shrink: 0; transition: width 0.2s ease; overflow: hidden; }
.toc-collapsed { width: 36px; }
.toc-header { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-bottom: 1px solid #e2e8f0; }
.toc-title { font-size: 0.85rem; font-weight: 600; color: #475569; }
.toc-toggle { width: 24px; height: 24px; border: none; background: none; color: #94a3b8; cursor: pointer; font-size: 0.75rem; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
.toc-toggle:hover { background: #e2e8f0; color: #475569; }
.toc-list { list-style: none; padding: 8px 0; margin: 0; overflow-y: auto; flex: 1; }
.toc-item { padding: 6px 16px; font-size: 0.82rem; color: #64748b; cursor: pointer; border-left: 2px solid transparent; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.toc-item:hover { color: #2563eb; background: #eff6ff; }
.toc-item.active { color: #2563eb; border-left-color: #2563eb; font-weight: 500; }
.toc-level-2 { padding-left: 16px; }
.toc-level-3 { padding-left: 28px; font-size: 0.78rem; }
.toc-empty { padding: 16px; font-size: 0.82rem; color: #94a3b8; text-align: center; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue
git commit -m "feat(lesson-plan): add collapsible TOC sidebar with IntersectionObserver active highlight"
```

---

## Chunk 4: Frontend Chat Panel

### Task 10: LessonPlanChat Component

**Files:**
- Create: `teacher-platform/src/components/lesson-plan/LessonPlanChat.vue`

Key references:
- Chat bubble styling: user `#E0EDFE`, AI `#f1f5f9` (matching existing project style)
- Voice input: `composables/useVoiceInput.js` (takes a ref, returns `{ isRecording, isSupported, toggleRecording }`)
- Knowledge library API: `GET /api/v1/libraries?scope=personal` and `?scope=system`
- File upload: `POST /api/v1/lesson-plan/upload`

- [ ] **Step 1: Create the chat component**

```vue
<!-- teacher-platform/src/components/lesson-plan/LessonPlanChat.vue -->
<template>
  <div class="chat-panel">
    <!-- Messages -->
    <div class="messages-area" ref="messagesRef">
      <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', msg.role]">
        <div class="msg-label">{{ msg.role === 'user' ? '我' : 'AI 助手' }}</div>
        <div class="msg-bubble" v-html="renderMsg(msg.content)"></div>
      </div>
      <!-- Loading bubble during streaming -->
      <div v-if="isSending" class="msg assistant">
        <div class="msg-label">AI 助手</div>
        <div class="msg-bubble loading-bubble">
          <span class="dot-anim">{{ hasContent ? '正在修改教案' : '正在生成教案' }}</span>
        </div>
      </div>
    </div>

    <!-- Tags: uploaded files + selected knowledge bases -->
    <div class="tags-area" v-if="uploadedFiles.length > 0 || selectedLibraries.length > 0">
      <span v-for="f in uploadedFiles" :key="'f' + f.file_id" class="tag file-tag">
        {{ f.filename }}
        <button class="tag-remove" @click="removeFile(f.file_id)">&times;</button>
      </span>
      <span v-for="lib in selectedLibraries" :key="'l' + lib.id" :class="['tag', lib.type === 'system' ? 'system-tag' : 'user-tag']">
        {{ lib.name }}
        <button class="tag-remove" @click="removeLibrary(lib.id)">&times;</button>
      </span>
    </div>

    <!-- Input area -->
    <div class="input-area">
      <textarea
        ref="inputRef"
        v-model="inputText"
        :placeholder="hasContent ? '输入修改要求...' : '描述您的教学需求，例如：帮我生成一份高一数学函数与方程的教案'"
        rows="3"
        @keydown.enter.exact.prevent="handleSend"
        :disabled="isSending"
      ></textarea>
      <div class="input-actions">
        <button class="action-btn" @click="triggerFileUpload" :disabled="isSending" title="上传参考资料">
          &#128206;
        </button>
        <button class="action-btn" @click="showLibPicker = !showLibPicker" :disabled="isSending" title="选择知识库">
          &#128218;
        </button>
        <button :class="['action-btn', { recording: isRecording }]" @click="toggleRecording" :disabled="isSending" title="语音输入">
          &#127908;
        </button>
        <button class="send-btn" @click="handleSend" :disabled="isSending || !inputText.trim()">发送</button>
      </div>
    </div>

    <!-- Knowledge base picker dropdown -->
    <div class="lib-picker" v-if="showLibPicker" @click.stop>
      <div class="lib-group" v-if="userLibs.length > 0">
        <div class="lib-group-title">&#128193; 我的知识库</div>
        <label v-for="lib in userLibs" :key="lib.id" class="lib-item">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          <span>{{ lib.name }}</span>
        </label>
      </div>
      <div class="lib-divider" v-if="userLibs.length > 0 && sysLibs.length > 0"></div>
      <div class="lib-group" v-if="sysLibs.length > 0">
        <div class="lib-group-title">&#127760; 公开知识库</div>
        <label v-for="lib in sysLibs" :key="lib.id" class="lib-item">
          <input type="checkbox" :value="lib.id" v-model="selectedLibIds" />
          <span>{{ lib.name }}</span>
        </label>
      </div>
      <p class="lib-empty" v-if="userLibs.length === 0 && sysLibs.length === 0">暂无知识库</p>
    </div>

    <!-- Hidden file input (no .pptx - parser unsupported) -->
    <input ref="fileInputRef" type="file" hidden accept=".pdf,.docx,.doc,.png,.jpg,.jpeg" @change="handleFileUpload" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { resolveApiUrl, getToken } from '@/api/http.js'
import { useVoiceInput } from '@/composables/useVoiceInput.js'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  isSending: { type: Boolean, default: false },
  hasContent: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'send-modify'])

const inputText = ref('')
const messagesRef = ref(null)
const inputRef = ref(null)
const fileInputRef = ref(null)
const showLibPicker = ref(false)
const uploadedFiles = ref([])
const selectedLibIds = ref([])
const userLibs = ref([])
const sysLibs = ref([])

const { isRecording, toggleRecording } = useVoiceInput(inputText)

const selectedLibraries = computed(() => {
  const all = [...userLibs.value, ...sysLibs.value]
  return all.filter((lib) => selectedLibIds.value.includes(lib.id))
})

// Auto-scroll messages on new entries
watch(() => props.messages.length, () => {
  nextTick(() => { if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight })
})

async function fetchLibraries() {
  try {
    const headers = { Authorization: `Bearer ${getToken()}` }
    const [uRes, sRes] = await Promise.all([
      fetch(resolveApiUrl('/api/v1/libraries?scope=personal'), { headers }),
      fetch(resolveApiUrl('/api/v1/libraries?scope=system'), { headers }),
    ])
    if (uRes.ok) {
      const d = await uRes.json()
      userLibs.value = (d.items || d || []).map((lib) => ({ ...lib, type: 'user' }))
    }
    if (sRes.ok) {
      const d = await sRes.json()
      sysLibs.value = (d.items || d || []).map((lib) => ({ ...lib, type: 'system' }))
    }
  } catch (e) {
    console.warn('Failed to fetch libraries:', e)
  }
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.isSending) return
  const payload = {
    text,
    file_ids: uploadedFiles.value.map((f) => f.file_id),
    library_ids: selectedLibIds.value,
  }
  emit(props.hasContent ? 'send-modify' : 'send', payload)
  inputText.value = ''
}

function triggerFileUpload() { fileInputRef.value?.click() }

async function handleFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/upload'), {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: formData,
    })
    if (!res.ok) throw new Error('Upload failed')
    const data = await res.json()
    uploadedFiles.value.push(data)
  } catch (e) {
    console.error('File upload failed:', e)
  }
  fileInputRef.value.value = ''
}

function removeFile(fid) { uploadedFiles.value = uploadedFiles.value.filter((f) => f.file_id !== fid) }
function removeLibrary(lid) { selectedLibIds.value = selectedLibIds.value.filter((id) => id !== lid) }
function renderMsg(content) { return content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') }

// Restore uploaded files from parent (after GET /latest)
function restoreFiles(files) { uploadedFiles.value = files }

function handleClickOutside(e) {
  if (showLibPicker.value && !e.target.closest('.lib-picker') && !e.target.closest('.action-btn')) {
    showLibPicker.value = false
  }
}

onMounted(() => {
  fetchLibraries()
  document.addEventListener('click', handleClickOutside)
})
onBeforeUnmount(() => { document.removeEventListener('click', handleClickOutside) })

defineExpose({ restoreFiles })
</script>

<style scoped>
.chat-panel { display: flex; flex-direction: column; height: 100%; background: #fff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; position: relative; }
.messages-area { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.msg { display: flex; flex-direction: column; gap: 4px; }
.msg.user { align-items: flex-end; }
.msg.assistant { align-items: flex-start; }
.msg-label { font-size: 0.75rem; color: #94a3b8; padding: 0 4px; }
.msg-bubble { max-width: 90%; padding: 10px 14px; border-radius: 12px; font-size: 0.9rem; line-height: 1.6; word-break: break-word; }
.msg.user .msg-bubble { background: #E0EDFE; color: #1e293b; border-bottom-right-radius: 4px; }
.msg.assistant .msg-bubble { background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
.loading-bubble .dot-anim::after { content: ''; animation: dots 1.5s steps(3) infinite; }
@keyframes dots { 0% { content: ''; } 33% { content: '.'; } 66% { content: '..'; } 100% { content: '...'; } }

.tags-area { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 16px; border-top: 1px solid #f1f5f9; }
.tag { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; }
.file-tag { background: #f1f5f9; color: #475569; }
.user-tag { background: #dbeafe; color: #2563eb; }
.system-tag { background: #d1fae5; color: #059669; }
.tag-remove { border: none; background: none; cursor: pointer; font-size: 0.85rem; color: inherit; opacity: 0.6; padding: 0 2px; }
.tag-remove:hover { opacity: 1; }

.input-area { padding: 12px 16px; border-top: 1px solid #e2e8f0; }
.input-area textarea { width: 100%; resize: none; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; font-size: 0.9rem; font-family: inherit; outline: none; }
.input-area textarea:focus { border-color: #93c5fd; }
.input-actions { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.action-btn { width: 32px; height: 32px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 1rem; }
.action-btn:hover { background: #f1f5f9; }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-btn.recording { background: #fee2e2; border-color: #fca5a5; }
.send-btn { margin-left: auto; padding: 6px 20px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-size: 0.85rem; cursor: pointer; }
.send-btn:hover { background: #1d4ed8; }
.send-btn:disabled { background: #93c5fd; cursor: not-allowed; }

.lib-picker { position: absolute; bottom: 120px; left: 16px; right: 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); z-index: 20; max-height: 240px; overflow-y: auto; padding: 8px 0; }
.lib-group-title { padding: 8px 16px 4px; font-size: 0.78rem; font-weight: 600; color: #94a3b8; }
.lib-item { display: flex; align-items: center; gap: 8px; padding: 6px 16px; font-size: 0.85rem; color: #334155; cursor: pointer; }
.lib-item:hover { background: #f8fafc; }
.lib-item input[type="checkbox"] { accent-color: #2563eb; }
.lib-divider { height: 1px; background: #e2e8f0; margin: 4px 12px; }
.lib-empty { padding: 16px; text-align: center; font-size: 0.82rem; color: #94a3b8; }
</style>
```

- [ ] **Step 2: Verify knowledge library endpoint**

Read `backend/app/api/libraries.py` to confirm `GET /api/v1/libraries?scope=personal` and `?scope=system` exist and return `{ items: [{ id, name, ... }] }`. The component already handles both `data.items` and raw array responses.

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan/LessonPlanChat.vue
git commit -m "feat(lesson-plan): add chat panel with knowledge picker, file upload, voice input"
```

---

## Chunk 5: Main Container + Integration

### Task 11: LessonPrepLessonPlan Main Container

**Files:**
- Create: `teacher-platform/src/views/LessonPrepLessonPlan.vue`

This component orchestrates:
- Three-column layout (TOC + Chat + Editor)
- SSE streaming with metadata parsing (`lesson_plan_id`, `session_id`)
- `res.ok` check before reading SSE stream (spec requirement)
- DB-based data loading on activation (`GET /latest`)
- Auto-save (30s debounce + blur + deactivation)
- Error rollback for failed modifications

Key references:
- SSE fetch pattern: `LessonPrepAnimation.vue` (lines 212-280)
- AbortController pattern: `LessonPrepAnimation.vue` (line 212)

- [ ] **Step 1: Create the main container component**

```vue
<!-- teacher-platform/src/views/LessonPrepLessonPlan.vue -->
<template>
  <div class="lesson-plan-page">
    <LessonPlanTOC
      :headings="headings"
      :is-streaming="isSending"
      @scroll-to="handleScrollTo"
    />
    <div class="chat-column">
      <LessonPlanChat
        ref="chatRef"
        :messages="messages"
        :is-sending="isSending"
        :has-content="hasEditorContent"
        @send="handleGenerate"
        @send-modify="handleModify"
      />
    </div>
    <div class="editor-column">
      <LessonPlanEditor
        ref="editorRef"
        :is-streaming="isSending"
        :streaming-markdown="streamingMarkdown"
        @update:markdown="handleMarkdownUpdate"
        @update:headings="headings = $event"
        @blur="autoSave"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { resolveApiUrl, getToken } from '@/api/http.js'
import LessonPlanChat from '@/components/lesson-plan/LessonPlanChat.vue'
import LessonPlanEditor from '@/components/lesson-plan/LessonPlanEditor.vue'
import LessonPlanTOC from '@/components/lesson-plan/LessonPlanTOC.vue'

const editorRef = ref(null)
const chatRef = ref(null)
const messages = ref([])
const isSending = ref(false)
const streamingMarkdown = ref('')
const currentMarkdown = ref('')
const headings = ref([])
const lessonPlanId = ref(null)
const sessionId = ref(null)

let abortController = null
let saveTimer = null
let isFirstMount = true

const hasEditorContent = computed(() => currentMarkdown.value.trim().length > 0)

// ---------- Data loading (from DB) ----------

async function loadLatestPlan() {
  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/latest'), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) return

    const data = await res.json()
    if (data.lesson_plan) {
      lessonPlanId.value = data.lesson_plan.id
      sessionId.value = data.lesson_plan.session_id
      currentMarkdown.value = data.lesson_plan.content || ''
      editorRef.value?.loadContent(currentMarkdown.value)
    } else {
      lessonPlanId.value = null
      sessionId.value = null
      currentMarkdown.value = ''
      editorRef.value?.loadContent('')
    }
    messages.value = (data.messages || []).map((m) => ({ role: m.role, content: m.content }))
    chatRef.value?.restoreFiles((data.files || []).map((f) => ({ file_id: f.id, filename: f.filename })))
  } catch (e) {
    console.error('Failed to load latest plan:', e)
  }
}

// ---------- SSE processing ----------

async function processSSEStream(res) {
  if (!res.ok) throw new Error(res.statusText || `HTTP ${res.status}`)

  const reader = res.body?.getReader()
  if (!reader) throw new Error('No reader available')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (value) buffer += decoder.decode(value, { stream: true })

    const events = buffer.split('\n\n')
    buffer = events.pop() || ''

    for (const ev of events) {
      const line = ev.split('\n')[0]
      if (!line?.startsWith('data: ')) continue

      const raw = line.slice(6).trim()
      if (raw === '[DONE]') return

      try {
        const data = JSON.parse(raw)
        // Metadata event (first event from generate)
        if (data.meta) {
          lessonPlanId.value = data.meta.lesson_plan_id
          sessionId.value = data.meta.session_id
          continue
        }
        if (data.error) throw new Error(data.error)
        if (data.content) streamingMarkdown.value += data.content
      } catch (parseErr) {
        if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr
      }
    }

    if (done) {
      // Process final buffer
      if (buffer.trim()) {
        const line = buffer.split('\n')[0]
        if (line?.startsWith('data: ')) {
          const raw = line.slice(6).trim()
          if (raw !== '[DONE]') {
            try {
              const data = JSON.parse(raw)
              if (data.content) streamingMarkdown.value += data.content
            } catch (_) {}
          }
        }
      }
      break
    }
  }
}

// ---------- Generate ----------

async function handleGenerate(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  isSending.value = true
  streamingMarkdown.value = ''
  abortController = new AbortController()

  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/generate'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({
        query: payload.text,
        library_ids: payload.library_ids || [],
        file_ids: payload.file_ids || [],
        session_id: sessionId.value || undefined,
      }),
      signal: abortController.signal,
    })

    await processSSEStream(res)

    // Determine if response is a lesson plan or clarifying question
    const isLessonPlan = streamingMarkdown.value.trim().startsWith('#')
    if (isLessonPlan) {
      currentMarkdown.value = streamingMarkdown.value
      // Show real AI content in chat (truncated for readability, full content in editor)
      const title = streamingMarkdown.value.match(/^#\s+(.+)/m)?.[1] || '教案'
      messages.value.push({ role: 'assistant', content: `已为您生成「${title}」，请在右侧编辑器中查看和编辑。如需修改，请直接告诉我。` })
    } else {
      // AI asked a clarifying question - show full real content in chat
      messages.value.push({ role: 'assistant', content: streamingMarkdown.value })
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Generate failed:', e)
      messages.value.push({ role: 'assistant', content: `生成失败: ${e.message}` })
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

// ---------- Modify ----------

async function handleModify(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  isSending.value = true
  streamingMarkdown.value = ''
  const backupMarkdown = editorRef.value?.getMarkdown() || ''
  abortController = new AbortController()

  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/modify'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({
        lesson_plan_id: lessonPlanId.value,
        instruction: payload.text,
        current_content: backupMarkdown,
        file_ids: payload.file_ids || [],
        library_ids: payload.library_ids || [],
      }),
      signal: abortController.signal,
    })

    await processSSEStream(res)
    currentMarkdown.value = streamingMarkdown.value
    // Show real content excerpt in chat (full response stored in ChatHistory by backend)
    const excerpt = streamingMarkdown.value.slice(0, 150).trim()
    messages.value.push({ role: 'assistant', content: excerpt + (streamingMarkdown.value.length > 150 ? '...\n\n*已在右侧编辑器中更新*' : '') })
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Modify failed:', e)
      messages.value.push({ role: 'assistant', content: `修改失败: ${e.message}` })
      editorRef.value?.loadContent(backupMarkdown)
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

// ---------- Auto-save ----------

function handleMarkdownUpdate(markdown) {
  currentMarkdown.value = markdown
  scheduleAutoSave()
}

function scheduleAutoSave() {
  if (!lessonPlanId.value || isSending.value) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(autoSave, 30000)
}

async function autoSave() {
  if (!lessonPlanId.value || isSending.value) return
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null }
  try {
    await fetch(resolveApiUrl(`/api/v1/lesson-plan/${lessonPlanId.value}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ content: currentMarkdown.value }),
    })
  } catch (e) {
    console.warn('Auto-save failed:', e)
  }
}

function handleScrollTo(pos) { editorRef.value?.scrollToPos(pos) }

// ---------- Lifecycle ----------

onMounted(async () => {
  isFirstMount = true
  await loadLatestPlan()
})

onActivated(async () => {
  if (isFirstMount) { isFirstMount = false; return }
  await loadLatestPlan()
})

onDeactivated(() => {
  abortController?.abort()
  autoSave()
})

onBeforeUnmount(() => {
  abortController?.abort()
  if (saveTimer) clearTimeout(saveTimer)
})
</script>

<style scoped>
.lesson-plan-page { display: flex; height: calc(100vh - 60px); gap: 0; background: #f1f5f9; padding: 16px; }
.chat-column { width: 33%; min-width: 300px; max-width: 420px; flex-shrink: 0; padding: 0 12px; }
.editor-column { flex: 1; min-width: 0; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/views/LessonPrepLessonPlan.vue
git commit -m "feat(lesson-plan): add main container with SSE streaming, DB lifecycle, auto-save"
```

---

### Task 12: Tab + Sidebar Integration

**Files:**
- Modify: `teacher-platform/src/views/LessonPrep.vue`
- Modify: `teacher-platform/src/components/LayoutWithNav.vue`

- [ ] **Step 1: Update LessonPrep.vue**

Read the full file first. Then:

1. Add import at the top with the other component imports:

```javascript
import LessonPrepLessonPlan from './LessonPrepLessonPlan.vue'
```

2. Insert into the `tabs` array at index 1 (between ppt and animation):

```javascript
{ id: 'lesson-plan', label: '教案生成' },
```

3. Add to the `currentComponent` computed map:

```javascript
'lesson-plan': LessonPrepLessonPlan,
```

4. Add to the `resetKeys` ref:

```javascript
'lesson-plan': 0,
```

- [ ] **Step 2: Update LayoutWithNav.vue sidebar**

Read the full file first. Insert into the `lessonPrepTabs` array at index 1 (between ppt and animation):

```javascript
{ id: 'lesson-plan', label: '教案生成', icon: 'lesson-plan' },
```

- [ ] **Step 3: Verify tab switching**

```bash
cd teacher-platform && npm run dev
```

Navigate to `/lesson-prep?tab=lesson-plan` and verify:
- Tab is visible in sidebar between PPT and animation
- The three-column layout renders (TOC + Chat + Editor)
- Switching to another tab and back preserves state (keep-alive reloads from DB)

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/views/LessonPrep.vue teacher-platform/src/components/LayoutWithNav.vue
git commit -m "feat(lesson-plan): integrate lesson plan tab into LessonPrep and sidebar navigation"
```

---

### Task 13: End-to-End Verification

- [ ] **Step 1: Start backend**

```bash
cd backend && python run.py
```

- [ ] **Step 2: Start frontend**

```bash
cd teacher-platform && npm run dev
```

- [ ] **Step 3: Test initial generation**

1. Navigate to `/lesson-prep?tab=lesson-plan`
2. Type "帮我生成一份高一数学函数与方程的教案"
3. Click send
4. Verify: SSE metadata arrives (check browser DevTools Network tab for `lesson_plan_id`)
5. Verify: streaming preview shows markdown content in right panel
6. Verify: after `[DONE]`, Tiptap editor loads the content
7. Verify: TOC shows heading structure
8. Verify: ChatHistory in PostgreSQL has both user and assistant messages

- [ ] **Step 4: Test AI clarification**

1. Type a vague request like "帮我生成一份教案" (missing subject/grade)
2. Verify: AI asks clarifying questions in chat instead of generating
3. Answer the question, send again
4. Verify: AI generates the lesson plan this time

- [ ] **Step 5: Test modification**

1. Type "把教学目标改为三维目标的形式"
2. Verify: right panel shows updated content streaming
3. Verify: editor updates when done
4. Verify: ChatHistory has the modification exchange

- [ ] **Step 6: Test manual editing + auto-save**

1. Click in the editor and modify text
2. Verify: TOC updates when headings change
3. Wait 30s or click outside editor
4. Verify: PATCH request appears in Network tab
5. Refresh the page, return to lesson-plan tab
6. Verify: edited content is restored from DB

- [ ] **Step 7: Test export**

1. Click "下载" button in toolbar
2. Test "Markdown" - verify `.md` file content is correct
3. Test "Word 文档" - verify `.docx` file opens correctly
4. Test "PDF" - verify PDF is generated from editor content

- [ ] **Step 8: Test knowledge base picker**

1. Click the knowledge base button
2. Verify: user and system libraries shown in grouped sections
3. Select libraries, verify tags appear above input
4. Verify: `library_ids` are included in the generate request

- [ ] **Step 9: Test file upload**

1. Click upload button, select a PDF file
2. Verify: file tag appears in chat panel
3. Send a generate request
4. Verify: `file_ids` are included in the request
5. Check `lesson_plan_references` table in PostgreSQL

- [ ] **Step 10: Test tab lifecycle**

1. Generate a lesson plan on the lesson-plan tab
2. Switch to the PPT tab
3. Switch back to lesson-plan tab
4. Verify: lesson plan content, chat history, and file tags are all restored from DB
5. Verify: no duplicate messages or lost content

- [ ] **Step 11: Fix any issues and final commit**

```bash
git add -A
git commit -m "feat(lesson-plan): polish UI and complete end-to-end integration"
```
