# Lesson Plan Generation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lesson plan generation tab to the LessonPrep page with AI chat + Tiptap editor + TOC sidebar, supporting streaming generation, iterative modification, and export.

**Architecture:** Two-phase backend (RAG retrieval then streaming LLM generation), Vue 3 frontend with Tiptap editor for rich-text editing, markdown-it for streaming preview, SSE for real-time content delivery.

**Tech Stack:** FastAPI, DashScope LLM (streaming), HybridRetriever (RAG), Tiptap + tiptap-markdown, markdown-it, html2pdf.js, pypandoc

**Spec:** `docs/superpowers/specs/2026-03-13-lesson-plan-generation-design.md`

---

## Chunk 0: Pre-fixes

### Task 0: Fix Prerequisites

**Files:**
- Modify: `teacher-platform/src/api/http.js` (line 10)
- Modify: `backend/app/services/ai/graph/nodes.py` (should_retry function)

- [ ] **Step 1: Export `getToken` from http.js**

The `getToken` function at line 10 of `http.js` is not exported but our new components need it. Change:

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

## Chunk 1: Project Setup + Backend Foundation

### Task 1: Create Feature Branch + Install Dependencies

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

### Task 2: Backend Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/lesson_plan.py`

- [ ] **Step 1: Create schema file**

```python
# backend/app/schemas/lesson_plan.py
from pydantic import BaseModel
from typing import Optional


class LessonPlanGenerateRequest(BaseModel):
    query: str
    library_ids: list[str] = []
    file_ids: list[str] = []
    session_id: Optional[str] = None


class LessonPlanModifyRequest(BaseModel):
    instruction: str
    current_content: str
    history: list[dict] = []
    file_ids: list[str] = []
    library_ids: list[str] = []
    session_id: Optional[str] = None


class LessonPlanUploadResponse(BaseModel):
    file_id: str
    filename: str


class LessonPlanExportRequest(BaseModel):
    content: str
    title: str = "教案"
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/lesson_plan.py
git commit -m "feat(lesson-plan): add pydantic schemas for lesson plan API"
```

---

### Task 3: Backend Lesson Plan Service - Core

**Files:**
- Create: `backend/app/services/lesson_plan_service.py`

This service handles:
1. Retrieving context from knowledge libraries (RAG) and uploaded files
2. Streaming lesson plan generation via LLM
3. Streaming lesson plan modification via LLM

Key references:
- SSE streaming pattern: `backend/app/api/html_chat.py` (lines 51-84)
- RAG retrieval: `backend/app/services/rag/hybrid_retriever.py` - `HybridRetriever.search()`
- LLM service: `backend/app/services/ai/dashscope_service.py` - `DashScopeService`
- Tool search: `backend/app/services/ai/tools.py` - `search_local_knowledge_impl()`

- [ ] **Step 1: Create the service file with the lesson plan template prompt**

```python
# backend/app/services/lesson_plan_service.py
import json
import logging
from typing import AsyncGenerator, Optional

from app.core.config import get_settings
from app.services.rag.hybrid_retriever import get_hybrid_retriever

logger = logging.getLogger(__name__)
settings = get_settings()

LESSON_PLAN_SYSTEM_PROMPT = """你是一位经验丰富的教学设计专家。请根据用户的要求生成一份结构完整、内容详实的教案。

教案必须严格按照以下 Markdown 结构输出，每个模块都需要有实质性内容：

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
| ... | ... | ... | ... | ... |
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

LESSON_PLAN_MODIFY_PROMPT = """你是一位教学设计专家。用户提供了一份现有教案（Markdown 格式），以及修改要求。
请根据修改要求对教案进行调整，输出修改后的**完整教案**（不是只输出修改部分）。

保持原有的 Markdown 结构和格式不变，仅修改用户指定的内容。
严格输出 Markdown 格式。"""


async def _stream_llm(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream LLM response using the OpenAI-compatible API (same as html_llm.py pattern)."""
    import httpx

    if not settings.HTML_LLM_API_KEY:
        return

    base = (settings.HTML_LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.HTML_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.HTML_LLM_MODEL,
        "messages": messages,
        "max_tokens": 6000,
        "stream": True,
    }

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
                        choices = obj.get("choices") or []
                        if not choices:
                            continue
                        delta = (choices[0] or {}).get("delta") or {}
                        content = delta.get("content") or ""
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"LLM stream error: {e}")


async def _retrieve_context(
    query: str,
    library_ids: list[str],
    file_ids: list[str],
    user_id: int,
) -> str:
    """Retrieve context from knowledge libraries and uploaded files."""
    context_parts = []

    # 1. RAG retrieval from knowledge libraries
    if library_ids:
        try:
            retriever = get_hybrid_retriever()
            int_ids = [int(lid) for lid in library_ids]
            results = await retriever.search(
                query=query,
                user_id=user_id,
                k=5,
                library_ids=int_ids,
            )
            for doc in results:
                content = doc.page_content if hasattr(doc, 'page_content') else str(doc)
                context_parts.append(content)
        except Exception as e:
            logger.warning(f"RAG retrieval failed for libraries {library_ids}: {e}")

    # 2. Retrieve uploaded file contents
    if file_ids:
        try:
            from app.services.lesson_plan_file_store import get_file_content
            for fid in file_ids:
                content = get_file_content(fid)
                if content:
                    context_parts.append(f"[参考资料]\n{content}")
        except Exception as e:
            logger.warning(f"File content retrieval failed: {e}")

    if context_parts:
        return "\n\n---\n\n".join(context_parts)
    return ""


async def stream_generate_lesson_plan(
    query: str,
    library_ids: list[str],
    file_ids: list[str],
    user_id: int,
) -> AsyncGenerator[str, None]:
    """Two-phase lesson plan generation: retrieve context, then stream LLM output."""

    # Phase 1: Retrieve context (non-streaming)
    context = await _retrieve_context(query, library_ids, file_ids, user_id)

    # Phase 2: Stream generation
    user_message = query
    if context:
        user_message = f"以下是参考资料：\n\n{context}\n\n---\n\n用户要求：{query}"

    messages = [
        {"role": "system", "content": LESSON_PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    async for chunk in _stream_llm(messages):
        yield chunk


async def stream_modify_lesson_plan(
    instruction: str,
    current_content: str,
    history: list[dict],
    file_ids: list[str],
    library_ids: list[str],
    user_id: int,
) -> AsyncGenerator[str, None]:
    """Lightweight lesson plan modification: direct LLM streaming."""

    # Optionally retrieve reference material context
    ref_context = ""
    if file_ids or library_ids:
        ref_context = await _retrieve_context(instruction, library_ids, file_ids, user_id)

    user_message = f"当前教案内容：\n\n{current_content}\n\n"
    if ref_context:
        user_message += f"参考资料：\n\n{ref_context}\n\n"
    user_message += f"修改要求：{instruction}"

    messages = [{"role": "system", "content": LESSON_PLAN_MODIFY_PROMPT}]

    # Add recent chat history for context
    for msg in history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    async for chunk in _stream_llm(messages):
        yield chunk
```

