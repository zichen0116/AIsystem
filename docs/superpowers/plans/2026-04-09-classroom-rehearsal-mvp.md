# 课堂预演 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现课堂预演 MVP — 用户输入教学主题，后端任务编排逐页生成幻灯片+动作序列，TTS 异步补齐，前端实时预览已完成页面并支持播放。

**Architecture:** 后端主导编排，页级增量持久化（DB 为唯一真相源）。SSE 仅作进度通知通道，前端通过 REST 获取完整数据。TTS 异步非阻塞，页面先 ready 再补音频。支持页级状态和单页重试。

**Tech Stack:** Python/FastAPI, SQLAlchemy async, DashScope LLM (qwen-plus) + TTS (qwen3-tts-flash), Vue 3/Pinia, 自建 SlideRenderer

**重要说明：PPTist 不是 npm 包，OpenMAIC 也没有使用 PPTist 包，而是自建了渲染器。本计划采用自建轻量 Vue 幻灯片渲染器，仅实现文本、图片、形状三种元素类型（MVP 够用），后续阶段再补充图表、LaTeX 等。**

---

## 文件结构

### 后端新增

```
backend/app/
├── api/rehearsal.py                         # API 路由（generate-stream, sessions/scenes CRUD, retry）
├── models/rehearsal.py                      # ORM：RehearsalSession + RehearsalScene
├── schemas/rehearsal.py                     # Pydantic 请求/响应模型
└── services/
    ├── rehearsal_generation_service.py       # 生成编排（大纲→逐页内容+动作，页级持久化）
    ├── rehearsal_session_service.py          # 会话/场景 CRUD
    └── tts_service.py                       # Qwen TTS + 音频持久化到 OSS
```

### 后端修改

```
backend/app/models/__init__.py               # 导出新模型
backend/app/api/__init__.py                  # 注册新路由
backend/app/services/oss_service.py          # 新增 upload_bytes() 支持音频上传
```

### 前端新增

```
teacher-platform/src/
├── api/rehearsal.js                         # 后端 API 调用封装
├── stores/rehearsal.js                      # Pinia store
├── composables/usePlaybackEngine.js         # PlaybackEngine 状态机
├── views/rehearsal/
│   ├── RehearsalNew.vue                     # 新建预演页（含生成预览）
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
    # 会话级状态：由页级状态汇总得出
    # generating: 有页面正在生成中
    # partial: 部分页面 ready，部分 failed，无 generating/pending
    # ready: 所有页面 ready
    # failed: 所有页面 failed 或无页面
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    total_scenes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    # 页级状态：pending → generating → ready / failed
    scene_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    slide_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # 页级 TTS 音频粗略摘要：pending / partial / ready / failed
    # 播放逻辑以 action 级 audio_status 为准（在 actions JSONB 中每个 speech action 各有自己的 audio_status）
    audio_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
git commit -m "feat(rehearsal): add RehearsalSession and RehearsalScene models with page-level status"
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

class RehearsalSceneResponse(BaseModel):
    id: int
    scene_order: int
    title: str
    scene_status: str
    slide_content: dict | None = None
    actions: list | None = None
    key_points: list | None = None
    audio_status: str
    error_message: str | None = None

    model_config = {"from_attributes": True}


class RehearsalSessionSummary(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    total_scenes: int
    language: str
    created_at: datetime
    updated_at: datetime
    # 汇总信息
    ready_count: int = 0
    failed_count: int = 0

    model_config = {"from_attributes": True}


class RehearsalSessionDetail(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    total_scenes: int
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
git commit -m "feat(rehearsal): add Pydantic schemas with page-level status"
```

---

## Task 3: 扩展 OSS 服务支持音频上传

**Files:**
- Modify: `backend/app/services/oss_service.py`

- [ ] **Step 1: 在 oss_service.py 末尾新增 upload_bytes 函数**

在文件末尾添加：

```python
async def upload_bytes(
    content: bytes,
    ext: str,
    user_id: int,
    prefix: str = "rehearsal-audio",
) -> str:
    """
    上传程序生成的字节内容到 OSS（用于 TTS 音频等非用户上传场景）。
    Returns: 公开访问 URL
    """
    object_key = f"{prefix}/{user_id}/{uuid.uuid4().hex}.{ext}"
    bucket = _get_bucket()
    bucket.put_object(object_key, content)

    endpoint_host = settings.OSS_ENDPOINT.replace("https://", "").replace("http://", "")
    url = f"https://{settings.OSS_BUCKET}.{endpoint_host}/{object_key}"
    logger.info(f"Bytes uploaded: {len(content)} bytes -> {url}")
    return url
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/oss_service.py
git commit -m "feat(oss): add upload_bytes for programmatic audio upload"
```

---

## Task 4: 后端 TTS Service（修正版）

**Files:**
- Create: `backend/app/services/tts_service.py`

- [ ] **Step 1: 创建 Qwen TTS 服务**

按 OpenMAIC 验证过的请求格式实现，含音频下载+OSS持久化：

