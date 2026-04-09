# 课堂预演 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现课堂预演 MVP — 用户输入教学主题，后端 SSE 流式生成幻灯片 + 动作序列 + TTS 语音，前端即时播放（含聚焦/激光/翻页/字幕）。

**Architecture:** 后端 FastAPI SSE 流式生成（两阶段管线：大纲 → 逐页内容+动作+TTS），前端 Vue 3 自建轻量幻灯片渲染器 + PlaybackEngine 状态机驱动播放。数据持久化到 PostgreSQL，音频文件存 OSS。

**Tech Stack:** Python/FastAPI, SQLAlchemy async, DashScope LLM (qwen-plus) + TTS (qwen3-tts-flash), Vue 3/Pinia, 自建 SlideRenderer

**重要说明：PPTist 不是 npm 包，OpenMAIC 也没有使用 PPTist 包，而是自建了渲染器。本计划采用自建轻量 Vue 幻灯片渲染器，仅实现文本、图片、形状三种元素类型（MVP 够用），后续阶段再补充图表、LaTeX 等。**

---

## 文件结构

### 后端新增

```
backend/app/
├── api/rehearsal.py                         # API 路由（generate-stream, sessions CRUD）
├── models/rehearsal.py                      # ORM：RehearsalSession + RehearsalScene
├── schemas/rehearsal.py                     # Pydantic 请求/响应模型
└── services/
    ├── rehearsal_generation_service.py       # SSE 生成编排（大纲→内容→动作→TTS）
    ├── rehearsal_session_service.py          # 会话 CRUD
    └── tts_service.py                       # Qwen TTS 轻量封装
```

### 后端修改

```
backend/app/models/__init__.py               # 导出新模型
backend/app/api/__init__.py                  # 注册新路由
```

### 前端新增

```
teacher-platform/src/
├── api/rehearsal.js                         # 后端 API 调用封装
├── stores/rehearsal.js                      # Pinia store
├── composables/usePlaybackEngine.js         # PlaybackEngine 状态机
├── views/rehearsal/
│   ├── RehearsalNew.vue                     # 新建预演页
│   ├── RehearsalPlay.vue                    # 播放页（核心）
│   └── RehearsalHistory.vue                 # 历史列表
└── components/rehearsal/
    ├── SlideRenderer.vue                    # 幻灯片渲染器（文本/图片/形状）
    ├── SpotlightOverlay.vue                 # 聚焦遮罩
    ├── LaserPointer.vue                     # 激光指针
    ├── SubtitlePanel.vue                    # 字幕面板
    └── PlaybackControls.vue                 # 播放控制栏
```

### 前端修改

```
teacher-platform/src/router/index.js         # 注册预演路由
```

---

## Task 1: 后端数据模型

**Files:**
- Create: `backend/app/models/rehearsal.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 ORM 模型文件**

```python
# backend/app/models/rehearsal.py
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RehearsalSession(Base):
    __tablename__ = "rehearsal_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="未命名预演")
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    total_scenes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ready_scenes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    playback_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-CN")
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    scenes: Mapped[list["RehearsalScene"]] = relationship(
        "RehearsalScene", back_populates="session", cascade="all, delete-orphan",
        order_by="RehearsalScene.scene_order"
    )


class RehearsalScene(Base):
    __tablename__ = "rehearsal_scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rehearsal_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    slide_content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session: Mapped["RehearsalSession"] = relationship("RehearsalSession", back_populates="scenes")
```

- [ ] **Step 2: 注册模型到 `__init__.py`**

在 `backend/app/models/__init__.py` 添加：

```python
from app.models.rehearsal import RehearsalSession, RehearsalScene
```

并在 `__all__` 列表中添加 `"RehearsalSession"`, `"RehearsalScene"`。

- [ ] **Step 3: 生成数据库迁移**

```bash
cd backend
alembic revision --autogenerate -m "add rehearsal_sessions and rehearsal_scenes tables"
```

- [ ] **Step 4: 执行迁移**

```bash
cd backend
alembic upgrade head
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/rehearsal.py backend/app/models/__init__.py backend/alembic/versions/
git commit -m "feat(rehearsal): add RehearsalSession and RehearsalScene models"
```

---

## Task 2: 后端 Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/rehearsal.py`

- [ ] **Step 1: 创建 schemas 文件**

```python
# backend/app/schemas/rehearsal.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ---------- 请求 ----------

class RehearsalGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="zh-CN")
    enable_tts: bool = Field(default=True)
    voice: str = Field(default="Cherry")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class RehearsalSnapshotUpdate(BaseModel):
    playback_snapshot: dict = Field(..., description="{sceneIndex, actionIndex}")


# ---------- 响应 ----------

class RehearsalSessionSummary(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    total_scenes: int
    ready_scenes: int
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RehearsalSceneResponse(BaseModel):
    id: int
    scene_order: int
    title: str
    slide_content: dict
    actions: list
    key_points: list | None = None

    model_config = {"from_attributes": True}


class RehearsalSessionDetail(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    total_scenes: int
    ready_scenes: int
    playback_snapshot: dict | None = None
    language: str
    settings: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    scenes: list[RehearsalSceneResponse]

    model_config = {"from_attributes": True}


class RehearsalSessionListResponse(BaseModel):
    sessions: list[RehearsalSessionSummary]
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/schemas/rehearsal.py
git commit -m "feat(rehearsal): add Pydantic request/response schemas"
```

---

## Task 3: 后端会话 CRUD Service

**Files:**
- Create: `backend/app/services/rehearsal_session_service.py`

- [ ] **Step 1: 创建会话服务**

```python
# backend/app/services/rehearsal_session_service.py
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rehearsal import RehearsalSession, RehearsalScene

logger = logging.getLogger(__name__)


async def list_sessions(db: AsyncSession, user_id: int) -> list[RehearsalSession]:
    result = await db.execute(
        select(RehearsalSession)
        .where(RehearsalSession.user_id == user_id)
        .order_by(RehearsalSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_session_with_scenes(
    db: AsyncSession, session_id: int, user_id: int
) -> RehearsalSession | None:
    result = await db.execute(
        select(RehearsalSession)
        .options(selectinload(RehearsalSession.scenes))
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_playback_snapshot(
    db: AsyncSession, session_id: int, user_id: int, snapshot: dict
) -> bool:
    result = await db.execute(
        select(RehearsalSession)
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    session.playback_snapshot = snapshot
    await db.flush()
    return True


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(RehearsalSession)
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/rehearsal_session_service.py
git commit -m "feat(rehearsal): add session CRUD service"
```

---

## Task 4: 后端 TTS Service

**Files:**
- Create: `backend/app/services/tts_service.py`

- [ ] **Step 1: 创建 Qwen TTS 服务**

