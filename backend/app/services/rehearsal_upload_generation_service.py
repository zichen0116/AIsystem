import logging
import re

from app.models.rehearsal import RehearsalScene, RehearsalSession
from app.services.lesson_plan_service import stream_llm
from app.services.tts_service import estimate_duration_ms, synthesize

logger = logging.getLogger(__name__)

_MARKDOWN_SYNTAX_RE = re.compile(r"(^|\s)([#>*`-]+)")
_WHITESPACE_RE = re.compile(r"\s+")

SCRIPT_SYSTEM_PROMPT = """You are an experienced classroom teacher.
Write a short spoken explanation for one uploaded slide/page.

Rules:
- Stay grounded in the provided page text.
- Keep the tone like a live teacher explanation.
- Do not invent major facts that are not supported by the page.
- If the page text is incomplete, still produce a concise usable explanation.
- Return plain text only.
"""


def _normalize_text(value: str | None) -> str:
    text = (value or "").strip()
    text = _MARKDOWN_SYNTAX_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _build_fallback_script(scene: RehearsalScene) -> str:
    page_number = scene.original_page_number or scene.scene_order + 1
    cleaned_text = _normalize_text(scene.page_text)
    if cleaned_text:
        excerpt = cleaned_text[:180]
        suffix = "..." if len(cleaned_text) > 180 else ""
        return f"Now we are on page {page_number}. The main point here is: {excerpt}{suffix}"
    return (
        f"Now we are on page {page_number}, titled {scene.title}. "
        "Please explain the visible page content and summarize the core takeaway."
    )


async def _call_llm_text(system_prompt: str, user_prompt: str) -> str | None:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    parts: list[str] = []
    async for chunk in stream_llm(messages):
        if chunk:
            parts.append(chunk)
    text = "".join(parts).strip()
    return text or None


def _append_error(scene: RehearsalScene, message: str) -> None:
    current = (scene.error_message or "").strip()
    if not current:
        scene.error_message = message
        return
    if message in current:
        return
    scene.error_message = f"{current}; {message}"


async def _generate_script_text(session: RehearsalSession, scene: RehearsalScene) -> tuple[str, bool]:
    cleaned_text = _normalize_text(scene.page_text)
    if not cleaned_text:
        return _build_fallback_script(scene), True

    page_number = scene.original_page_number or scene.scene_order + 1
    user_prompt = (
        f"Session title: {session.title}\n"
        f"Language: {session.language}\n"
        f"Page title: {scene.title}\n"
        f"Page number: {page_number}\n"
        f"Page text:\n{cleaned_text[:4000]}\n\n"
        "Write one concise teacher-style narration for this page."
    )

    script_text = await _call_llm_text(SCRIPT_SYSTEM_PROMPT, user_prompt)
    if not script_text:
        return _build_fallback_script(scene), True
    return _normalize_text(script_text), False


async def _populate_audio(scene: RehearsalScene, script_text: str, voice: str, speed: float, user_id: int) -> dict:
    duration = estimate_duration_ms(script_text, speed)
    action = {
        "type": "speech",
        "text": script_text,
        "duration": duration,
        "audio_status": "pending",
    }

    tts_result = await synthesize(
        script_text,
        voice=voice,
        speed=speed,
        user_id=user_id,
        persist=True,
    )
    action["audio_status"] = tts_result["audio_status"]
    if tts_result["temp_audio_url"]:
        action["temp_audio_url"] = tts_result["temp_audio_url"]
    if tts_result["persistent_audio_url"]:
        action["persistent_audio_url"] = tts_result["persistent_audio_url"]

    scene.audio_url = tts_result["persistent_audio_url"] or tts_result["temp_audio_url"]
    scene.audio_status = tts_result["audio_status"]
    return action


async def generate_upload_session_narration(db, session: RehearsalSession) -> dict:
    settings = session.settings or {}
    enable_tts = settings.get("enableTTS", False)
    voice = settings.get("voice", "Cherry")
    speed = float(settings.get("speed", 1.0) or 1.0)

    generated_count = 0
    degraded_count = 0

    for scene in session.scenes or []:
        if scene.scene_status not in {"ready", "fallback"}:
            continue
        if scene.is_skipped:
            continue

        try:
            if settings:
                script_text, used_fallback = await _generate_script_text(session, scene)
            else:
                script_text, used_fallback = _build_fallback_script(scene), True

            scene.script_text = script_text
            if used_fallback and scene.scene_status == "ready":
                scene.scene_status = "fallback"
                degraded_count += 1

            if enable_tts:
                action = await _populate_audio(scene, script_text, voice, speed, session.user_id)
            else:
                scene.audio_url = None
                scene.audio_status = "failed"
                action = {
                    "type": "speech",
                    "text": script_text,
                    "duration": estimate_duration_ms(script_text, speed),
                    "audio_status": "failed",
                }

            scene.actions = [action]
            generated_count += 1
        except Exception as exc:
            logger.exception("Upload narration generation failed: scene_id=%s", scene.id)
            script_text = _build_fallback_script(scene)
            scene.script_text = script_text
            scene.actions = [
                {
                    "type": "speech",
                    "text": script_text,
                    "duration": estimate_duration_ms(script_text, speed),
                    "audio_status": "failed",
                }
            ]
            scene.audio_url = None
            scene.audio_status = "failed"
            if scene.page_image_url and scene.scene_status == "ready":
                scene.scene_status = "fallback"
                degraded_count += 1
            _append_error(scene, f"script generation failed: {exc}")
            generated_count += 1

        if hasattr(db, "add"):
            db.add(scene)

    if hasattr(db, "flush"):
        await db.flush()
    return {
        "generated_scene_count": generated_count,
        "degraded_scene_count": degraded_count,
    }