```python
# backend/app/services/tts_service.py
"""
Qwen TTS 轻量封装 — 单 provider，不做多 provider 架构。
调用阿里云百炼 DashScope multimodal-generation 接口。
TTS 失败时返回 None，调用方降级为计时播放。
音频持久化到 OSS，返回持久 URL。
"""
import logging
import httpx

from app.core.config import get_settings
from app.services.oss_service import upload_bytes

logger = logging.getLogger(__name__)
settings = get_settings()

DASHSCOPE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen3-tts-flash"
DEFAULT_VOICE = "Cherry"


def _speed_to_rate(speed: float) -> int:
    """将播放速度 (0.5-2.0) 转换为 DashScope rate 参数 (-500 to 500)。"""
    return round((speed - 1.0) * 500)


async def synthesize(
    text: str,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    user_id: int = 0,
    persist: bool = True,
) -> dict:
    """
    合成语音。返回:
    {
        "temp_audio_url": str | None,      # DashScope 返回的临时 URL（约24h有效）
        "persistent_audio_url": str | None, # OSS 持久 URL
        "audio_status": "temp_ready" | "ready" | "failed",
        "duration": int,                    # 预估时长 ms
    }
    """
    duration = estimate_duration_ms(text, speed)
    result = {
        "temp_audio_url": None,
        "persistent_audio_url": None,
        "audio_status": "failed",
        "duration": duration,
    }

    if not settings.DASHSCOPE_API_KEY:
        logger.warning("DASHSCOPE_API_KEY not set, skipping TTS")
        return result

    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "model": DEFAULT_MODEL,
        "input": {
            "text": text,
            "voice": voice,
            "language_type": "Chinese",
        },
        "parameters": {
            "rate": _speed_to_rate(speed),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. 调用 TTS API
            resp = await client.post(DASHSCOPE_TTS_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            temp_url = data.get("output", {}).get("audio", {}).get("url")

            if not temp_url:
                logger.warning(f"TTS response missing audio URL: {data}")
                return result

            result["temp_audio_url"] = temp_url
            result["audio_status"] = "temp_ready"

            # 2. 下载音频并持久化到 OSS
            if persist and user_id:
                try:
                    audio_resp = await client.get(temp_url, timeout=30.0)
                    audio_resp.raise_for_status()
                    audio_bytes = audio_resp.content
                    persistent_url = await upload_bytes(audio_bytes, "wav", user_id, "rehearsal-audio")
                    result["persistent_audio_url"] = persistent_url
                    result["audio_status"] = "ready"
                    logger.info(f"TTS persisted: {len(text)} chars -> {persistent_url[:80]}...")
                except Exception as e:
                    logger.warning(f"TTS audio persist failed (temp URL still usable): {e}")
                    # 保持 temp_ready 状态

            return result

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return result


def estimate_duration_ms(text: str, speed: float = 1.0) -> int:
    """估算文本阅读时长（毫秒），用于无音频时的计时播放。"""
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    non_cjk = text
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            non_cjk = non_cjk.replace(c, '', 1)
    word_count = len(non_cjk.split())
    duration = cjk_count * 150 + word_count * 240
    duration = max(duration, 2000)
    return int(duration / speed)
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/tts_service.py
git commit -m "feat(rehearsal): add Qwen TTS service with audio persistence to OSS"
```

---

## Task 5: 后端会话/场景 CRUD Service

**Files:**
- Create: `backend/app/services/rehearsal_session_service.py`

- [ ] **Step 1: 创建会话服务**

```python
# backend/app/services/rehearsal_session_service.py
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rehearsal import RehearsalSession, RehearsalScene

logger = logging.getLogger(__name__)


async def list_sessions(db: AsyncSession, user_id: int) -> list[dict]:
    """列出会话，附带 ready_count 和 failed_count 汇总。"""
    result = await db.execute(
        select(RehearsalSession)
        .options(selectinload(RehearsalSession.scenes))
        .where(RehearsalSession.user_id == user_id)
        .order_by(RehearsalSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        ready = sum(1 for sc in s.scenes if sc.scene_status == "ready")
        failed = sum(1 for sc in s.scenes if sc.scene_status == "failed")
        out.append({
            "id": s.id, "title": s.title, "topic": s.topic,
            "status": s.status, "total_scenes": s.total_scenes,
            "language": s.language,
            "created_at": s.created_at, "updated_at": s.updated_at,
            "ready_count": ready, "failed_count": failed,
        })
    return out


async def get_session_with_scenes(
    db: AsyncSession, session_id: int, user_id: int
) -> RehearsalSession | None:
    result = await db.execute(
        select(RehearsalSession)
        .options(selectinload(RehearsalSession.scenes))
        .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_scene(
    db: AsyncSession, session_id: int, scene_order: int, user_id: int
) -> RehearsalScene | None:
    """获取单个场景（校验 user_id 所有权）。"""
    result = await db.execute(
        select(RehearsalScene)
        .join(RehearsalSession)
        .where(
            RehearsalScene.session_id == session_id,
            RehearsalScene.scene_order == scene_order,
            RehearsalSession.user_id == user_id,
        )
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


def compute_session_status(session: RehearsalSession) -> str:
    """根据页级状态汇总计算会话级状态。"""
    if not session.scenes:
        return "failed"
    statuses = [s.scene_status for s in session.scenes]
    if any(st in ("pending", "generating") for st in statuses):
        return "generating"
    if all(st == "ready" for st in statuses):
        return "ready"
    if all(st == "failed" for st in statuses):
        return "failed"
    return "partial"


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
git commit -m "feat(rehearsal): add session/scene CRUD service with status aggregation"
```

