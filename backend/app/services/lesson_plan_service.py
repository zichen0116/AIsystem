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

只有在上述关键信息都已明确时，才按照以下 Markdown 结构生成完整教案。

**格式要求（严格遵守）：**
- 必须直接以 # 开头输出教案，不要添加任何前言、客套话或解释性文字
- 第一个字符必须是 #，不要有"好的，我来为您生成教案"等开场白
- 只输出教案 Markdown 内容，不要输出其他格式

教案结构：

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
    import re
    try:
        async with AsyncSessionLocal() as db:
            try:
                now = datetime.now(timezone.utc)

                # Extract lesson plan content intelligently
                lesson_plan_content = None

                # Try to find the first line starting with # (Markdown heading)
                lines = content.split("\n")
                first_heading_idx = None
                for i, line in enumerate(lines):
                    if line.strip().startswith("#"):
                        first_heading_idx = i
                        break

                # If found a heading, extract from that point onwards
                if first_heading_idx is not None:
                    lesson_plan_content = "\n".join(lines[first_heading_idx:]).strip()

                # Update lesson plan - write content if we extracted a lesson plan
                if lesson_plan_content:
                    title = lesson_plan_content.split("\n")[0].lstrip("# ").split("—")[0].strip() or "未命名教案"
                    await db.execute(
                        update(LessonPlan)
                        .where(LessonPlan.id == plan_id)
                        .values(content=lesson_plan_content, title=title, status="completed", updated_at=now)
                    )
                else:
                    # No lesson plan structure found, keep as draft
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