```python
# backend/app/services/tts_service.py
"""
Qwen TTS 轻量封装 — 单 provider，不做多 provider 架构。
调用阿里云百炼 DashScope multimodal-generation 接口。
失败时返回 None，调用方降级为计时播放。
"""
import logging
import uuid

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DASHSCOPE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen3-tts-flash"
DEFAULT_VOICE = "Cherry"


async def synthesize(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> str | None:
    """
    合成语音，返回音频 URL。失败返回 None（调用方降级为计时播放）。
    """
    if not settings.DASHSCOPE_API_KEY:
        logger.warning("DASHSCOPE_API_KEY not set, skipping TTS")
        return None

    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEFAULT_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": text}],
                }
            ]
        },
        "parameters": {
            "voice": voice,
            "speed": speed,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(DASHSCOPE_TTS_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            audio_url = (
                data.get("output", {})
                .get("audio", {})
                .get("url")
            )
            if audio_url:
                logger.info(f"TTS generated: {len(text)} chars -> {audio_url[:80]}...")
                return audio_url
            logger.warning(f"TTS response missing audio URL: {data}")
            return None
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return None


def estimate_duration_ms(text: str, speed: float = 1.0) -> int:
    """估算文本阅读时长（毫秒），用于无音频时的计时播放。"""
    # 中文按 150ms/字，英文按 240ms/词
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    non_cjk = text
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            non_cjk = non_cjk.replace(c, '', 1)
    word_count = len(non_cjk.split())
    duration = cjk_count * 150 + word_count * 240
    duration = max(duration, 2000)  # 最短 2 秒
    return int(duration / speed)
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/tts_service.py
git commit -m "feat(rehearsal): add Qwen TTS service with auto-degradation"
```

---

## Task 5: 后端生成服务（SSE 管线）

**Files:**
- Create: `backend/app/services/rehearsal_generation_service.py`

- [ ] **Step 1: 创建生成服务**

```python
# backend/app/services/rehearsal_generation_service.py
"""
课堂预演 SSE 生成管线。
Stage 1: LLM -> 场景大纲
Stage 2: 逐场景 -> slide content + actions + TTS
"""
import json
import logging
from typing import AsyncGenerator

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.rehearsal import RehearsalSession, RehearsalScene
from app.services.lesson_plan_service import stream_llm
from app.services.tts_service import synthesize, estimate_duration_ms

logger = logging.getLogger(__name__)
settings = get_settings()


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


OUTLINE_SYSTEM_PROMPT = """你是一位资深教师和课程设计专家。根据用户提供的教学主题，设计一组教学场景大纲。

要求：
1. 生成 5-8 个教学场景，每个场景对应一页幻灯片
2. 涵盖：课程导入、核心知识点讲解（多页）、总结回顾
3. 每个场景包含标题、描述、3-5 个要点

输出严格 JSON 数组格式，不要输出其他内容：
[
  {
    "title": "场景标题",
    "description": "这一页要讲什么",
    "keyPoints": ["要点1", "要点2", "要点3"],
    "teachingObjective": "教学目标"
  }
]"""

SLIDE_CONTENT_SYSTEM_PROMPT = """你是一位幻灯片设计专家。根据场景大纲生成一页幻灯片内容。

画布尺寸：宽 1000px，高 562px（16:9）。
元素使用绝对定位 (left, top, width, height)。
每个元素必须有唯一 id（格式：el_1, el_2, ...）。

支持的元素类型：
1. text: HTML 文本 { id, type: "text", content: "<p>HTML内容</p>", left, top, width, height, fontSize?, color? }
2. image: 图片 { id, type: "image", src: "placeholder", left, top, width, height }
3. shape: 形状 { id, type: "shape", shape: "rect"|"roundRect"|"ellipse", left, top, width, height, fill: "#颜色" }

设计规范：
- 标题用大字体 (28-36px)，放页面上方
- 正文用中等字体 (18-24px)
- 元素不要重叠，留足间距
- 背景用浅色或白色
- 每页 3-6 个元素

输出严格 JSON 格式，不要输出其他内容：
{
  "id": "slide_N",
  "viewportSize": 1000,
  "viewportRatio": 0.5625,
  "background": { "type": "solid", "color": "#ffffff" },
  "elements": [ ... ]
}"""

ACTIONS_SYSTEM_PROMPT = """你是一位课堂教学专家。根据幻灯片内容和要点，生成该页的教学动作序列。

可用动作类型：
1. speech: 讲解 { "type": "speech", "text": "讲稿内容" }
2. spotlight: 聚焦元素 { "type": "spotlight", "elementId": "el_1", "dimOpacity": 0.4 }
3. laser: 激光指向 { "type": "laser", "elementId": "el_1", "color": "#ff0000" }

设计规范：
- 每页 4-8 个动作
- 通常先 spotlight 某元素，然后 speech 讲解该元素
- speech 文本要自然、口语化，像真正在课堂上讲课
- 第一页要有开场白（"同学们好，今天我们来学习..."）
- 最后一页要有收尾语
- spotlight 的 elementId 必须引用幻灯片中已有的元素 id
- 不要生成 navigate 动作（翻页由系统自动处理）

输出严格 JSON 数组格式，不要输出其他内容：
[
  { "type": "spotlight", "elementId": "el_1", "dimOpacity": 0.4 },
  { "type": "speech", "text": "这里讲解..." },
  ...
]"""


async def _call_llm_json(system_prompt: str, user_prompt: str) -> dict | list | None:
    """调用 LLM 并解析 JSON 输出。收集完整响应后解析。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    full = ""
    async for chunk in stream_llm(messages):
        full += chunk

    # 清理 markdown 代码块标记
    text = full.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # 去掉 ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        start = text.find('[') if '[' in text else text.find('{')
        end = text.rfind(']') + 1 if ']' in text else text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        logger.error(f"Failed to parse LLM JSON: {text[:200]}...")
        return None


async def generate_stream(
    topic: str,
    language: str,
    enable_tts: bool,
    voice: str,
    speed: float,
    user_id: int,
) -> AsyncGenerator[str, None]:
    """SSE 流式生成预演内容。"""

    async with AsyncSessionLocal() as db:
        try:
            # --- 创建会话 ---
            session = RehearsalSession(
                user_id=user_id,
                title=topic[:100],
                topic=topic,
                status="generating",
                language=language,
                settings={"voice": voice, "speed": speed, "enableTTS": enable_tts},
            )
            db.add(session)
            await db.flush()
            session_id = session.id

            yield _sse_event("session_created", {"sessionId": session_id, "title": session.title})

            # --- Stage 1: 生成大纲 ---
            outlines = await _call_llm_json(
                OUTLINE_SYSTEM_PROMPT,
                f"教学主题：{topic}\n语言：{language}"
            )
            if not outlines or not isinstance(outlines, list):
                session.status = "failed"
                session.error_message = "大纲生成失败"
                await db.commit()
                yield _sse_event("error", {"message": "大纲生成失败"})
                return

            session.total_scenes = len(outlines)
            await db.flush()

            yield _sse_event("outline_ready", {
                "outlines": outlines,
                "totalScenes": len(outlines),
            })

            # --- Stage 2: 逐场景生成 ---
            all_outlines_text = json.dumps(outlines, ensure_ascii=False)

            for idx, outline in enumerate(outlines):
                try:
                    # 2a: 生成 slide content
                    slide_prompt = (
                        f"场景标题：{outline['title']}\n"
                        f"场景描述：{outline.get('description', '')}\n"
                        f"要点：{json.dumps(outline.get('keyPoints', []), ensure_ascii=False)}\n"
                        f"这是第 {idx + 1}/{len(outlines)} 页\n"
                        f"课程所有大纲：{all_outlines_text}"
                    )
                    slide_content = await _call_llm_json(SLIDE_CONTENT_SYSTEM_PROMPT, slide_prompt)
                    if not slide_content or not isinstance(slide_content, dict):
                        slide_content = _fallback_slide(outline, idx)

                    # 2b: 生成 actions
                    element_ids = [el.get("id", "") for el in slide_content.get("elements", [])]
                    actions_prompt = (
                        f"幻灯片标题：{outline['title']}\n"
                        f"要点：{json.dumps(outline.get('keyPoints', []), ensure_ascii=False)}\n"
                        f"幻灯片元素 ID 列表：{json.dumps(element_ids)}\n"
                        f"这是第 {idx + 1}/{len(outlines)} 页"
                    )
                    actions = await _call_llm_json(ACTIONS_SYSTEM_PROMPT, actions_prompt)
                    if not actions or not isinstance(actions, list):
                        actions = [{"type": "speech", "text": outline.get("description", outline["title"])}]

                    # 过滤无效 elementId
                    valid_ids = set(element_ids)
                    for action in actions:
                        if action.get("type") in ("spotlight", "laser"):
                            if action.get("elementId") not in valid_ids:
                                action["type"] = "speech"
                                action["text"] = ""
                                action.pop("elementId", None)
                                action.pop("dimOpacity", None)
                                action.pop("color", None)
                    actions = [a for a in actions if not (a.get("type") == "speech" and not a.get("text"))]

                    # 2c: TTS
                    if enable_tts:
                        for action in actions:
                            if action.get("type") == "speech" and action.get("text"):
                                audio_url = await synthesize(action["text"], voice, speed)
                                action["audioUrl"] = audio_url  # None if failed
                                action["duration"] = estimate_duration_ms(action["text"], speed)

                    # 无 TTS 时补充 duration
                    for action in actions:
                        if action.get("type") == "speech" and "duration" not in action:
                            action["duration"] = estimate_duration_ms(action.get("text", ""), speed)

                    # 写入 DB
                    scene = RehearsalScene(
                        session_id=session_id,
                        scene_order=idx,
                        title=outline["title"],
                        slide_content=slide_content,
                        actions=actions,
                        key_points=outline.get("keyPoints"),
                    )
                    db.add(scene)
                    session.ready_scenes = idx + 1
                    await db.flush()

                    yield _sse_event("scene_ready", {
                        "sceneIndex": idx,
                        "scene": {
                            "title": outline["title"],
                            "slideContent": slide_content,
                            "actions": actions,
                            "keyPoints": outline.get("keyPoints"),
                        },
                    })

                except Exception as e:
                    logger.error(f"Scene {idx} generation failed: {e}")
                    yield _sse_event("scene_error", {
                        "sceneIndex": idx,
                        "message": str(e),
                    })
                    continue

            # --- 完成 ---
            if session.ready_scenes == session.total_scenes:
                session.status = "ready"
            elif session.ready_scenes > 0:
                session.status = "partial"
            else:
                session.status = "failed"
                session.error_message = "所有场景生成失败"

            # 用第一个大纲生成标题
            session.title = f"{topic[:50]} - 课堂预演"
            await db.commit()

            yield _sse_event("complete", {"sessionId": session_id})

        except Exception as e:
            logger.error(f"Generation pipeline failed: {e}")
            try:
                session.status = "failed" if session.ready_scenes == 0 else "partial"
                session.error_message = str(e)
                await db.commit()
            except Exception:
                await db.rollback()
            yield _sse_event("error", {"message": str(e)})


def _fallback_slide(outline: dict, idx: int) -> dict:
    """LLM 生成 slide 失败时的降级方案：纯文本幻灯片。"""
    elements = [
        {
            "id": f"el_{idx}_title",
            "type": "text",
            "content": f"<p style='font-size:32px;font-weight:bold'>{outline['title']}</p>",
            "left": 50, "top": 40, "width": 900, "height": 60,
        },
    ]
    for i, point in enumerate(outline.get("keyPoints", [])[:5]):
        elements.append({
            "id": f"el_{idx}_pt_{i}",
            "type": "text",
            "content": f"<p style='font-size:20px'>• {point}</p>",
            "left": 80, "top": 140 + i * 70, "width": 840, "height": 50,
        })
    return {
        "id": f"slide_{idx}",
        "viewportSize": 1000,
        "viewportRatio": 0.5625,
        "background": {"type": "solid", "color": "#ffffff"},
        "elements": elements,
    }
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/rehearsal_generation_service.py
git commit -m "feat(rehearsal): add SSE generation pipeline service"
```