---

## Task 6: 后端生成服务（页级增量持久化 + TTS 异步）

**Files:**
- Create: `backend/app/services/rehearsal_generation_service.py`

- [ ] **Step 1: 创建生成服务**

```python
# backend/app/services/rehearsal_generation_service.py
"""
课堂预演生成管线。
- SSE 仅作进度通知通道（精简事件），不承载完整 scene 数据
- 页级增量持久化到 DB
- TTS 异步非阻塞，页面先 ready 再补音频
- 支持单页重试
"""
import json
import logging
import asyncio
from typing import AsyncGenerator

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.rehearsal import RehearsalSession, RehearsalScene
from app.services.lesson_plan_service import stream_llm
from app.services.tts_service import synthesize, estimate_duration_ms
from app.services.rehearsal_session_service import compute_session_status

logger = logging.getLogger(__name__)
settings = get_settings()


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------- LLM Prompts ----------

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


# ---------- LLM Helper ----------

async def _call_llm_json(system_prompt: str, user_prompt: str) -> dict | list | None:
    """调用 LLM 并解析 JSON 输出。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    full = ""
    async for chunk in stream_llm(messages):
        full += chunk

    text = full.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('[') if '[' in text else text.find('{')
        end = text.rfind(']') + 1 if ']' in text else text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        logger.error(f"Failed to parse LLM JSON: {text[:200]}...")
        return None


# ---------- 页级生成 ----------

async def _generate_scene(
    session_id: int, scene_id: int, scene_order: int,
    outline: dict, all_outlines_text: str, total: int,
    enable_tts: bool, voice: str, speed: float, user_id: int,
) -> str:
    """
    生成单页内容+动作，落库。TTS 异步补齐。
    返回最终的 scene_status。
    """
    async with AsyncSessionLocal() as db:
        try:
            # 标记为 generating
            scene = await db.get(RehearsalScene, scene_id)
            if not scene:
                return "failed"
            scene.scene_status = "generating"
            await db.commit()

            # 1. 生成 slide content
            slide_prompt = (
                f"场景标题：{outline['title']}\n"
                f"场景描述：{outline.get('description', '')}\n"
                f"要点：{json.dumps(outline.get('keyPoints', []), ensure_ascii=False)}\n"
                f"这是第 {scene_order + 1}/{total} 页\n"
                f"课程所有大纲：{all_outlines_text}"
            )
            slide_content = await _call_llm_json(SLIDE_CONTENT_SYSTEM_PROMPT, slide_prompt)
            if not slide_content or not isinstance(slide_content, dict):
                slide_content = _fallback_slide(outline, scene_order)

            # 2. 生成 actions
            element_ids = [el.get("id", "") for el in slide_content.get("elements", [])]
            actions_prompt = (
                f"幻灯片标题：{outline['title']}\n"
                f"要点：{json.dumps(outline.get('keyPoints', []), ensure_ascii=False)}\n"
                f"幻灯片元素 ID 列表：{json.dumps(element_ids)}\n"
                f"这是第 {scene_order + 1}/{total} 页"
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

            # 补充 duration 到 speech actions
            for action in actions:
                if action.get("type") == "speech":
                    action["duration"] = estimate_duration_ms(action.get("text", ""), speed)
                    action["audio_status"] = "pending"

            # 3. 落库：页面标记 ready（无音频也可播放）
            scene = await db.get(RehearsalScene, scene_id)
            scene.slide_content = slide_content
            scene.actions = actions
            scene.scene_status = "ready"
            scene.audio_status = "pending" if enable_tts else "failed"
            await db.commit()

            # 4. TTS 异步补齐（不阻塞页面 ready）
            if enable_tts:
                asyncio.create_task(
                    _fill_tts_for_scene(scene_id, actions, voice, speed, user_id)
                )

            return "ready"

        except Exception as e:
            logger.error(f"Scene {scene_order} generation failed: {e}")
            try:
                scene = await db.get(RehearsalScene, scene_id)
                if scene:
                    scene.scene_status = "failed"
                    scene.error_message = str(e)[:500]
                    await db.commit()
            except Exception:
                await db.rollback()
            return "failed"


async def _fill_tts_for_scene(
    scene_id: int, actions: list, voice: str, speed: float, user_id: int
):
    """异步为场景的 speech actions 补齐 TTS 音频。"""
    async with AsyncSessionLocal() as db:
        try:
            scene = await db.get(RehearsalScene, scene_id)
            if not scene:
                return

            updated_actions = list(scene.actions or [])
            total_speech = 0
            success_count = 0

            for action in updated_actions:
                if action.get("type") != "speech" or not action.get("text"):
                    continue
                total_speech += 1
                tts_result = await synthesize(action["text"], voice, speed, user_id)
                action["temp_audio_url"] = tts_result["temp_audio_url"]
                action["persistent_audio_url"] = tts_result["persistent_audio_url"]
                action["audio_status"] = tts_result["audio_status"]
                if tts_result["audio_status"] in ("temp_ready", "ready"):
                    success_count += 1

            scene.actions = updated_actions
            # 页级 audio_status 是粗略摘要，播放逻辑以 action 级 audio_status 为准
            if total_speech == 0:
                scene.audio_status = "ready"
            elif success_count == total_speech:
                scene.audio_status = "ready"
            elif success_count > 0:
                scene.audio_status = "partial"
            else:
                scene.audio_status = "failed"
            await db.commit()
            logger.info(f"TTS fill completed for scene {scene_id}: audio_status={scene.audio_status}")

        except Exception as e:
            logger.error(f"TTS fill failed for scene {scene_id}: {e}")


# ---------- 主生成管线 ----------

async def generate_stream(
    topic: str, language: str, enable_tts: bool,
    voice: str, speed: float, user_id: int,
) -> AsyncGenerator[str, None]:
    """SSE 流式生成预演。SSE 仅作进度通知，完整数据从 DB 获取。"""

    async with AsyncSessionLocal() as db:
        try:
            # 创建会话
            session = RehearsalSession(
                user_id=user_id,
                title=f"{topic[:80]} - 课堂预演",
                topic=topic,
                status="generating",
                language=language,
                settings={"voice": voice, "speed": speed, "enableTTS": enable_tts},
            )
            db.add(session)
            await db.flush()
            session_id = session.id

            yield _sse_event("session_created", {"sessionId": session_id, "title": session.title})

            # Stage 1: 大纲
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

            # 预创建所有 scene 记录（pending 状态）
            scene_ids = []
            for idx, outline in enumerate(outlines):
                scene = RehearsalScene(
                    session_id=session_id,
                    scene_order=idx,
                    title=outline["title"],
                    scene_status="pending",
                    key_points=outline.get("keyPoints"),
                )
                db.add(scene)
                await db.flush()
                scene_ids.append(scene.id)

            await db.commit()

            yield _sse_event("outline_ready", {
                "totalScenes": len(outlines),
                "outlines": [{"title": o["title"], "description": o.get("description", "")} for o in outlines],
            })

            # Stage 2: 逐页生成
            all_outlines_text = json.dumps(outlines, ensure_ascii=False)

            for idx, outline in enumerate(outlines):
                scene_status = await _generate_scene(
                    session_id=session_id,
                    scene_id=scene_ids[idx],
                    scene_order=idx,
                    outline=outline,
                    all_outlines_text=all_outlines_text,
                    total=len(outlines),
                    enable_tts=enable_tts,
                    voice=voice,
                    speed=speed,
                    user_id=user_id,
                )

                # SSE 通知：只发精简状态，前端从 DB 获取完整数据
                yield _sse_event("scene_status", {
                    "sceneIndex": idx,
                    "sceneId": scene_ids[idx],
                    "status": scene_status,
                    "title": outline["title"],
                })

            # 汇总会话状态
            async with AsyncSessionLocal() as db2:
                session = await db2.get(RehearsalSession, session_id)
                from sqlalchemy.orm import selectinload
                from sqlalchemy import select
                result = await db2.execute(
                    select(RehearsalSession)
                    .options(selectinload(RehearsalSession.scenes))
                    .where(RehearsalSession.id == session_id)
                )
                session = result.scalar_one()
                session.status = compute_session_status(session)
                await db2.commit()

                yield _sse_event("complete", {
                    "sessionId": session_id,
                    "status": session.status,
                })

        except Exception as e:
            logger.error(f"Generation pipeline failed: {e}")
            try:
                session.status = "failed"
                session.error_message = str(e)[:500]
                await db.commit()
            except Exception:
                await db.rollback()
            yield _sse_event("error", {"message": str(e)})


# ---------- 单页重试 ----------

async def retry_scene(session_id: int, scene_order: int, user_id: int) -> str:
    """重试单页生成。返回新的 scene_status。"""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # 验证权限并获取 session
        result = await db.execute(
            select(RehearsalSession)
            .options(selectinload(RehearsalSession.scenes))
            .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Session not found")

        scene = next((s for s in session.scenes if s.scene_order == scene_order), None)
        if not scene:
            raise ValueError("Scene not found")

        # 从 session settings 获取配置
        stg = session.settings or {}
        outline = {
            "title": scene.title,
            "keyPoints": scene.key_points or [],
            "description": "",
        }
        all_outlines = [
            {"title": s.title, "keyPoints": s.key_points or []}
            for s in session.scenes
        ]

    # 在 DB session 外执行生成
    scene_status = await _generate_scene(
        session_id=session_id,
        scene_id=scene.id,
        scene_order=scene_order,
        outline=outline,
        all_outlines_text=json.dumps(all_outlines, ensure_ascii=False),
        total=session.total_scenes,
        enable_tts=stg.get("enableTTS", True),
        voice=stg.get("voice", "Cherry"),
        speed=stg.get("speed", 1.0),
        user_id=user_id,
    )

    # 更新会话级状态
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(RehearsalSession)
            .options(selectinload(RehearsalSession.scenes))
            .where(RehearsalSession.id == session_id)
        )
        session = result.scalar_one()
        session.status = compute_session_status(session)
        await db.commit()

    return scene_status


def _fallback_slide(outline: dict, idx: int) -> dict:
    """LLM 生成 slide 失败时的降级方案。"""
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
git commit -m "feat(rehearsal): add generation service with page-level persistence and async TTS"
```

