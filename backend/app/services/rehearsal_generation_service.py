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
import re
from copy import deepcopy
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.rehearsal import RehearsalSession, RehearsalScene
from app.services.lesson_plan_service import stream_llm
from app.services.rehearsal_media_service import populate_slide_media
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
3. highlight: 高亮元素 { "type": "highlight", "elementIds": ["el_1"], "color": "#ff6b6b", "opacity": 0.22, "borderWidth": 3 }
4. laser: 激光指向 { "type": "laser", "elementId": "el_1", "color": "#ff0000", "duration": 1600 }

设计规范：
- 每页 4-8 个动作
- 通常先 spotlight / highlight 某元素，然后 speech 讲解该元素
- speech 文本要自然、口语化，像真正在课堂上讲课
- 第一页要有开场白（例如“同学们好，今天我们来学习……”）
- 中间页禁止再次问候、禁止重新自我介绍，应自然承接上一页
- 最后一页要有收尾语
- 所有页面属于同一节课，不要出现“上节课”“上一节”等跨课表达
- 优先聚焦正文重点、图示、公式，不要聚焦纯装饰元素
- 所有 elementId 必须引用幻灯片中已有的元素 id
- 不要生成 navigate 动作（翻页由系统自动处理）

输出严格 JSON 数组格式，不要输出其他内容：
[
  { "type": "spotlight", "elementId": "el_1", "dimOpacity": 0.4 },
  { "type": "speech", "text": "这里讲解..." },
  { "type": "laser", "elementId": "el_2", "color": "#ff3b30", "duration": 1600 }
]"""

OPENING_GREETING_RE = re.compile(
    r"^\s*(同学们好|大家好|同学们，大家好|欢迎大家|hello everyone|hi everyone|good (morning|afternoon|evening)( everyone)?)"
    r"[，,。.!！:：\s]*",
    re.IGNORECASE,
)

OPENING_TODAY_RE = re.compile(r"^\s*今天(我们|咱们)来学习[，,：:。\s]*")
HTML_TAG_RE = re.compile(r"<[^>]+>")
VISUAL_ACTION_TYPES = {"spotlight", "highlight", "laser"}


def _build_course_context_for_actions(all_outlines: list[dict], scene_order: int, total: int) -> str:
    """Build course outline + page position context (OpenMAIC-style)."""
    if not all_outlines:
        return ""

    lines: list[str] = ["Course Outline:"]
    for idx, item in enumerate(all_outlines):
        title = item.get("title", f"Page {idx + 1}")
        marker = " <- current" if idx == scene_order else ""
        lines.append(f"{idx + 1}. {title}{marker}")

    lines.append("")
    lines.append(
        "IMPORTANT: All pages are in the same class session. Do NOT greet again after page 1. "
        "When referencing earlier content, say we just covered it; never say last class.",
    )

    if scene_order == 0:
        lines.append("Position: FIRST page. Greeting/opening is allowed.")
    elif scene_order == total - 1:
        lines.append(f"Position: LAST page ({scene_order + 1}/{total}). Summarize and close; do NOT greet again.")
    else:
        lines.append(f"Position: MIDDLE page ({scene_order + 1}/{total}). Continue naturally; do NOT greet again.")

    return "\n".join(lines)


def normalize_actions_for_page_position(actions: list | None, scene_order: int, title: str) -> list:
    """Strip duplicated opening greeting on non-first pages."""
    updated_actions = deepcopy(actions or [])
    if scene_order == 0:
        return updated_actions

    for action in updated_actions:
        if action.get("type") != "speech" or not action.get("text"):
            continue
        original = str(action["text"]).strip()
        cleaned = OPENING_GREETING_RE.sub("", original).strip()
        cleaned = OPENING_TODAY_RE.sub("", cleaned).strip()
        if cleaned != original:
            action["text"] = cleaned or f"接下来我们继续学习《{title}》。"
        break

    return updated_actions


def _strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text or "").strip()


def format_elements_for_actions_prompt(elements: list | None) -> str:
    lines: list[str] = []
    for el in elements or []:
        element_id = str(el.get("id") or "").strip()
        if not element_id:
            continue

        element_type = str(el.get("type") or "unknown")
        summary = f"type={element_type}"
        if element_type == "text":
            text_summary = _strip_html(str(el.get("content") or ""))[:60]
            if text_summary:
                summary = f'{summary}, text="{text_summary}"'
        elif element_type == "image":
            summary = f"{summary}, image element"
        elif element_type == "shape":
            summary = f'{summary}, shape={el.get("shape") or "rect"}'

        top = el.get("top")
        left = el.get("left")
        if isinstance(left, (int, float)) and isinstance(top, (int, float)):
            summary = f"{summary}, position=({int(left)}, {int(top)})"

        lines.append(f"- id={element_id}, {summary}")

    return "\n".join(lines) if lines else "- (no elements)"


def _pick_default_focus_element_id(elements: list | None) -> str | None:
    focusable = [el for el in (elements or []) if el.get("id")]
    if not focusable:
        return None

    body_text = [
        el for el in focusable
        if el.get("type") == "text" and isinstance(el.get("top"), (int, float)) and el.get("top", 0) >= 90
    ]
    if body_text:
        return body_text[0]["id"]

    media_like = [el for el in focusable if el.get("type") in ("image", "shape")]
    if media_like:
        return media_like[0]["id"]

    text_like = [el for el in focusable if el.get("type") == "text"]
    if text_like:
        return text_like[0]["id"]

    return focusable[0]["id"]


def _build_default_slide_actions(outline: dict, slide_content: dict) -> list[dict]:
    actions: list[dict] = []
    focus_element_id = _pick_default_focus_element_id(slide_content.get("elements"))
    if focus_element_id:
        actions.append({
            "type": "spotlight",
            "elementId": focus_element_id,
            "dimOpacity": 0.45,
        })

    speech_text = outline.get("description") or "。".join(outline.get("keyPoints", [])[:3]) or outline["title"]
    actions.append({"type": "speech", "text": speech_text})
    return actions


def finalize_actions_for_slide(actions: list | None, outline: dict, slide_content: dict, scene_order: int) -> list:
    valid_ids = {str(el.get("id")) for el in slide_content.get("elements", []) if el.get("id")}
    preferred_id = _pick_default_focus_element_id(slide_content.get("elements"))
    finalized: list[dict] = []

    for raw_action in actions or []:
        if not isinstance(raw_action, dict):
            continue

        action_type = str(raw_action.get("type") or "").strip()
        if action_type == "speech":
            text = str(raw_action.get("text") or "").strip()
            if text:
                finalized.append({"type": "speech", "text": text})
            continue

        if action_type == "spotlight":
            element_id = raw_action.get("elementId")
            if element_id not in valid_ids:
                element_id = preferred_id
            if element_id:
                finalized.append({
                    "type": "spotlight",
                    "elementId": element_id,
                    "dimOpacity": raw_action.get("dimOpacity", 0.4),
                })
            continue

        if action_type == "highlight":
            element_ids = raw_action.get("elementIds")
            if not isinstance(element_ids, list):
                single_id = raw_action.get("elementId")
                element_ids = [single_id] if single_id else []
            element_ids = [element_id for element_id in element_ids if element_id in valid_ids]
            if not element_ids and preferred_id:
                element_ids = [preferred_id]
            if element_ids:
                finalized.append({
                    "type": "highlight",
                    "elementIds": element_ids,
                    "color": raw_action.get("color", "#ff6b6b"),
                    "opacity": raw_action.get("opacity", 0.22),
                    "borderWidth": raw_action.get("borderWidth", 3),
                })
            continue

        if action_type == "laser":
            element_id = raw_action.get("elementId")
            if element_id not in valid_ids:
                element_id = preferred_id
            if element_id:
                finalized.append({
                    "type": "laser",
                    "elementId": element_id,
                    "color": raw_action.get("color", "#ff3b30"),
                    "duration": raw_action.get("duration", 1600),
                })

    finalized = normalize_actions_for_page_position(finalized, scene_order, outline["title"])

    if not any(action.get("type") in VISUAL_ACTION_TYPES for action in finalized):
        focus_element_id = preferred_id
        if focus_element_id:
            finalized.insert(0, {
                "type": "spotlight",
                "elementId": focus_element_id,
                "dimOpacity": 0.45,
            })

    if not any(action.get("type") == "speech" and action.get("text") for action in finalized):
        finalized.append({
            "type": "speech",
            "text": outline.get("description") or outline["title"],
        })

    return finalized
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

            slide_content = await populate_slide_media(
                slide_content,
                outline,
                user_id=user_id,
                session_id=session_id,
                scene_id=scene_id,
            )

            # 2. 生成 actions
            element_ids = [el.get("id", "") for el in slide_content.get("elements", [])]
            element_summaries = format_elements_for_actions_prompt(slide_content.get("elements", []))
            outlines_for_context: list[dict] = []
            try:
                parsed_outlines = json.loads(all_outlines_text) if all_outlines_text else []
                if isinstance(parsed_outlines, list):
                    outlines_for_context = parsed_outlines
            except Exception:
                outlines_for_context = []

            course_context = _build_course_context_for_actions(
                outlines_for_context,
                scene_order=scene_order,
                total=total,
            )
            actions_prompt = (
                f"幻灯片标题：{outline['title']}\n"
                f"要点：{json.dumps(outline.get('keyPoints', []), ensure_ascii=False)}\n"
                f"幻灯片元素 ID 列表：{json.dumps(element_ids)}\n"
                f"幻灯片元素摘要：\n{element_summaries}\n"
                f"这是第 {scene_order + 1}/{total} 页\n"
                f"{course_context}"
            )
            actions = await _call_llm_json(ACTIONS_SYSTEM_PROMPT, actions_prompt)
            if not actions or not isinstance(actions, list):
                actions = _build_default_slide_actions(outline, slide_content)

            actions = finalize_actions_for_slide(actions, outline, slide_content, scene_order)

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

            updated_actions = deepcopy(scene.actions or [])
            total_speech = 0
            success_count = 0

            for action_index, action in enumerate(updated_actions):
                if action.get("type") != "speech" or not action.get("text"):
                    continue
                total_speech += 1
                tts_result = await synthesize(action["text"], voice, speed, user_id)
                action["temp_audio_url"] = tts_result["temp_audio_url"]
                action["persistent_audio_url"] = tts_result["persistent_audio_url"]
                action["audio_status"] = tts_result["audio_status"]
                logger.info(
                    "TTS result prepared for scene_id=%s action_index=%s audio_status=%s "
                    "temp_audio_url=%s persistent_audio_url=%s",
                    scene_id,
                    action_index,
                    tts_result["audio_status"],
                    tts_result["temp_audio_url"],
                    tts_result["persistent_audio_url"],
                )
                if tts_result["audio_status"] in ("temp_ready", "ready"):
                    success_count += 1

            scene.actions = updated_actions
            flag_modified(scene, "actions")
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
            logger.info(
                "TTS fill completed for scene %s: audio_status=%s successful=%s total_speech=%s",
                scene_id,
                scene.audio_status,
                success_count,
                total_speech,
            )

        except Exception as e:
            logger.error(f"TTS fill failed for scene {scene_id}: {e}")


def merge_tts_results_into_actions(actions: list | None, tts_results: list[dict]) -> list:
    """Return a persisted-safe action list with TTS fields merged into speech actions."""
    updated_actions = deepcopy(actions or [])
    speech_index = 0

    for action in updated_actions:
        if action.get("type") != "speech" or not action.get("text"):
            continue
        if speech_index >= len(tts_results):
            break
        tts_result = tts_results[speech_index]
        speech_index += 1
        action["temp_audio_url"] = tts_result["temp_audio_url"]
        action["persistent_audio_url"] = tts_result["persistent_audio_url"]
        action["audio_status"] = tts_result["audio_status"]

    return updated_actions


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
                result = await db2.execute(
                    select(RehearsalSession)
                    .options(selectinload(RehearsalSession.scenes))
                    .where(RehearsalSession.id == session_id)
                )
                final_session = result.scalar_one()
                final_session.status = compute_session_status(final_session)
                await db2.commit()

                yield _sse_event("complete", {
                    "sessionId": session_id,
                    "status": final_session.status,
                })

        except Exception as e:
            logger.error(f"Generation pipeline failed: {e}")
            try:
                async with AsyncSessionLocal() as err_db:
                    s = await err_db.get(RehearsalSession, session_id)
                    if s:
                        s.status = "failed"
                        s.error_message = str(e)[:500]
                        await err_db.commit()
            except Exception:
                pass
            yield _sse_event("error", {"message": str(e)})


# ---------- 单页重试 ----------

async def retry_scene(session_id: int, scene_order: int, user_id: int) -> str:
    """重试单页生成。返回新的 scene_status。"""
    async with AsyncSessionLocal() as db:
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