Note: This uses the same OpenAI-compatible streaming pattern as `backend/app/services/html_llm.py` (`HTML_LLM_API_KEY`, `HTML_LLM_BASE_URL`, `HTML_LLM_MODEL` from settings). No need to add a method to DashScopeService.

- [ ] **Step 2: Create the file content store (simple in-memory store for uploaded file texts)**

```python
# backend/app/services/lesson_plan_file_store.py
"""Simple in-memory store for uploaded file text content.

Files are parsed on upload and their extracted text is stored here,
keyed by file_id. Used by the lesson plan service to inject reference
material into LLM prompts.
"""
import uuid
from typing import Optional

_store: dict[str, dict] = {}


def save_file_content(filename: str, content: str) -> str:
    """Save parsed file content, return file_id."""
    file_id = str(uuid.uuid4())
    _store[file_id] = {"filename": filename, "content": content}
    return file_id


def get_file_content(file_id: str) -> Optional[str]:
    """Retrieve parsed file content by file_id."""
    entry = _store.get(file_id)
    return entry["content"] if entry else None


def get_file_info(file_id: str) -> Optional[dict]:
    """Retrieve file metadata."""
    return _store.get(file_id)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/lesson_plan_service.py backend/app/services/lesson_plan_file_store.py
git commit -m "feat(lesson-plan): add lesson plan service with retrieval and streaming generation"
```

---

## Chunk 2: Backend API Endpoints

### Task 4: Backend API Routes

**Files:**
- Create: `backend/app/api/lesson_plan.py`
- Modify: `backend/app/api/__init__.py` (line ~14, add router include)

Key references:
- SSE response pattern: `backend/app/api/html_chat.py` (lines 51-84)
- Auth pattern: `backend/app/core/auth.py` (line 75, `CurrentUser`)
- Router registration: `backend/app/api/__init__.py`

- [ ] **Step 1: Create the API route file**