---

## Task 7: 后端 API 路由

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
    RehearsalSceneResponse,
)
from app.services import rehearsal_session_service as session_svc
from app.services.rehearsal_generation_service import generate_stream, retry_scene

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rehearsal", tags=["rehearsal"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/generate-stream")
async def generate_rehearsal_stream(req: RehearsalGenerateRequest, user: CurrentUser):
    """SSE 流式生成课堂预演（仅通知进度，完整数据从 sessions/{id} 获取）。"""
    return StreamingResponse(
        generate_stream(
            topic=req.topic, language=req.language, enable_tts=req.enable_tts,
            voice=req.voice, speed=req.speed, user_id=user.id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions", response_model=RehearsalSessionListResponse)
async def list_sessions(user: CurrentUser, db: DbSession):
    """获取预演会话列表（含页级状态汇总）。"""
    sessions = await session_svc.list_sessions(db, user.id)
    return RehearsalSessionListResponse(
        sessions=[RehearsalSessionSummary(**s) for s in sessions]
    )


@router.get("/sessions/{session_id}", response_model=RehearsalSessionDetail)
async def get_session(session_id: int, user: CurrentUser, db: DbSession):
    """获取预演会话详情（含所有场景和页级状态）。"""
    session = await session_svc.get_session_with_scenes(db, session_id, user.id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预演不存在")
    return RehearsalSessionDetail.model_validate(session)


@router.get("/sessions/{session_id}/scenes/{scene_order}", response_model=RehearsalSceneResponse)
async def get_scene(session_id: int, scene_order: int, user: CurrentUser, db: DbSession):
    """获取单个场景（用于前端增量获取已就绪页面）。"""
    scene = await session_svc.get_scene(db, session_id, scene_order, user.id)
    if not scene:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "场景不存在")
    return RehearsalSceneResponse.model_validate(scene)


@router.post("/sessions/{session_id}/scenes/{scene_order}/retry")
async def retry_scene_endpoint(session_id: int, scene_order: int, user: CurrentUser):
    """重试生成失败的单个场景。"""
    try:
        new_status = await retry_scene(session_id, scene_order, user.id)
        return {"scene_status": new_status}
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


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

- [ ] **Step 2: 注册路由到 `__init__.py`**

在 `backend/app/api/__init__.py` 添加：

```python
from app.api import rehearsal
```

并添加：

```python
api_router.include_router(rehearsal.router)
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/rehearsal.py backend/app/api/__init__.py
git commit -m "feat(rehearsal): add API routes with scene-level endpoints and retry"
```

---

## Task 8: 前端 API 层

**Files:**
- Create: `teacher-platform/src/api/rehearsal.js`

- [ ] **Step 1: 创建 API 封装**

```javascript
// teacher-platform/src/api/rehearsal.js
import { apiRequest, authFetch } from './http.js'

const API = '/api/v1/rehearsal'

/** SSE 流式生成（返回 Response，调用方读 SSE） */
export async function generateRehearsalStream(params) {
  return await authFetch(`${API}/generate-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

/** 会话列表 */
export async function fetchSessions() {
  return await apiRequest(`${API}/sessions`)
}

/** 会话详情（含全部场景） */
export async function fetchSession(sessionId) {
  return await apiRequest(`${API}/sessions/${sessionId}`)
}

/** 获取单个场景 */
export async function fetchScene(sessionId, sceneOrder) {
  return await apiRequest(`${API}/sessions/${sessionId}/scenes/${sceneOrder}`)
}

/** 重试失败场景 */
export async function retryScene(sessionId, sceneOrder) {
  return await apiRequest(`${API}/sessions/${sessionId}/scenes/${sceneOrder}/retry`, {
    method: 'POST',
  })
}

/** 更新播放进度 */
export async function updatePlaybackSnapshot(sessionId, snapshot) {
  return await apiRequest(`${API}/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ playback_snapshot: snapshot }),
  })
}

/** 删除预演 */
export async function deleteSession(sessionId) {
  return await apiRequest(`${API}/sessions/${sessionId}`, { method: 'DELETE' })
}
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/api/rehearsal.js
git commit -m "feat(rehearsal): add frontend API layer with scene-level endpoints"
```

---

## Task 9: 前端 Pinia Store

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
  fetchScene,
  retryScene,
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
    spotlightTarget: null,
    laserTarget: null,
    currentSubtitle: '',

    // 生成状态
    generatingStatus: null, // null | generating | complete | error
    generatingProgress: '',
    totalScenes: 0,
    sceneStatuses: [], // [{sceneIndex, status, title}]

    // 历史列表
    sessions: [],
    sessionsLoading: false,
  }),

  getters: {
    currentScene(state) {
      return state.scenes[state.currentSceneIndex] || null
    },
    totalScenesCount(state) {
      return state.scenes.length
    },
    isPlaying(state) {
      return state.playbackState === 'playing'
    },
    isPaused(state) {
      return state.playbackState === 'paused'
    },
    readySceneCount(state) {
      return state.sceneStatuses.filter(s => s.status === 'ready').length
    },
    failedSceneCount(state) {
      return state.sceneStatuses.filter(s => s.status === 'failed').length
    },
  },

  actions: {
    // --- SSE 生成（通知模式） ---
    async startGenerate(params) {
      this.generatingStatus = 'generating'
      this.generatingProgress = '正在生成大纲...'
      this.scenes = []
      this.sceneStatuses = []
      this.currentSession = null
      this.totalScenes = 0

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
          buffer = lines.pop()

          let eventType = null
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                this._handleSSEEvent(eventType, data)
              } catch { /* ignore */ }
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
      }
    },

    _handleSSEEvent(eventType, data) {
      switch (eventType) {
        case 'session_created':
          this.currentSession = { id: data.sessionId, title: data.title }
          break

        case 'outline_ready':
          this.totalScenes = data.totalScenes
          this.generatingProgress = `大纲就绪，共 ${data.totalScenes} 页，正在生成第 1 页...`
          break

        case 'scene_status': {
          // 更新页级状态
          this.sceneStatuses.push({
            sceneIndex: data.sceneIndex,
            status: data.status,
            title: data.title,
            sceneId: data.sceneId,
          })
          const readyCount = this.sceneStatuses.filter(s => s.status === 'ready').length
          const failedCount = this.sceneStatuses.filter(s => s.status === 'failed').length
          this.generatingProgress = `已完成 ${readyCount + failedCount}/${this.totalScenes} 页`
            + (failedCount > 0 ? `（${failedCount} 页失败）` : '') + '...'

          // 如果页面 ready，从 DB 获取完整数据
          if (data.status === 'ready' && this.currentSession?.id) {
            this._fetchScene(this.currentSession.id, data.sceneIndex)
          }
          break
        }

        case 'complete':
          this.generatingStatus = 'complete'
          this.generatingProgress = '生成完成'
          if (this.currentSession) {
            this.currentSession.status = data.status
          }
          break

        case 'error':
          this.generatingStatus = 'error'
          this.generatingProgress = `生成失败: ${data.message}`
          break
      }
    },

    async _fetchScene(sessionId, sceneOrder) {
      try {
        const scene = await fetchScene(sessionId, sceneOrder)
        // 按 scene_order 插入到正确位置
        const existing = this.scenes.findIndex(s => s.sceneOrder === sceneOrder)
        const mapped = {
          sceneOrder: scene.scene_order,
          title: scene.title,
          slideContent: scene.slide_content,
          actions: scene.actions,
          keyPoints: scene.key_points,
          sceneStatus: scene.scene_status,
          audioStatus: scene.audio_status,
        }
        if (existing >= 0) {
          this.scenes[existing] = mapped
        } else {
          this.scenes.push(mapped)
          this.scenes.sort((a, b) => a.sceneOrder - b.sceneOrder)
        }
      } catch (e) {
        console.error(`Failed to fetch scene ${sceneOrder}:`, e)
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

    // --- 页面重试 ---
    async retryFailedScene(sessionId, sceneOrder) {
      const result = await retryScene(sessionId, sceneOrder)
      if (result.scene_status === 'ready') {
        await this._fetchScene(sessionId, sceneOrder)
        // 更新 sceneStatuses
        const idx = this.sceneStatuses.findIndex(s => s.sceneIndex === sceneOrder)
        if (idx >= 0) this.sceneStatuses[idx].status = 'ready'
      }
      return result.scene_status
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
      const data = await fetchSession(sessionId)
      this.currentSession = data
      this.scenes = (data.scenes || [])
        .filter(s => s.scene_status === 'ready')
        .map(s => ({
          sceneOrder: s.scene_order,
          title: s.title,
          slideContent: s.slide_content,
          actions: s.actions,
          keyPoints: s.key_points,
          sceneStatus: s.scene_status,
          audioStatus: s.audio_status,
        }))
      if (data.playback_snapshot) {
        this.currentSceneIndex = data.playback_snapshot.sceneIndex || 0
        this.currentActionIndex = data.playback_snapshot.actionIndex || 0
      } else {
        this.currentSceneIndex = 0
        this.currentActionIndex = 0
      }
      this.playbackState = 'idle'
      this.clearEffects()
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
      this.totalScenes = 0
      this.sceneStatuses = []
      this.sessions = []
      this.sessionsLoading = false
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/stores/rehearsal.js
git commit -m "feat(rehearsal): add Pinia store with SSE notification + DB fetch pattern"
```

---

## Task 10: 前端 PlaybackEngine

**Files:**
- Create: `teacher-platform/src/composables/usePlaybackEngine.js`

- [ ] **Step 1: 创建 PlaybackEngine composable**

```javascript
// teacher-platform/src/composables/usePlaybackEngine.js
import { ref, watch } from 'vue'
import { useRehearsalStore } from '../stores/rehearsal.js'

/**
 * PlaybackEngine — 状态机: idle → playing → paused
 * 音频优先级: persistent_audio_url > temp_audio_url > 计时播放
 */
export function usePlaybackEngine() {
  const store = useRehearsalStore()
  const audioRef = ref(null)
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

  function _getAudioUrl(action) {
    // 优先级: persistent > temp > null
    return action.persistent_audio_url || action.temp_audio_url || action.audioUrl || null
  }

  async function processNext() {
    if (store.playbackState !== 'playing') return

    const scene = store.scenes[store.currentSceneIndex]
    if (!scene) {
      store.playbackState = 'idle'
      store.clearEffects()
      store.savePlaybackProgress()
      return
    }

    const actions = scene.actions || []
    const actionIndex = store.currentActionIndex

    if (actionIndex >= actions.length) {
      const nextIndex = store.currentSceneIndex + 1
      if (nextIndex >= store.scenes.length) {
        store.playbackState = 'idle'
        store.clearEffects()
        store.savePlaybackProgress()
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
        const audioUrl = _getAudioUrl(action)
        if (audioUrl) {
          audioRef.value = new Audio(audioUrl)
          audioRef.value.onended = () => processNext()
          audioRef.value.onerror = () => _playWithTimer(action.duration || 3000)
          try {
            await audioRef.value.play()
          } catch {
            _playWithTimer(action.duration || 3000)
          }
        } else {
          _playWithTimer(action.duration || 3000)
        }
        break

      case 'spotlight':
        store.spotlightTarget = {
          elementId: action.elementId,
          dimOpacity: action.dimOpacity ?? 0.4,
        }
        store.laserTarget = null
        processNext()
        break

      case 'laser':
        store.laserTarget = {
          elementId: action.elementId,
          color: action.color || '#ff0000',
        }
        store.spotlightTarget = null
        processNext()
        break

      case 'navigate':
        store.setSceneIndex(action.targetSceneIndex)
        processNext()
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
    if (audioRef.value && !audioRef.value.paused) audioRef.value.pause()
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
    if (store.playbackState === 'playing') processNext()
  }

  function prevScene() { jumpToScene(Math.max(0, store.currentSceneIndex - 1)) }
  function nextScene() { jumpToScene(Math.min(store.scenes.length - 1, store.currentSceneIndex + 1)) }

  function cleanup() {
    _clearTimers()
    if (audioRef.value) { audioRef.value.pause(); audioRef.value = null }
  }

  return { start, pause, resume, stop, jumpToScene, prevScene, nextScene, cleanup }
}
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/composables/usePlaybackEngine.js
git commit -m "feat(rehearsal): add PlaybackEngine with audio priority chain"
```

---

## Task 11: 前端幻灯片渲染器 + 遮罩组件

**Files:**
- Create: `teacher-platform/src/components/rehearsal/SlideRenderer.vue`
- Create: `teacher-platform/src/components/rehearsal/SpotlightOverlay.vue`
- Create: `teacher-platform/src/components/rehearsal/LaserPointer.vue`
- Create: `teacher-platform/src/components/rehearsal/SubtitlePanel.vue`
- Create: `teacher-platform/src/components/rehearsal/PlaybackControls.vue`

这些组件代码与之前版本相同（不受架构调整影响），参见原计划 Task 10-11 的完整代码。此处不重复，实现时按原计划的组件代码编写即可。

- [ ] **Step 1: 创建 SlideRenderer.vue** — 同原计划 Task 10 Step 1
- [ ] **Step 2: 创建 SpotlightOverlay.vue** — 同原计划 Task 10 Step 2
- [ ] **Step 3: 创建 LaserPointer.vue** — 同原计划 Task 10 Step 3
- [ ] **Step 4: 创建 SubtitlePanel.vue** — 同原计划 Task 11 Step 1
- [ ] **Step 5: 创建 PlaybackControls.vue** — 同原计划 Task 11 Step 2
- [ ] **Step 6: 提交**

```bash
git add teacher-platform/src/components/rehearsal/
git commit -m "feat(rehearsal): add SlideRenderer, Spotlight, Laser, Subtitle, Controls"
```

---

## Task 12: 前端页面 — RehearsalNew（含生成预览）

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
        <el-input v-model="topic" type="textarea" :rows="3"
          placeholder="例：高中物理 - 牛顿第二定律" :disabled="isGenerating" />
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

      <el-button type="primary" :loading="isGenerating"
        :disabled="!topic.trim() || isGenerating" @click="handleGenerate" style="width:100%">
        {{ isGenerating ? '生成中...' : '开始生成' }}
      </el-button>

      <!-- 生成预览 -->
      <div v-if="store.generatingStatus" class="progress-section">
        <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="8" />
        <p class="progress-text">{{ store.generatingProgress }}</p>

        <!-- 页级状态列表 -->
        <div v-if="store.sceneStatuses.length" class="scene-status-list">
          <div v-for="s in store.sceneStatuses" :key="s.sceneIndex" class="scene-status-item">
            <span class="scene-title">{{ s.sceneIndex + 1 }}. {{ s.title }}</span>
            <el-tag :type="s.status === 'ready' ? 'success' : 'danger'" size="small">
              {{ s.status === 'ready' ? '就绪' : '失败' }}
            </el-tag>
            <el-button v-if="s.status === 'failed'" size="small" text type="primary"
              @click="handleRetry(s.sceneIndex)">
              重试
            </el-button>
          </div>
        </div>

        <el-button v-if="store.scenes.length > 0 && store.currentSession"
          type="success" @click="goToPlay" style="width:100%;margin-top:12px">
          开始播放（{{ store.scenes.length }} 页就绪）
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
  if (!store.totalScenes) return 10
  const done = store.sceneStatuses.length
  return Math.round((done / store.totalScenes) * 90) + 10
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
}

async function handleRetry(sceneOrder) {
  if (!store.currentSession?.id) return
  await store.retryFailedScene(store.currentSession.id, sceneOrder)
}

function goToPlay() {
  if (store.currentSession?.id) {
    router.push(`/rehearsal/play/${store.currentSession.id}`)
  }
}
</script>

<style scoped>
.rehearsal-new { max-width: 560px; margin: 60px auto; padding: 0 20px; }
.new-card { background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
h2 { margin: 0 0 4px; font-size: 22px; }
.desc { color: #8b949e; font-size: 14px; margin: 0 0 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: #57606a; margin-bottom: 6px; }
.form-row { display: flex; gap: 16px; }
.half { flex: 1; }
.progress-section { margin-top: 20px; padding-top: 16px; border-top: 1px solid #eee; }
.progress-text { font-size: 13px; color: #58a6ff; margin: 8px 0 0; }
.scene-status-list { margin-top: 12px; }
.scene-status-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.scene-title { flex: 1; font-size: 13px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalNew.vue
git commit -m "feat(rehearsal): add RehearsalNew with page-level status and retry"
```

---

## Task 13: 前端页面 — RehearsalPlay

**Files:**
- Create: `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`

与原计划 Task 13 代码相同（播放页不受架构调整影响，因为它加载的数据已经来自 DB）。实现时按原计划代码编写。

- [ ] **Step 1: 创建 RehearsalPlay.vue** — 同原计划 Task 13 Step 1
- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalPlay.vue
git commit -m "feat(rehearsal): add RehearsalPlay page"
```

---

## Task 14: 前端页面 — RehearsalHistory

**Files:**
- Create: `teacher-platform/src/views/rehearsal/RehearsalHistory.vue`

与原计划 Task 14 代码基本相同，但状态标签需要包含 partial。实现时按原计划代码编写，确保 `statusLabel` 和 `statusTagType` 包含 partial 映射。

- [ ] **Step 1: 创建 RehearsalHistory.vue** — 同原计划 Task 14 Step 1
- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/views/rehearsal/RehearsalHistory.vue
git commit -m "feat(rehearsal): add RehearsalHistory page"
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

- [ ] **Step 2: 提交**

```bash
git add teacher-platform/src/router/index.js
git commit -m "feat(rehearsal): register rehearsal routes"
```

---

## Task 16: 集成验证

- [ ] **Step 1: 后端启动验证**

```bash
cd backend
alembic upgrade head
python run.py
```

访问 `http://localhost:8000/docs`，确认 rehearsal 接口出现。

- [ ] **Step 2: 前端启动验证**

```bash
cd teacher-platform
npm run dev
```

访问 `/rehearsal/new`、`/rehearsal/history`。

- [ ] **Step 3: 端到端测试**

1. 新建预演：输入主题 → 观察页级状态逐页更新
2. 失败页重试：如有失败页点击"重试"
3. 播放：进入播放页 → Spotlight/Laser/字幕/翻页
4. 历史：返回历史列表 → 会话状态正确
5. 恢复：重新打开播放页 → 进度恢复

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat(rehearsal): classroom rehearsal MVP complete"
```