---

## Task 6: 后端 API 路由

**Files:**
- Create: `backend/app/api/rehearsal.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: 创建 API 路由**

```python
# backend/app/api/rehearsal.py
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.database import get_db
from app.schemas.rehearsal import (
    RehearsalGenerateRequest,
    RehearsalSnapshotUpdate,
    RehearsalSessionSummary,
    RehearsalSessionDetail,
    RehearsalSessionListResponse,
)
from app.services import rehearsal_session_service as session_svc
from app.services.rehearsal_generation_service import generate_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rehearsal", tags=["rehearsal"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/generate-stream")
async def generate_rehearsal_stream(req: RehearsalGenerateRequest, user: CurrentUser):
    """SSE 流式生成课堂预演。"""
    generator = generate_stream(
        topic=req.topic,
        language=req.language,
        enable_tts=req.enable_tts,
        voice=req.voice,
        speed=req.speed,
        user_id=user.id,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions", response_model=RehearsalSessionListResponse)
async def list_sessions(user: CurrentUser, db: DbSession):
    """获取当前用户的预演会话列表。"""
    sessions = await session_svc.list_sessions(db, user.id)
    return RehearsalSessionListResponse(
        sessions=[RehearsalSessionSummary.model_validate(s) for s in sessions]
    )


@router.get("/sessions/{session_id}", response_model=RehearsalSessionDetail)
async def get_session(session_id: int, user: CurrentUser, db: DbSession):
    """获取预演会话详情（含所有场景）。"""
    session = await session_svc.get_session_with_scenes(db, session_id, user.id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    return RehearsalSessionDetail.model_validate(session)


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: int, req: RehearsalSnapshotUpdate, user: CurrentUser, db: DbSession
):
    """更新播放进度快照。"""
    ok = await session_svc.update_playback_snapshot(db, session_id, user.id, req.playback_snapshot)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    await db.commit()
    return {"success": True}


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: int, user: CurrentUser, db: DbSession):
    """删除预演会话。"""
    ok = await session_svc.delete_session(db, session_id, user.id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    return None
```

- [ ] **Step 2: 注册路由**

在 `backend/app/api/__init__.py` 添加：

```python
from app.api import rehearsal
```

在 `api_router.include_router(...)` 列表中添加：

```python
api_router.include_router(rehearsal.router)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/rehearsal.py backend/app/api/__init__.py
git commit -m "feat(rehearsal): add API routes and register to router"
```

---

## Task 7: 前端 API 层

**Files:**
- Create: `teacher-platform/src/api/rehearsal.js`

- [ ] **Step 1: 创建 API 封装**

```javascript
// teacher-platform/src/api/rehearsal.js
import { apiRequest, authFetch } from './http.js'

const API = '/api/v1/rehearsal'

/**
 * SSE 流式生成预演。返回 Response 对象，调用方自行读取 SSE。
 */
export async function generateRehearsalStream(params) {
  return await authFetch(`${API}/generate-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

/**
 * 获取预演会话列表
 */
export async function fetchSessions() {
  return await apiRequest(`${API}/sessions`)
}

/**
 * 获取预演会话详情（含场景）
 */
export async function fetchSession(sessionId) {
  return await apiRequest(`${API}/sessions/${sessionId}`)
}

/**
 * 更新播放进度
 */
export async function updatePlaybackSnapshot(sessionId, snapshot) {
  return await apiRequest(`${API}/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ playback_snapshot: snapshot }),
  })
}