```python
# backend/app/api/lesson_plan.py
import json
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse

from app.core.auth import CurrentUser
from app.schemas.lesson_plan import (
    LessonPlanGenerateRequest,
    LessonPlanModifyRequest,
    LessonPlanExportRequest,
    LessonPlanUploadResponse,
)
from app.services.lesson_plan_service import (
    stream_generate_lesson_plan,
    stream_modify_lesson_plan,
)
from app.services.lesson_plan_file_store import save_file_content, get_file_info

logger = logging.getLogger(__name__)
router = APIRouter()


async def _sse_stream(async_gen):
    """Wrap an async generator into SSE format."""
    try:
        async for chunk in async_gen:
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/generate")
async def generate_lesson_plan(req: LessonPlanGenerateRequest, user: CurrentUser):
    """Generate a lesson plan with RAG retrieval + streaming LLM."""
    gen = stream_generate_lesson_plan(
        query=req.query,
        library_ids=req.library_ids,
        file_ids=req.file_ids,
        user_id=user.id,
    )
    return StreamingResponse(
        _sse_stream(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/modify")
async def modify_lesson_plan(req: LessonPlanModifyRequest, user: CurrentUser):
    """Modify an existing lesson plan with lightweight LLM streaming."""
    gen = stream_modify_lesson_plan(
        instruction=req.instruction,
        current_content=req.current_content,
        history=req.history,
        file_ids=req.file_ids,
        library_ids=req.library_ids,
        user_id=user.id,
    )
    return StreamingResponse(
        _sse_stream(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/upload", response_model=LessonPlanUploadResponse)
async def upload_reference_file(file: UploadFile = File(...), user: CurrentUser = None):
    """Upload a reference file, parse its content, store for later use."""
    from app.services.parsers.factory import ParserFactory

    # Save temp file for parsing
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content_bytes = await file.read()
        tmp.write(content_bytes)
        tmp_path = tmp.name

    # Parse file content using existing parser factory
    try:
        result = await ParserFactory.parse_file(tmp_path)
        if result and result.chunks:
            text_content = "\n\n".join(chunk.content for chunk in result.chunks)
        else:
            text_content = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"Failed to parse {file.filename}: {e}, using raw text")
        text_content = content_bytes.decode("utf-8", errors="ignore")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    file_id = save_file_content(file.filename, text_content)
    return LessonPlanUploadResponse(file_id=file_id, filename=file.filename)


@router.post("/export/docx")
async def export_docx(req: LessonPlanExportRequest):
    """Convert Markdown to DOCX using pypandoc."""
    import pypandoc
    from starlette.background import BackgroundTask

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name

    try:
        pypandoc.convert_text(
            req.content,
            "docx",
            format="md",
            outputfile=tmp_path,
        )
        return FileResponse(
            tmp_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{req.title}.docx",
            background=BackgroundTask(lambda: Path(tmp_path).unlink(missing_ok=True)),
        )
    except Exception as e:
        logger.error(f"DOCX export failed: {e}")
        Path(tmp_path).unlink(missing_ok=True)
        raise
```

- [ ] **Step 2: Register the router in `app/api/__init__.py`**

Read `backend/app/api/__init__.py` first, then add:

```python
from app.api import lesson_plan
api_router.include_router(lesson_plan.router, prefix="/lesson-plan", tags=["lesson-plan"])
```

- [ ] **Step 3: Verify the parser factory interface**

Read `backend/app/services/parsers/factory.py` to confirm:
- `ParserFactory.get_parser(file_type)` exists
- Parser's `parse(file_path)` method signature
- Return format (dict with "text" key? or string?)

Adjust the upload endpoint's parsing logic to match the actual interface.

- [ ] **Step 4: Test the endpoints manually**

```bash
cd backend
python run.py
```

Test with curl:
```bash
# Upload
curl -X POST http://localhost:8000/api/v1/lesson-plan/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.pdf"

# Generate (SSE)
curl -X POST http://localhost:8000/api/v1/lesson-plan/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "生成一份高一数学函数教案"}'
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/lesson_plan.py backend/app/api/__init__.py
git commit -m "feat(lesson-plan): add generate, modify, upload, export API endpoints"
```

---

## Chunk 3: Frontend Tiptap Editor + TOC

### Task 5: LessonPlanEditor Component

**Files:**
- Create: `teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue`

This is the right 2/3 panel containing:
- Top toolbar (fullscreen, copy, download MD/DOCX/PDF)
- Tiptap editor instance with tiptap-markdown
- Markdown preview overlay (shown during streaming)

Key references:
- Existing styling patterns: `teacher-platform/src/views/LessonPrepAnimation.vue`
- Color palette: primary blue `#2563eb`, light blue `#dbeafe`, grays `#f1f5f9` etc.

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
          <button class="toolbar-btn" @click="showDownloadMenu = !showDownloadMenu">下载</button>
          <div class="download-menu" v-if="showDownloadMenu">
            <button @click="downloadMd">Markdown</button>
            <button @click="downloadDocx">Word 文档</button>
            <button @click="downloadPdf">PDF</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Streaming preview overlay -->
    <div class="streaming-preview" v-if="isStreaming" v-html="previewHtml"></div>

    <!-- Tiptap editor -->
    <div class="editor-container" v-show="!isStreaming">
      <editor-content :editor="editor" class="tiptap-content" />
    </div>

    <!-- Empty state -->
    <div class="editor-empty" v-if="!hasContent && !isStreaming">
      <div class="empty-icon">&#128221;</div>
      <p class="empty-title">教案将在此处显示</p>
      <p class="empty-desc">在左侧对话框中描述您的教学需求，AI 将为您生成教案</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, onActivated, onDeactivated, nextTick, shallowRef } from 'vue'
import { EditorContent, Editor } from '@tiptap/vue-3'
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

const emit = defineEmits(['update:markdown', 'update:headings'])

const isFullscreen = ref(false)
const showDownloadMenu = ref(false)
const savedMarkdown = ref('')
// Use shallowRef + manual Editor for proper keep-alive lifecycle control
const editor = shallowRef(null)

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
  if (editor.value) {
    editor.value.destroy()
  }
  editor.value = new Editor({
    extensions: editorExtensions,
    content,
    editable: true,
    onUpdate: () => {
      const markdown = editor.value?.storage.markdown.getMarkdown() || ''
      emit('update:markdown', markdown)
      extractHeadings()
    },
  })
}

// Create editor on initial mount
createEditor()

const hasContent = computed(() => {
  if (!editor.value) return false
  return !editor.value.isEmpty
})

const charCount = computed(() => {
  return editor.value?.storage.characterCount.characters() || 0
})

const previewHtml = computed(() => {
  return md.render(props.streamingMarkdown || '')
})

// When streaming completes, inject final content into Tiptap
watch(() => props.isStreaming, (streaming, wasStreaming) => {
  if (wasStreaming && !streaming && props.streamingMarkdown) {
    editor.value?.commands.setContent(props.streamingMarkdown)
    editor.value?.setEditable(true)
    extractHeadings()
  }
})

// Lock editor during streaming
watch(() => props.isStreaming, (streaming) => {
  if (streaming) {
    editor.value?.setEditable(false)
  }
})

function extractHeadings() {
  if (!editor.value) return
  const headings = []
  editor.value.state.doc.descendants((node, pos) => {
    if (node.type.name === 'heading') {
      headings.push({
        level: node.attrs.level,
        text: node.textContent,
        pos,
      })
    }
  })
  emit('update:headings', headings)
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
}

async function copyContent() {
  const markdown = editor.value?.storage.markdown.getMarkdown() || ''
  await navigator.clipboard.writeText(markdown)
}

function downloadMd() {
  const markdown = editor.value?.storage.markdown.getMarkdown() || ''
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  downloadBlob(blob, '教案.md')
  showDownloadMenu.value = false
}

async function downloadDocx() {
  showDownloadMenu.value = false
  const markdown = editor.value?.storage.markdown.getMarkdown() || ''
  const { resolveApiUrl, getToken } = await import('@/api/http.js')
  const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/export/docx'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ content: markdown, title: '教案' }),
  })
  const blob = await res.blob()
  downloadBlob(blob, '教案.docx')
}

async function downloadPdf() {
  showDownloadMenu.value = false
  const html2pdf = (await import('html2pdf.js')).default
  const element = document.querySelector('.tiptap-content .ProseMirror')
  if (!element) return
  html2pdf().set({
    margin: 10,
    filename: '教案.pdf',
    html2canvas: { scale: 2 },
    jsPDF: { unit: 'mm', format: 'a4' },
  }).from(element).save()
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// Expose methods for parent component
function getMarkdown() {
  return editor.value?.storage.markdown.getMarkdown() || ''
}

function setMarkdownContent(markdown) {
  editor.value?.commands.setContent(markdown)
}

function scrollToPos(pos) {
  const view = editor.value?.view
  if (!view) return
  const coords = view.coordsAtPos(pos)
  const editorEl = view.dom.closest('.editor-container')
  if (editorEl) {
    editorEl.scrollTo({ top: coords.top - editorEl.getBoundingClientRect().top + editorEl.scrollTop - 20, behavior: 'smooth' })
  }
}

// Keep-alive lifecycle: save content, destroy editor, rebuild on reactivation
onDeactivated(() => {
  savedMarkdown.value = editor.value?.storage.markdown.getMarkdown() || ''
  editor.value?.destroy()
  editor.value = null
})

onActivated(() => {
  createEditor(savedMarkdown.value)
})

onBeforeUnmount(() => {
  editor.value?.destroy()
})

defineExpose({ getMarkdown, setMarkdownContent, scrollToPos })
</script>

<style scoped>
.editor-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  position: relative;
}

.editor-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  border-radius: 0;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.char-count {
  font-size: 0.8rem;
  color: #94a3b8;
}

.toolbar-btn {
  padding: 4px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  font-size: 0.85rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
}

.toolbar-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.download-group {
  position: relative;
}

.download-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  overflow: hidden;
}

.download-menu button {
  display: block;
  width: 100%;
  padding: 8px 20px;
  border: none;
  background: none;
  font-size: 0.85rem;
  color: #334155;
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
}

.download-menu button:hover {
  background: #f1f5f9;
}

.streaming-preview {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  font-size: 0.95rem;
  line-height: 1.7;
  color: #1e293b;
}