/**
 * 删除预演
 */
export async function deleteSession(sessionId) {
  return await apiRequest(`${API}/sessions/${sessionId}`, {
    method: 'DELETE',
  })
}
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/api/rehearsal.js
git commit -m "feat(rehearsal): add frontend API layer"
```

---

## Task 8: 前端 Pinia Store

**Files:**
- Create: `teacher-platform/src/stores/rehearsal.js`

- [ ] **Step 1: 创建 store**

```javascript
// teacher-platform/src/stores/rehearsal.js
import { defineStore } from 'pinia'
import {
  generateRehearsalStream,
  fetchSessions,
  fetchSession,
  updatePlaybackSnapshot,
  deleteSession,
} from '../api/rehearsal.js'

export const useRehearsalStore = defineStore('rehearsal', {
  state: () => ({
    // 当前会话
    currentSession: null,
    scenes: [],

    // 播放状态
    currentSceneIndex: 0,
    currentActionIndex: 0,
    playbackState: 'idle', // idle | playing | paused

    // 视觉效果
    spotlightTarget: null, // { elementId, dimOpacity }
    laserTarget: null, // { elementId, color }

    // 当前字幕
    currentSubtitle: '',

    // 生成状态
    generatingStatus: null, // null | generating | complete | error
    generatingProgress: '', // 进度文案
    outlines: [],

    // 历史列表
    sessions: [],
    sessionsLoading: false,
  }),

  getters: {
    currentScene(state) {
      return state.scenes[state.currentSceneIndex] || null
    },
    totalScenes(state) {
      return state.scenes.length
    },
    isPlaying(state) {
      return state.playbackState === 'playing'
    },
    isPaused(state) {
      return state.playbackState === 'paused'
    },
  },

  actions: {
    // --- 生成 ---
    async startGenerate(params) {
      this.generatingStatus = 'generating'
      this.generatingProgress = '正在生成大纲...'
      this.scenes = []
      this.outlines = []
      this.currentSession = null

      try {
        const resp = await generateRehearsalStream(params)
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${resp.status}`)
        }
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() // 保留不完整行

          let eventType = null
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              const dataStr = line.slice(6)
              try {
                const data = JSON.parse(dataStr)
                this._handleSSEEvent(eventType, data)
              } catch { /* ignore parse errors */ }
              eventType = null
            }
          }
        }

        if (this.generatingStatus === 'generating') {
          this.generatingStatus = 'complete'
        }
      } catch (e) {
        this.generatingStatus = 'error'
        this.generatingProgress = `生成失败: ${e.message}`
        console.error('Generation failed:', e)
      }
    },

    _handleSSEEvent(eventType, data) {
      switch (eventType) {
        case 'session_created':
          this.currentSession = { id: data.sessionId, title: data.title }
          break
        case 'outline_ready':
          this.outlines = data.outlines
          this.generatingProgress = `大纲就绪，共 ${data.totalScenes} 页，正在生成第 1 页...`
          break
        case 'scene_ready':
          this.scenes.push(data.scene)
          this.generatingProgress = `已生成 ${this.scenes.length}/${this.outlines.length} 页...`
          break
        case 'complete':
          this.generatingStatus = 'complete'
          this.generatingProgress = '生成完成'
          if (this.currentSession) {
            this.currentSession.id = data.sessionId
          }
          break
        case 'error':
          this.generatingStatus = 'error'
          this.generatingProgress = `生成失败: ${data.message}`
          break
      }
    },

    // --- 播放控制 ---
    clearEffects() {
      this.spotlightTarget = null
      this.laserTarget = null
      this.currentSubtitle = ''
    },

    setSceneIndex(index) {
      this.currentSceneIndex = index
      this.currentActionIndex = 0
      this.clearEffects()
    },

    // --- 会话 CRUD ---
    async loadSessions() {
      this.sessionsLoading = true
      try {
        const data = await fetchSessions()
        this.sessions = data.sessions || []
      } catch (e) {
        console.error('Failed to load sessions:', e)
      } finally {
        this.sessionsLoading = false
      }
    },

    async loadSession(sessionId) {
      try {
        const data = await fetchSession(sessionId)
        this.currentSession = data
        this.scenes = (data.scenes || []).map(s => ({
          title: s.title,
          slideContent: s.slide_content,
          actions: s.actions,
          keyPoints: s.key_points,
        }))
        // 恢复播放进度
        if (data.playback_snapshot) {
          this.currentSceneIndex = data.playback_snapshot.sceneIndex || 0
          this.currentActionIndex = data.playback_snapshot.actionIndex || 0
        } else {
          this.currentSceneIndex = 0
          this.currentActionIndex = 0
        }
        this.playbackState = 'idle'
        this.clearEffects()
      } catch (e) {
        console.error('Failed to load session:', e)
        throw e
      }
    },

    async savePlaybackProgress() {
      if (!this.currentSession?.id) return
      try {
        await updatePlaybackSnapshot(this.currentSession.id, {
          sceneIndex: this.currentSceneIndex,
          actionIndex: this.currentActionIndex,
        })
      } catch (e) {
        console.error('Failed to save progress:', e)
      }
    },

    async removeSession(sessionId) {
      await deleteSession(sessionId)
      this.sessions = this.sessions.filter(s => s.id !== sessionId)
    },

    // --- 重置 ---
    $reset() {
      this.currentSession = null
      this.scenes = []
      this.currentSceneIndex = 0
      this.currentActionIndex = 0
      this.playbackState = 'idle'
      this.spotlightTarget = null
      this.laserTarget = null
      this.currentSubtitle = ''
      this.generatingStatus = null
      this.generatingProgress = ''
      this.outlines = []
      this.sessions = []
      this.sessionsLoading = false
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/stores/rehearsal.js
git commit -m "feat(rehearsal): add Pinia store with SSE generation and session management"
```

---

## Task 9: 前端 PlaybackEngine

**Files:**
- Create: `teacher-platform/src/composables/usePlaybackEngine.js`

- [ ] **Step 1: 创建 PlaybackEngine composable**

```javascript
// teacher-platform/src/composables/usePlaybackEngine.js
import { ref, watch } from 'vue'
import { useRehearsalStore } from '../stores/rehearsal.js'

/**
 * PlaybackEngine — 驱动预演动作序列的状态机。
 * 状态: idle → playing → paused
 *
 * 使用方式:
 *   const { start, pause, resume, stop, jumpToScene } = usePlaybackEngine()
 */
export function usePlaybackEngine() {
  const store = useRehearsalStore()
  const audioRef = ref(null) // HTML5 Audio 实例
  let readingTimer = null

  function _clearTimers() {
    if (readingTimer) {
      clearTimeout(readingTimer)
      readingTimer = null
    }
    if (audioRef.value) {
      audioRef.value.pause()
      audioRef.value.onended = null
    }
  }

  async function processNext() {
    if (store.playbackState !== 'playing') return

    const scene = store.scenes[store.currentSceneIndex]
    if (!scene) {
      // 所有场景播完
      store.playbackState = 'idle'
      store.clearEffects()
      store.savePlaybackProgress()
      return
    }

    const actions = scene.actions || []
    const actionIndex = store.currentActionIndex

    if (actionIndex >= actions.length) {
      // 当前场景动作播完，切换到下一个场景
      const nextIndex = store.currentSceneIndex + 1
      if (nextIndex >= store.scenes.length) {
        // 全部场景播完
        store.playbackState = 'idle'
        store.clearEffects()
        store.savePlaybackProgress()
        return
      }
      // 检查下一场景是否就绪（SSE 流式模式下可能还在生成）
      if (nextIndex >= store.scenes.length) {
        // 等待新场景就绪
        const unwatch = watch(() => store.scenes.length, (newLen) => {
          if (newLen > nextIndex) {
            unwatch()
            store.setSceneIndex(nextIndex)
            processNext()
          }
        })
        return
      }
      store.setSceneIndex(nextIndex)
      store.savePlaybackProgress()
      processNext()
      return
    }

    const action = actions[actionIndex]
    store.currentActionIndex = actionIndex + 1

    switch (action.type) {
      case 'speech':
        store.clearEffects()
        store.currentSubtitle = action.text || ''
        if (action.audioUrl) {
          // 播放 TTS 音频
          audioRef.value = new Audio(action.audioUrl)
          audioRef.value.onended = () => processNext()
          audioRef.value.onerror = () => {
            // 音频加载失败，降级为计时播放
            _playWithTimer(action.duration || 3000)
          }
          try {
            await audioRef.value.play()
          } catch {
            // 自动播放被阻止，降级为计时
            _playWithTimer(action.duration || 3000)
          }
        } else {
          // 无音频，用计时播放
          _playWithTimer(action.duration || 3000)
        }
        break

      case 'spotlight':
        store.spotlightTarget = {
          elementId: action.elementId,
          dimOpacity: action.dimOpacity ?? 0.4,
        }
        store.laserTarget = null
        processNext() // 即发即忘
        break

      case 'laser':
        store.laserTarget = {
          elementId: action.elementId,
          color: action.color || '#ff0000',
        }
        store.spotlightTarget = null
        processNext() // 即发即忘
        break

      case 'navigate':
        store.setSceneIndex(action.targetSceneIndex)
        processNext() // 即发即忘
        break

      default:
        processNext()
    }
  }

  function _playWithTimer(durationMs) {
    readingTimer = setTimeout(() => {
      readingTimer = null
      processNext()
    }, durationMs)
  }

  function start() {
    if (store.scenes.length === 0) return
    store.playbackState = 'playing'
    store.clearEffects()
    processNext()
  }

  function pause() {
    store.playbackState = 'paused'
    _clearTimers()
    if (audioRef.value && !audioRef.value.paused) {
      audioRef.value.pause()
    }
  }

  function resume() {
    if (store.playbackState !== 'paused') return
    store.playbackState = 'playing'
    if (audioRef.value && audioRef.value.paused && audioRef.value.src) {
      audioRef.value.play().catch(() => processNext())
    } else {
      processNext()
    }
  }

  function stop() {
    store.playbackState = 'idle'
    _clearTimers()
    store.clearEffects()
    store.savePlaybackProgress()
  }

  function jumpToScene(index) {
    _clearTimers()
    store.setSceneIndex(index)
    if (store.playbackState === 'playing') {
      processNext()
    }
  }

  function prevScene() {
    const idx = Math.max(0, store.currentSceneIndex - 1)
    jumpToScene(idx)
  }

  function nextScene() {
    const idx = Math.min(store.scenes.length - 1, store.currentSceneIndex + 1)
    jumpToScene(idx)
  }

  function cleanup() {
    _clearTimers()
    if (audioRef.value) {
      audioRef.value.pause()
      audioRef.value = null
    }
  }

  return {
    start,
    pause,
    resume,
    stop,
    jumpToScene,
    prevScene,
    nextScene,
    cleanup,
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/composables/usePlaybackEngine.js
git commit -m "feat(rehearsal): add PlaybackEngine composable state machine"
```

---

## Task 10: 前端幻灯片渲染器组件

**Files:**
- Create: `teacher-platform/src/components/rehearsal/SlideRenderer.vue`
- Create: `teacher-platform/src/components/rehearsal/SpotlightOverlay.vue`
- Create: `teacher-platform/src/components/rehearsal/LaserPointer.vue`

- [ ] **Step 1: 创建 SlideRenderer**

```vue
<!-- teacher-platform/src/components/rehearsal/SlideRenderer.vue -->
<template>
  <div class="slide-renderer" ref="containerRef" :style="containerStyle">
    <div class="slide-canvas" :style="canvasStyle" ref="canvasRef">
      <!-- 背景 -->
      <div class="slide-background" :style="backgroundStyle"></div>
      <!-- 元素 -->
      <div
        v-for="el in elements"
        :key="el.id"
        :data-element-id="el.id"
        class="slide-element"
        :style="elementStyle(el)"
      >
        <!-- 文本元素 -->
        <div v-if="el.type === 'text'" class="el-text" v-html="el.content"></div>
        <!-- 图片元素 -->
        <img
          v-else-if="el.type === 'image'"
          class="el-image"
          :src="el.src"
          :alt="el.id"
          draggable="false"
        />
        <!-- 形状元素 -->
        <div
          v-else-if="el.type === 'shape'"
          class="el-shape"
          :style="shapeStyle(el)"
        ></div>
      </div>
      <!-- 叠加层 -->
      <SpotlightOverlay v-if="spotlightTarget" :target="spotlightTarget" :canvas-ref="canvasRef" />
      <LaserPointer v-if="laserTarget" :target="laserTarget" :canvas-ref="canvasRef" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SpotlightOverlay from './SpotlightOverlay.vue'
import LaserPointer from './LaserPointer.vue'

const props = defineProps({
  slide: { type: Object, required: true },
  spotlightTarget: { type: Object, default: null },
  laserTarget: { type: Object, default: null },
})

const containerRef = ref(null)
const canvasRef = ref(null)

const viewportSize = computed(() => props.slide?.viewportSize || 1000)
const viewportRatio = computed(() => props.slide?.viewportRatio || 0.5625)
const elements = computed(() => props.slide?.elements || [])

const containerStyle = computed(() => ({
  width: '100%',
  aspectRatio: `${1 / viewportRatio.value}`,
  position: 'relative',
  overflow: 'hidden',
}))

const canvasStyle = computed(() => ({
  width: '100%',
  height: '100%',
  position: 'relative',
}))

const backgroundStyle = computed(() => {
  const bg = props.slide?.background
  if (!bg) return { backgroundColor: '#ffffff' }
  if (bg.type === 'solid') return { backgroundColor: bg.color || '#ffffff' }
  if (bg.type === 'gradient' && bg.value) return { background: bg.value }
  return { backgroundColor: '#ffffff' }
})

function elementStyle(el) {
  const scale = 100 / viewportSize.value // 百分比换算
  return {
    position: 'absolute',
    left: `${(el.left || 0) * scale}%`,
    top: `${(el.top || 0) * scale / viewportRatio.value}%`,
    width: `${(el.width || 100) * scale}%`,
    height: el.height ? `${(el.height) * scale / viewportRatio.value}%` : 'auto',
    fontSize: el.fontSize ? `${el.fontSize * scale}vw` : undefined,
    color: el.color || undefined,
    transform: el.rotate ? `rotate(${el.rotate}deg)` : undefined,
  }
}

function shapeStyle(el) {
  const shape = el.shape || 'rect'
  const base = {
    width: '100%',
    height: '100%',
    backgroundColor: el.fill || '#4A90D9',
  }
  if (shape === 'ellipse') base.borderRadius = '50%'
  else if (shape === 'roundRect') base.borderRadius = '8px'
  return base
}
</script>

<style scoped>
.slide-renderer {
  background: #000;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slide-canvas {
  background: #fff;
  border-radius: 2px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.slide-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 2px;
}

.slide-element {
  z-index: 1;
  pointer-events: none;
}

.el-text {
  word-wrap: break-word;
  overflow: hidden;
}

.el-text :deep(p) {
  margin: 0;
}

.el-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.el-shape {
  width: 100%;
  height: 100%;
}
</style>
```

- [ ] **Step 2: 创建 SpotlightOverlay**

```vue
<!-- teacher-platform/src/components/rehearsal/SpotlightOverlay.vue -->
<template>
  <div class="spotlight-overlay" v-if="targetRect">
    <svg class="spotlight-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
      <defs>
        <mask id="spotlight-mask">
          <rect x="0" y="0" width="100" height="100" fill="white" />
          <rect
            :x="targetRect.x"
            :y="targetRect.y"
            :width="targetRect.w"
            :height="targetRect.h"
            fill="black"
            rx="0.5"
            ry="0.5"
          />
        </mask>
      </defs>
      <rect
        x="0" y="0" width="100" height="100"
        :fill="`rgba(0,0,0,${target.dimOpacity || 0.4})`"
        mask="url(#spotlight-mask)"
      />
    </svg>
    <!-- 高亮边框 -->
    <div class="spotlight-border" :style="borderStyle"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  target: { type: Object, required: true },
  canvasRef: { type: Object, default: null },
})

const targetRect = ref(null)

function updateRect() {
  if (!props.canvasRef || !props.target?.elementId) {
    targetRect.value = null
    return
  }
  const canvas = props.canvasRef
  const el = canvas.querySelector(`[data-element-id="${props.target.elementId}"]`)
  if (!el) {
    targetRect.value = null
    return
  }
  const canvasRect = canvas.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  const padding = 4
  targetRect.value = {
    x: ((elRect.left - canvasRect.left - padding) / canvasRect.width) * 100,
    y: ((elRect.top - canvasRect.top - padding) / canvasRect.height) * 100,
    w: ((elRect.width + padding * 2) / canvasRect.width) * 100,
    h: ((elRect.height + padding * 2) / canvasRect.height) * 100,
  }
}

const borderStyle = computed(() => {
  if (!targetRect.value) return { display: 'none' }
  return {
    left: `${targetRect.value.x}%`,
    top: `${targetRect.value.y}%`,
    width: `${targetRect.value.w}%`,
    height: `${targetRect.value.h}%`,
  }
})

watch(() => props.target, () => { updateRect() }, { deep: true, immediate: true })
onMounted(() => { updateRect() })

let resizeObserver = null
onMounted(() => {
  if (props.canvasRef) {
    resizeObserver = new ResizeObserver(() => updateRect())
    resizeObserver.observe(props.canvasRef)
  }
})
onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<style scoped>
.spotlight-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  pointer-events: none;
}

.spotlight-svg {
  width: 100%;
  height: 100%;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.spotlight-border {
  position: absolute;
  border: 1.5px solid rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}
</style>
```

- [ ] **Step 3: 创建 LaserPointer**

```vue
<!-- teacher-platform/src/components/rehearsal/LaserPointer.vue -->
<template>
  <div class="laser-pointer" v-if="position" :style="pointerStyle">
    <div class="laser-dot" :style="{ backgroundColor: target.color || '#ff0000' }"></div>
    <div class="laser-ring" :style="{ borderColor: target.color || '#ff0000' }"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  target: { type: Object, required: true },
  canvasRef: { type: Object, default: null },
})

const position = ref(null)

function updatePosition() {
  if (!props.canvasRef || !props.target?.elementId) {
    position.value = null
    return
  }
  const el = props.canvasRef.querySelector(`[data-element-id="${props.target.elementId}"]`)
  if (!el) {
    position.value = null
    return
  }
  const canvasRect = props.canvasRef.getBoundingClientRect()
  const elRect = el.getBoundingClientRect()
  position.value = {
    x: ((elRect.left - canvasRect.left + elRect.width / 2) / canvasRect.width) * 100,
    y: ((elRect.top - canvasRect.top + elRect.height / 2) / canvasRect.height) * 100,
  }
}

const pointerStyle = computed(() => {
  if (!position.value) return { display: 'none' }
  return {
    left: `${position.value.x}%`,
    top: `${position.value.y}%`,
  }
})

watch(() => props.target, () => updatePosition(), { deep: true, immediate: true })
onMounted(() => updatePosition())
</script>

<style scoped>
.laser-pointer {
  position: absolute;
  z-index: 11;
  pointer-events: none;
  transform: translate(-50%, -50%);
}

.laser-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  opacity: 0.9;
}

.laser-ring {
  position: absolute;
  top: -6px;
  left: -6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid;
  opacity: 0.5;
  animation: laser-pulse 1s ease-in-out infinite;
}

@keyframes laser-pulse {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.5); opacity: 0.2; }
}
</style>
```

- [ ] **Step 4: 提交**

```bash
git add teacher-platform/src/components/rehearsal/SlideRenderer.vue
git add teacher-platform/src/components/rehearsal/SpotlightOverlay.vue
git add teacher-platform/src/components/rehearsal/LaserPointer.vue
git commit -m "feat(rehearsal): add SlideRenderer with Spotlight and Laser overlays"
```

---

## Task 11: 前端播放控制组件

**Files:**
- Create: `teacher-platform/src/components/rehearsal/SubtitlePanel.vue`
- Create: `teacher-platform/src/components/rehearsal/PlaybackControls.vue`

- [ ] **Step 1: 创建 SubtitlePanel**

```vue
<!-- teacher-platform/src/components/rehearsal/SubtitlePanel.vue -->
<template>
  <div class="subtitle-panel" v-if="text">
    <p class="subtitle-text">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
})
</script>

<style scoped>
.subtitle-panel {
  background: rgba(22, 27, 34, 0.95);
  padding: 12px 20px;
  border-top: 1px solid #30363d;
}

.subtitle-text {
  margin: 0;
  color: #e6edf3;
  font-size: 14px;
  line-height: 1.6;
  text-align: center;
}
</style>
```

- [ ] **Step 2: 创建 PlaybackControls**

```vue
<!-- teacher-platform/src/components/rehearsal/PlaybackControls.vue -->
<template>
  <div class="playback-controls">
    <button class="ctrl-btn" @click="$emit('prev')" :disabled="disablePrev" title="上一页">
      ⏮
    </button>
    <button class="ctrl-btn play-btn" @click="onPlayPause" :title="isPlaying ? '暂停' : '播放'">
      {{ isPlaying ? '⏸' : '▶' }}
    </button>
    <button class="ctrl-btn" @click="$emit('next')" :disabled="disableNext" title="下一页">
      ⏭
    </button>
    <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
  </div>
</template>

<script setup>
const props = defineProps({
  isPlaying: Boolean,
  isPaused: Boolean,
  currentPage: { type: Number, default: 1 },
  totalPages: { type: Number, default: 1 },
  disablePrev: Boolean,
  disableNext: Boolean,
})

const emit = defineEmits(['play', 'pause', 'resume', 'prev', 'next'])

function onPlayPause() {
  if (props.isPlaying) {
    emit('pause')
  } else if (props.isPaused) {
    emit('resume')
  } else {
    emit('play')
  }
}
</script>

<style scoped>
.playback-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 10px;
  border-top: 1px solid #30363d;
  background: #0d1117;
}

.ctrl-btn {
  background: none;
  border: none;
  color: #8b949e;
  font-size: 16px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  transition: color 0.2s;
}

.ctrl-btn:hover:not(:disabled) {
  color: #e6edf3;
}

.ctrl-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.play-btn {
  background: #58a6ff;
  color: #fff;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.play-btn:hover {
  background: #79b8ff;
  color: #fff;
}

.page-indicator {
  color: #8b949e;
  font-size: 13px;
  min-width: 50px;
  text-align: center;
}
</style>
```

- [ ] **Step 3: 提交**

```bash
git add teacher-platform/src/components/rehearsal/SubtitlePanel.vue
git add teacher-platform/src/components/rehearsal/PlaybackControls.vue
git commit -m "feat(rehearsal): add SubtitlePanel and PlaybackControls components"
```

---

## Task 12: 前端页面 — RehearsalNew

**Files:**
- Create: `teacher-platform/src/views/rehearsal/RehearsalNew.vue`

- [ ] **Step 1: 创建新建预演页面**

```vue
<!-- teacher-platform/src/views/rehearsal/RehearsalNew.vue -->
<template>
  <div class="rehearsal-new">
    <div class="new-card">
      <h2>课堂预演</h2>
      <p class="desc">输入教学主题，AI 为您生成可播放的课堂预演</p>

      <div class="form-group">
        <label>教学主题</label>
        <el-input
          v-model="topic"
          type="textarea"
          :rows="3"
          placeholder="例：高中物理 - 牛顿第二定律"
          :disabled="isGenerating"
        />
      </div>

      <div class="form-row">
        <div class="form-group half">
          <label>语言</label>
          <el-select v-model="language" :disabled="isGenerating">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </div>
        <div class="form-group half">
          <label>语音合成</label>
          <el-switch v-model="enableTTS" :disabled="isGenerating" />
        </div>
      </div>

      <el-button
        type="primary"
        :loading="isGenerating"
        :disabled="!topic.trim() || isGenerating"
        @click="handleGenerate"
        style="width: 100%"
      >
        {{ isGenerating ? '生成中...' : '开始生成' }}
      </el-button>

      <!-- 进度 -->
      <div v-if="store.generatingStatus" class="progress-section">
        <el-progress
          :percentage="progressPercent"
          :status="progressStatus"
          :stroke-width="8"
        />
        <p class="progress-text">{{ store.generatingProgress }}</p>

        <el-button
          v-if="store.generatingStatus === 'complete' && store.currentSession"
          type="success"
          @click="goToPlay"
          style="width: 100%; margin-top: 12px"
        >
          开始播放
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'

const router = useRouter()
const store = useRehearsalStore()

const topic = ref('')
const language = ref('zh-CN')
const enableTTS = ref(true)

const isGenerating = computed(() => store.generatingStatus === 'generating')

const progressPercent = computed(() => {
  if (!store.outlines.length) return 10
  return Math.round((store.scenes.length / store.outlines.length) * 90) + 10
})

const progressStatus = computed(() => {
  if (store.generatingStatus === 'error') return 'exception'
  if (store.generatingStatus === 'complete') return 'success'
  return undefined
})

async function handleGenerate() {
  store.$reset()
  await store.startGenerate({
    topic: topic.value.trim(),
    language: language.value,
    enable_tts: enableTTS.value,
    voice: 'Cherry',
    speed: 1.0,
  })

  // 生成完成后自动跳转（如果有场景）
  if (store.scenes.length > 0 && store.currentSession?.id) {
    router.push(`/rehearsal/play/${store.currentSession.id}`)
  }
}

function goToPlay() {
  if (store.currentSession?.id) {
    router.push(`/rehearsal/play/${store.currentSession.id}`)
  }
}
</script>

<style scoped>
.rehearsal-new {
  max-width: 560px;
  margin: 60px auto;
  padding: 0 20px;
}

.new-card {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

h2 {
  margin: 0 0 4px;
  font-size: 22px;
}

.desc {
  color: #8b949e;
  font-size: 14px;
  margin: 0 0 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #57606a;
  margin-bottom: 6px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.half {
  flex: 1;
}

.progress-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.progress-text {
  font-size: 13px;
  color: #58a6ff;
  margin: 8px 0 0;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalNew.vue
git commit -m "feat(rehearsal): add RehearsalNew page with SSE generation"
```

---

## Task 13: 前端页面 — RehearsalPlay

**Files:**
- Create: `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`

- [ ] **Step 1: 创建播放页面**

```vue
<!-- teacher-platform/src/views/rehearsal/RehearsalPlay.vue -->
<template>
  <div class="rehearsal-play">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <button class="back-btn" @click="goBack">← 返回</button>
      <span class="title">{{ store.currentSession?.title || '课堂预演' }}</span>
      <span class="page-info">第 {{ store.currentSceneIndex + 1 }}/{{ store.totalScenes }} 页</span>
    </div>

    <!-- 幻灯片区域 -->
    <div class="slide-area">
      <SlideRenderer
        v-if="currentSlide"
        :slide="currentSlide"
        :spotlight-target="store.spotlightTarget"
        :laser-target="store.laserTarget"
      />
      <div v-else class="empty-slide">
        <p>暂无内容</p>
      </div>
    </div>

    <!-- 字幕 -->
    <SubtitlePanel :text="store.currentSubtitle" />

    <!-- 播放控制 -->
    <PlaybackControls
      :is-playing="store.isPlaying"
      :is-paused="store.isPaused"
      :current-page="store.currentSceneIndex + 1"
      :total-pages="store.totalScenes"
      :disable-prev="store.currentSceneIndex <= 0"
      :disable-next="store.currentSceneIndex >= store.totalScenes - 1"
      @play="engine.start()"
      @pause="engine.pause()"
      @resume="engine.resume()"
      @prev="engine.prevScene()"
      @next="engine.nextScene()"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRehearsalStore } from '../../stores/rehearsal.js'
import { usePlaybackEngine } from '../../composables/usePlaybackEngine.js'
import SlideRenderer from '../../components/rehearsal/SlideRenderer.vue'
import SubtitlePanel from '../../components/rehearsal/SubtitlePanel.vue'
import PlaybackControls from '../../components/rehearsal/PlaybackControls.vue'

const route = useRoute()
const router = useRouter()
const store = useRehearsalStore()
const engine = usePlaybackEngine()

const currentSlide = computed(() => {
  const scene = store.currentScene
  return scene?.slideContent || null
})

onMounted(async () => {
  const sessionId = Number(route.params.id)
  if (sessionId && (!store.currentSession || store.currentSession.id !== sessionId)) {
    try {
      await store.loadSession(sessionId)
    } catch {
      router.push('/rehearsal/history')
    }
  }
})

onBeforeUnmount(() => {
  engine.cleanup()
  store.savePlaybackProgress()
})

function goBack() {
  engine.stop()
  router.push('/rehearsal/history')
}
</script>

<style scoped>
.rehearsal-play {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid #30363d;
  flex-shrink: 0;
}

.back-btn {
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  font-size: 14px;
}

.back-btn:hover {
  color: #e6edf3;
}

.title {
  font-size: 15px;
  font-weight: 500;
}

.page-info {
  font-size: 13px;
  color: #8b949e;
}

.slide-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  min-height: 0;
}

.slide-area > * {
  max-width: 900px;
  width: 100%;
}

.empty-slide {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b949e;
  font-size: 16px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalPlay.vue
git commit -m "feat(rehearsal): add RehearsalPlay page with slide renderer and playback"
```

---

## Task 14: 前端页面 — RehearsalHistory

**Files:**
- Create: `teacher-platform/src/views/rehearsal/RehearsalHistory.vue`

- [ ] **Step 1: 创建历史列表页面**

```vue
<!-- teacher-platform/src/views/rehearsal/RehearsalHistory.vue -->
<template>
  <div class="rehearsal-history">
    <div class="header">
      <h2>预演历史</h2>
      <el-button type="primary" @click="$router.push('/rehearsal/new')">+ 新建预演</el-button>
    </div>

    <div v-if="store.sessionsLoading" class="loading">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="store.sessions.length === 0" class="empty">
      <p>暂无预演记录</p>
      <el-button type="primary" @click="$router.push('/rehearsal/new')">创建第一个预演</el-button>
    </div>

    <div v-else class="session-list">
      <div
        v-for="session in store.sessions"
        :key="session.id"
        class="session-card"
      >
        <div class="card-info">
          <h3>{{ session.title }}</h3>
          <p class="card-meta">
            {{ session.ready_scenes || session.total_scenes }} 页 ·
            {{ formatTime(session.updated_at) }}
          </p>
        </div>
        <div class="card-actions">
          <el-tag :type="statusTagType(session.status)" size="small">
            {{ statusLabel(session.status) }}
          </el-tag>
          <el-button
            v-if="session.status === 'ready' || session.status === 'partial'"
            type="primary"
            size="small"
            text
            @click="$router.push(`/rehearsal/play/${session.id}`)"
          >
            ▶ 播放
          </el-button>
          <el-button
            type="danger"
            size="small"
            text
            @click="handleDelete(session.id)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRehearsalStore } from '../../stores/rehearsal.js'

const store = useRehearsalStore()

onMounted(() => {
  store.loadSessions()
})

function statusLabel(status) {
  const map = {
    generating: '生成中',
    partial: '部分完成',
    ready: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function statusTagType(status) {
  const map = {
    generating: 'warning',
    partial: 'info',
    ready: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定要删除这个预演吗？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.removeSession(id)
  } catch { /* 取消 */ }
}
</script>

<style scoped>
.rehearsal-history {
  max-width: 800px;
  margin: 40px auto;
  padding: 0 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

h2 {
  margin: 0;
  font-size: 20px;
}

.empty {
  text-align: center;
  padding: 60px 0;
  color: #8b949e;
}

.session-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 10px;
  transition: box-shadow 0.2s;
}

.session-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-info h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.card-meta {
  margin: 0;
  font-size: 13px;
  color: #8b949e;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalHistory.vue
git commit -m "feat(rehearsal): add RehearsalHistory page with session list"
```

---

## Task 15: 前端路由注册

**Files:**
- Modify: `teacher-platform/src/router/index.js`

- [ ] **Step 1: 添加预演路由**

在 `routes` 数组中，`{ path: '/:pathMatch(.*)*', redirect: '/' }` 之前添加：

```javascript
{
  path: '/rehearsal/new',
  name: 'RehearsalNew',
  component: () => import('../views/rehearsal/RehearsalNew.vue'),
  meta: { requiresAuth: true, layout: 'nav' }
},
{
  path: '/rehearsal/play/:id',
  name: 'RehearsalPlay',
  component: () => import('../views/rehearsal/RehearsalPlay.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/rehearsal/history',
  name: 'RehearsalHistory',
  component: () => import('../views/rehearsal/RehearsalHistory.vue'),
  meta: { requiresAuth: true, layout: 'nav' }
},
```

注意：RehearsalPlay 不带 `layout: 'nav'`，因为播放页应该全屏展示。

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/router/index.js
git commit -m "feat(rehearsal): register rehearsal routes"
```

---

## Task 16: 集成验证

- [ ] **Step 1: 启动后端，验证迁移和路由注册**

```bash
cd backend
alembic upgrade head
python run.py
```

访问 `http://localhost:8000/docs`，确认 `/api/v1/rehearsal/` 下的接口出现在 Swagger 文档中。

- [ ] **Step 2: 启动前端，验证路由和页面加载**

```bash
cd teacher-platform
npm run dev
```

访问：
- `http://localhost:5173/rehearsal/new` — 新建预演页面
- `http://localhost:5173/rehearsal/history` — 历史列表页面

- [ ] **Step 3: 端到端测试**

1. 在新建预演页面输入主题（如"高中物理 - 牛顿第二定律"）
2. 点击"开始生成"
3. 观察进度条和进度文案更新
4. 生成完成后点击"开始播放"
5. 在播放页验证：幻灯片渲染、Spotlight 聚焦、字幕显示、播放/暂停/翻页
6. 返回历史列表，确认会话出现且状态正确
7. 重新点击播放，验证会话恢复

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat(rehearsal): classroom rehearsal MVP complete"
```