.editor-container {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.tiptap-content :deep(.ProseMirror) {
  padding: 24px 32px;
  min-height: 100%;
  outline: none;
  font-size: 0.95rem;
  line-height: 1.7;
  color: #1e293b;
}

.tiptap-content :deep(.ProseMirror h1) {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 1.5em 0 0.5em;
  color: #0f172a;
}

.tiptap-content :deep(.ProseMirror h2) {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 1.2em 0 0.4em;
  color: #1e293b;
  padding-bottom: 6px;
  border-bottom: 1px solid #e2e8f0;
}

.tiptap-content :deep(.ProseMirror h3) {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 1em 0 0.3em;
  color: #334155;
}

.tiptap-content :deep(.ProseMirror table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.tiptap-content :deep(.ProseMirror th),
.tiptap-content :deep(.ProseMirror td) {
  border: 1px solid #e2e8f0;
  padding: 8px 12px;
  text-align: left;
}

.tiptap-content :deep(.ProseMirror th) {
  background: #f1f5f9;
  font-weight: 600;
}

.tiptap-content :deep(.ProseMirror ul[data-type="taskList"]) {
  list-style: none;
  padding-left: 0;
}

.tiptap-content :deep(.ProseMirror ul[data-type="taskList"] li) {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.tiptap-content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  color: #94a3b8;
  pointer-events: none;
  float: left;
  height: 0;
}

.editor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  padding: 40px;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-title {
  font-size: 1.1rem;
  font-weight: 500;
  color: #64748b;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 0.9rem;
  color: #94a3b8;
  text-align: center;
}

/* Streaming preview styles (matches editor styles) */
.streaming-preview h1 { font-size: 1.5rem; font-weight: 700; margin: 1.5em 0 0.5em; color: #0f172a; }
.streaming-preview h2 { font-size: 1.25rem; font-weight: 600; margin: 1.2em 0 0.4em; color: #1e293b; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; }
.streaming-preview table { border-collapse: collapse; width: 100%; margin: 1em 0; }
.streaming-preview th, .streaming-preview td { border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }
.streaming-preview th { background: #f1f5f9; font-weight: 600; }
.streaming-preview ul.task-list-item { list-style: none; padding-left: 0; }
</style>
```

- [ ] **Step 2: Verify Tiptap renders correctly**

Start dev server and navigate to the page. Temporarily mount the editor component standalone to verify Tiptap initializes without errors:

```bash
cd teacher-platform && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan/LessonPlanEditor.vue
git commit -m "feat(lesson-plan): add Tiptap editor component with toolbar and streaming preview"
```

---

### Task 6: LessonPlanTOC Component

**Files:**
- Create: `teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue`

- [ ] **Step 1: Create the TOC component**

```vue
<!-- teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue -->
<template>
  <div :class="['toc-panel', { 'toc-collapsed': collapsed }]">
    <div class="toc-header">
      <span v-if="!collapsed" class="toc-title">目录</span>
      <button class="toc-toggle" @click="collapsed = !collapsed" :title="collapsed ? '展开目录' : '收起目录'">
        {{ collapsed ? '>' : '<' }}
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
    <p class="toc-empty" v-if="!collapsed && headings.length === 0">
      暂无目录
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  headings: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: -1 },
})
defineEmits(['scroll-to'])

const collapsed = ref(false)
</script>

<style scoped>
.toc-panel {
  width: 180px;
  border-right: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s ease;
  overflow: hidden;
}

.toc-collapsed {
  width: 36px;
}

.toc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.toc-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
}

.toc-toggle {
  width: 24px;
  height: 24px;
  border: none;
  background: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.85rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toc-toggle:hover {
  background: #e2e8f0;
  color: #475569;
}

.toc-list {
  list-style: none;
  padding: 8px 0;
  margin: 0;
  overflow-y: auto;
  flex: 1;
}

.toc-item {
  padding: 6px 16px;
  font-size: 0.82rem;
  color: #64748b;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toc-item:hover {
  color: #2563eb;
  background: #eff6ff;
}

.toc-item.active {
  color: #2563eb;
  border-left-color: #2563eb;
  font-weight: 500;
}

.toc-level-2 { padding-left: 16px; }
.toc-level-3 { padding-left: 28px; font-size: 0.78rem; }

.toc-empty {
  padding: 16px;
  font-size: 0.82rem;
  color: #94a3b8;
  text-align: center;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/components/lesson-plan/LessonPlanTOC.vue
git commit -m "feat(lesson-plan): add collapsible TOC sidebar component"
```

---

## Chunk 4: Frontend Chat Panel

### Task 7: LessonPlanChat Component

**Files:**
- Create: `teacher-platform/src/components/lesson-plan/LessonPlanChat.vue`

Key references:
- Chat bubble styling: `LessonPrepAnimation.vue` (user=#E0EDFE, AI=white)
- Voice input: `composables/useVoiceInput.js`
- File upload pattern: `LessonPrepAnimation.vue` lines 62-82
- HTTP utility: `api/http.js`

- [ ] **Step 1: Create the chat component**

```vue
<!-- teacher-platform/src/components/lesson-plan/LessonPlanChat.vue -->
<template>
  <div class="chat-panel">
    <!-- Messages -->
    <div class="messages-area" ref="messagesRef">
      <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', msg.role]">
        <div class="msg-label">{{ msg.role === 'user' ? '我' : '小助手' }}</div>
        <div class="msg-bubble" v-html="renderMsg(msg.content)"></div>
      </div>
      <div v-if="isSending" class="msg assistant">
        <div class="msg-label">小助手</div>
        <div class="msg-bubble loading-bubble">
          <span class="dot-anim">正在{{ hasContent ? '修改' : '生成' }}教案</span>
        </div>
      </div>
    </div>

    <!-- Tags area: selected files + knowledge bases -->
    <div class="tags-area" v-if="uploadedFiles.length > 0 || selectedLibraries.length > 0">
      <span
        v-for="f in uploadedFiles" :key="f.file_id"
        class="tag file-tag"
      >
        {{ f.filename }}
        <button class="tag-remove" @click="removeFile(f.file_id)">&times;</button>
      </span>
      <span
        v-for="lib in selectedLibraries" :key="lib.id"
        :class="['tag', lib.type === 'system' ? 'system-tag' : 'user-tag']"
      >
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
          <span>&#128206;</span>
        </button>
        <button class="action-btn" @click="showLibraryPicker = !showLibraryPicker" :disabled="isSending" title="选择知识库">
          <span>&#128218;</span>
        </button>
        <button :class="['action-btn', { recording: isRecording }]" @click="toggleVoice" :disabled="isSending" title="语音输入">
          <span>&#127908;</span>
        </button>
        <button class="send-btn" @click="handleSend" :disabled="isSending || !inputText.trim()">
          发送
        </button>
      </div>
    </div>

    <!-- Knowledge base picker dropdown -->
    <div class="library-picker" v-if="showLibraryPicker" @click.stop>
      <div class="lib-group" v-if="userLibraries.length > 0">
        <div class="lib-group-title">&#128193; 我的知识库</div>
        <label v-for="lib in userLibraries" :key="lib.id" class="lib-item">
          <input type="checkbox" :value="lib.id" v-model="selectedLibraryIds" />
          <span>{{ lib.name }}</span>
        </label>
      </div>
      <div class="lib-divider" v-if="userLibraries.length > 0 && systemLibraries.length > 0"></div>
      <div class="lib-group" v-if="systemLibraries.length > 0">
        <div class="lib-group-title">&#127760; 公开知识库</div>
        <label v-for="lib in systemLibraries" :key="lib.id" class="lib-item">
          <input type="checkbox" :value="lib.id" v-model="selectedLibraryIds" />
          <span>{{ lib.name }}</span>
        </label>
      </div>
      <p class="lib-empty" v-if="userLibraries.length === 0 && systemLibraries.length === 0">暂无知识库</p>
    </div>

    <!-- Hidden file input -->
    <input ref="fileInputRef" type="file" hidden accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg" @change="handleFileUpload" />
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
const showLibraryPicker = ref(false)
const uploadedFiles = ref([])
const selectedLibraryIds = ref([])
const userLibraries = ref([])
const systemLibraries = ref([])

// useVoiceInput takes a ref and directly mutates it on speech recognition
const { isRecording, isSupported, toggleRecording } = useVoiceInput(inputText)

const selectedLibraries = computed(() => {
  const all = [...userLibraries.value, ...systemLibraries.value]
  return all.filter((lib) => selectedLibraryIds.value.includes(lib.id))
})

// No need for transcript watcher — useVoiceInput directly mutates inputText

watch(() => props.messages.length, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
})

onMounted(() => {
  fetchLibraries()
})

async function fetchLibraries() {
  try {
    const token = getToken()
    const headers = { Authorization: `Bearer ${token}` }

    // Fetch user libraries (actual route: /api/v1/libraries)
    const userRes = await fetch(resolveApiUrl('/api/v1/libraries?scope=personal'), { headers })
    if (userRes.ok) {
      const data = await userRes.json()
      userLibraries.value = (data.items || data || []).map((lib) => ({ ...lib, type: 'user' }))
    }

    // Fetch system libraries
    const sysRes = await fetch(resolveApiUrl('/api/v1/libraries?scope=system'), { headers })
    if (sysRes.ok) {
      const data = await sysRes.json()
      systemLibraries.value = (data.items || data || []).map((lib) => ({ ...lib, type: 'system' }))
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
    library_ids: selectedLibraryIds.value,
  }

  if (props.hasContent) {
    emit('send-modify', payload)
  } else {
    emit('send', payload)
  }
  inputText.value = ''
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

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
    const data = await res.json()
    uploadedFiles.value.push(data)
  } catch (e) {
    console.error('File upload failed:', e)
  }
  fileInputRef.value.value = ''
}

function removeFile(fileId) {
  uploadedFiles.value = uploadedFiles.value.filter((f) => f.file_id !== fileId)
}

function removeLibrary(libId) {
  selectedLibraryIds.value = selectedLibraryIds.value.filter((id) => id !== libId)
}

function toggleVoice() {
  toggleRecording()
}

function renderMsg(content) {
  // Simple text rendering, escape HTML
  return content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
}

// Close library picker when clicking outside
function handleClickOutside(e) {
  if (showLibraryPicker.value && !e.target.closest('.library-picker') && !e.target.closest('.action-btn')) {
    showLibraryPicker.value = false
  }
}

onMounted(() => {
  fetchLibraries()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  position: relative;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.msg {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.msg.user { align-items: flex-end; }
.msg.assistant { align-items: flex-start; }

.msg-label {
  font-size: 0.75rem;
  color: #94a3b8;
  padding: 0 4px;
}

.msg-bubble {
  max-width: 90%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 0.9rem;
  line-height: 1.6;
  word-break: break-word;
}

.msg.user .msg-bubble {
  background: #E0EDFE;
  color: #1e293b;
  border-bottom-right-radius: 4px;
}

.msg.assistant .msg-bubble {
  background: #f1f5f9;
  color: #1e293b;
  border-bottom-left-radius: 4px;
}

.loading-bubble .dot-anim::after {
  content: '';
  animation: dots 1.5s steps(3) infinite;
}

@keyframes dots {
  0% { content: ''; }
  33% { content: '.'; }
  66% { content: '..'; }
  100% { content: '...'; }
}

.tags-area {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 16px;
  border-top: 1px solid #f1f5f9;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
}

.file-tag { background: #f1f5f9; color: #475569; }
.user-tag { background: #dbeafe; color: #2563eb; }
.system-tag { background: #d1fae5; color: #059669; }

.tag-remove {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.85rem;
  color: inherit;
  opacity: 0.6;
  padding: 0 2px;
}

.tag-remove:hover { opacity: 1; }

.input-area {
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
}

.input-area textarea {
  width: 100%;
  resize: none;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.9rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s ease;
}

.input-area textarea:focus {
  border-color: #93c5fd;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.15s ease;
}

.action-btn:hover { background: #f1f5f9; }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-btn.recording { background: #fee2e2; border-color: #fca5a5; }

.send-btn {
  margin-left: auto;
  padding: 6px 20px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.send-btn:hover { background: #1d4ed8; }
.send-btn:disabled { background: #93c5fd; cursor: not-allowed; }

/* Knowledge base picker */
.library-picker {
  position: absolute;
  bottom: 120px;
  left: 16px;
  right: 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 20;
  max-height: 240px;
  overflow-y: auto;
  padding: 8px 0;
}

.lib-group-title {
  padding: 8px 16px 4px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #94a3b8;
}

.lib-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  font-size: 0.85rem;
  color: #334155;
  cursor: pointer;
}

.lib-item:hover { background: #f8fafc; }

.lib-item input[type="checkbox"] {
  accent-color: #2563eb;
}

.lib-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 4px 12px;
}

.lib-empty {
  padding: 16px;
  text-align: center;
  font-size: 0.82rem;
  color: #94a3b8;
}
</style>
```

- [ ] **Step 2: Verify knowledge base API endpoint**

Read `backend/app/api/libraries.py` and `backend/app/api/__init__.py` to confirm the library listing endpoint path and response format. The chat component calls `GET /api/v1/libraries?scope=personal` and `?scope=system`. Verify the endpoint exists, supports the `scope` query parameter, and returns items with `id` and `name` fields. If the endpoint doesn't support `scope` filtering, add it or adjust the frontend accordingly.

- [ ] **Step 3: Commit**

```bash
git add teacher-platform/src/components/lesson-plan/LessonPlanChat.vue
git commit -m "feat(lesson-plan): add chat panel with knowledge base picker and file upload"
```

---

## Chunk 5: Frontend Main Container + Integration

### Task 8: LessonPrepLessonPlan Main Container

**Files:**
- Create: `teacher-platform/src/views/LessonPrepLessonPlan.vue`

This is the main container that:
- Manages three-column layout (TOC + Chat + Editor)
- Handles SSE streaming connections
- Coordinates state between child components

Key references:
- SSE streaming fetch pattern: `LessonPrepAnimation.vue` lines 216-280
- AbortController: `LessonPrepAnimation.vue` line 212

- [ ] **Step 1: Create the main container component**

```vue
<!-- teacher-platform/src/views/LessonPrepLessonPlan.vue -->
<template>
  <div class="lesson-plan-page">
    <!-- TOC sidebar -->
    <LessonPlanTOC
      :headings="headings"
      :active-index="activeHeadingIndex"
      @scroll-to="handleScrollTo"
    />

    <!-- Chat panel (left 1/3) -->
    <div class="chat-column">
      <LessonPlanChat
        :messages="messages"
        :is-sending="isSending"
        :has-content="hasContent"
        @send="handleGenerate"
        @send-modify="handleModify"
      />
    </div>

    <!-- Editor panel (right 2/3) -->
    <div class="editor-column">
      <LessonPlanEditor
        ref="editorRef"
        :is-streaming="isSending"
        :streaming-markdown="streamingMarkdown"
        @update:markdown="currentMarkdown = $event"
        @update:headings="headings = $event"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { resolveApiUrl, getToken } from '@/api/http.js'
import LessonPlanChat from '@/components/lesson-plan/LessonPlanChat.vue'
import LessonPlanEditor from '@/components/lesson-plan/LessonPlanEditor.vue'
import LessonPlanTOC from '@/components/lesson-plan/LessonPlanTOC.vue'

const editorRef = ref(null)
const messages = ref([])
const isSending = ref(false)
const streamingMarkdown = ref('')
const currentMarkdown = ref('')
const headings = ref([])
const activeHeadingIndex = ref(-1)

let abortController = null

const hasContent = computed(() => currentMarkdown.value.trim().length > 0)

async function handleGenerate(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  isSending.value = true
  streamingMarkdown.value = ''

  abortController = new AbortController()

  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/generate'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({
        query: payload.text,
        library_ids: payload.library_ids || [],
        file_ids: payload.file_ids || [],
      }),
      signal: abortController.signal,
    })

    await processSSEStream(res)
    messages.value.push({ role: 'assistant', content: '教案已生成，您可以在右侧编辑器中查看和修改。' })
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Generate failed:', e)
      messages.value.push({ role: 'assistant', content: '生成失败，请重试。' })
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

async function handleModify(payload) {
  messages.value.push({ role: 'user', content: payload.text })
  isSending.value = true
  streamingMarkdown.value = ''

  // Save current content for rollback on error
  const backupMarkdown = editorRef.value?.getMarkdown() || ''

  abortController = new AbortController()

  try {
    const res = await fetch(resolveApiUrl('/api/v1/lesson-plan/modify'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({
        instruction: payload.text,
        current_content: backupMarkdown,
        history: messages.value.slice(-10),
        file_ids: payload.file_ids || [],
        library_ids: payload.library_ids || [],
      }),
      signal: abortController.signal,
    })

    await processSSEStream(res)
    messages.value.push({ role: 'assistant', content: '教案已更新。' })
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Modify failed:', e)
      messages.value.push({ role: 'assistant', content: '修改失败，请重试。' })
      // Rollback editor content
      editorRef.value?.setMarkdownContent(backupMarkdown)
    }
  } finally {
    isSending.value = false
    abortController = null
  }
}

async function processSSEStream(res) {
  const reader = res.body?.getReader()
  if (!reader) throw new Error('No reader available')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || !trimmed.startsWith('data:')) continue

      const dataStr = trimmed.slice(5).trim()
      if (dataStr === '[DONE]') return

      try {
        const data = JSON.parse(dataStr)
        if (data.content) {
          streamingMarkdown.value += data.content
        }
        if (data.error) {
          throw new Error(data.error)
        }
      } catch (parseErr) {
        // Skip non-JSON lines
      }
    }
  }
}

function handleScrollTo(pos) {
  editorRef.value?.scrollToPos(pos)
}

onBeforeUnmount(() => {
  abortController?.abort()
})
</script>

<style scoped>
.lesson-plan-page {
  display: flex;
  height: calc(100vh - 60px);
  gap: 0;
  background: #f1f5f9;
  padding: 16px;
}

.chat-column {
  width: 33%;
  min-width: 300px;
  max-width: 420px;
  flex-shrink: 0;
  padding-right: 12px;
}

.editor-column {
  flex: 1;
  min-width: 0;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add teacher-platform/src/views/LessonPrepLessonPlan.vue
git commit -m "feat(lesson-plan): add main container with SSE streaming and three-column layout"
```

---

### Task 9: Tab + Sidebar Integration

**Files:**
- Modify: `teacher-platform/src/views/LessonPrep.vue` (lines 4-7 imports, lines 19-24 tabs array)
- Modify: `teacher-platform/src/components/LayoutWithNav.vue` (lines 26-31 lessonPrepTabs array)

- [ ] **Step 1: Update LessonPrep.vue**

Read the file first, then:

1. Add import for `LessonPrepLessonPlan`:

```javascript
import LessonPrepLessonPlan from './LessonPrepLessonPlan.vue'
```

2. Insert into the tabs array between `ppt` and `animation`:

```javascript
{ id: 'lesson-plan', label: '教案生成', component: LessonPrepLessonPlan }
```

3. Add it to the `<component :is>` mapping or dynamic component resolution (match existing pattern).

- [ ] **Step 2: Update LayoutWithNav.vue sidebar**

Read the file first, then insert into the `lessonPrepTabs` array at index 1:

```javascript
{ id: 'lesson-plan', label: '教案生成', icon: 'lesson-plan' }
```

- [ ] **Step 3: Verify tab switching works**

```bash
cd teacher-platform && npm run dev
```

Navigate to `/lesson-prep?tab=lesson-plan` and verify:
- Tab is visible in sidebar between PPT and animation
- The three-column layout renders
- Switching between tabs preserves state (keep-alive)

- [ ] **Step 4: Commit**

```bash
git add teacher-platform/src/views/LessonPrep.vue teacher-platform/src/components/LayoutWithNav.vue
git commit -m "feat(lesson-plan): integrate lesson plan tab into LessonPrep and sidebar navigation"
```

---

### Task 10: End-to-End Verification + Polish

- [ ] **Step 1: Start backend**

```bash
cd backend && python run.py
```

- [ ] **Step 2: Start frontend**

```bash
cd teacher-platform && npm run dev
```

- [ ] **Step 3: Test initial generation flow**

1. Navigate to `/lesson-prep?tab=lesson-plan`
2. Type "帮我生成一份高一数学函数与方程的教案" in the chat input
3. Click send
4. Verify: streaming preview shows content appearing in the right panel
5. Verify: after [DONE], content is loaded into Tiptap editor
6. Verify: TOC shows the heading structure

- [ ] **Step 4: Test modification flow**

1. In the chat input, type "把教学目标改为三维目标的形式"
2. Click send
3. Verify: right panel shows updated content streaming
4. Verify: editor is updated when done

- [ ] **Step 5: Test manual editing**

1. Click in the editor and modify text
2. Verify: TOC updates when headings change
3. Verify: the edited content is preserved for the next AI modification

- [ ] **Step 6: Test export**

1. Click "下载" button in toolbar
2. Test "Markdown" download — verify `.md` file is correct
3. Test "Word 文档" download — verify `.docx` file opens correctly
4. Test "PDF" download — verify PDF is generated from editor content

- [ ] **Step 7: Test knowledge base picker**

1. Click the knowledge base button
2. Verify: user and system libraries are shown in grouped sections
3. Select libraries, verify tags appear above input
4. Verify: selected library_ids are sent in the request

- [ ] **Step 8: Test file upload**

1. Click upload button, select a PDF
2. Verify: file tag appears
3. Send a generate request with the uploaded file
4. Verify: file_ids are included in the request

- [ ] **Step 9: Fix any styling/layout issues**

Adjust CSS as needed to match existing codebase visual patterns (colors, spacing, border radius, shadows).

- [ ] **Step 10: Final commit**

```bash
git add -A
git commit -m "feat(lesson-plan): polish UI and complete end-to-end integration"
```
