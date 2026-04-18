"""
课堂预演媒体生成服务。

- 独立于 PPT 生成模块
- 使用阿里云百炼 Qwen 文生图
- 图片统一持久化到 OSS，返回公网 URL
- 单张图片失败时降级为可渲染的 shape，避免前端继续请求无效 src
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.oss_service import upload_bytes

logger = logging.getLogger(__name__)
settings = get_settings()

QWEN_IMAGE_ENDPOINT = "/api/v1/services/aigc/multimodal-generation/generation"
IMAGE_PLACEHOLDER_SRC = "placeholder"
DEFAULT_IMAGE_SIZE = "1280*720"
DEFAULT_IMAGE_PREFIX = "rehearsal-images"
DOWNLOAD_MAX_BYTES = 20 * 1024 * 1024
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text or "").strip()


def _element_center(element: dict) -> tuple[float, float]:
    left = float(element.get("left") or 0)
    top = float(element.get("top") or 0)
    width = float(element.get("width") or 0)
    height = float(element.get("height") or 0)
    return left + width / 2, top + height / 2


def _collect_slot_text_cues(element: dict, slide_content: dict | None, limit: int = 2) -> list[str]:
    elements = (slide_content or {}).get("elements") or []
    if not isinstance(elements, list):
        return []

    center_x, center_y = _element_center(element)
    width = float(element.get("width") or 0)
    height = float(element.get("height") or 0)
    max_distance = max(width, height, 180.0) * 1.5
    cues: list[tuple[float, str]] = []

    for candidate in elements:
        if not isinstance(candidate, dict) or candidate.get("type") != "text":
            continue
        text = _strip_html(str(candidate.get("content") or ""))
        if not text:
            continue
        text_center_x, text_center_y = _element_center(candidate)
        distance = ((center_x - text_center_x) ** 2 + (center_y - text_center_y) ** 2) ** 0.5
        if distance > max_distance:
            continue
        cues.append((distance, text))

    cues.sort(key=lambda item: item[0])

    selected: list[str] = []
    for _, text in cues:
        if text in selected:
            continue
        selected.append(text)
        if len(selected) >= limit:
            break
    return selected


def _image_slot_position(element: dict, slide_content: dict | None) -> tuple[int, int]:
    image_elements = [
        item
        for item in ((slide_content or {}).get("elements") or [])
        if isinstance(item, dict) and item.get("type") == "image"
    ]
    for index, image_element in enumerate(image_elements, start=1):
        if image_element is element or image_element.get("id") == element.get("id"):
            return index, len(image_elements)
    return 1, max(len(image_elements), 1)


def build_rehearsal_image_prompt(outline: dict, element: dict, slide_content: dict | None = None) -> str:
    title = str(outline.get("title") or "").strip()
    description = str(outline.get("description") or "").strip()
    key_points = [
        str(point).strip()
        for point in (outline.get("keyPoints") or [])
        if str(point).strip()
    ]
    width = int(element.get("width") or 0)
    height = int(element.get("height") or 0)
    slot_index, slot_total = _image_slot_position(element, slide_content)
    slot_cues = _collect_slot_text_cues(element, slide_content)

    prompt_lines = [
        "Create a clean educational slide illustration.",
        f"Topic: {title or 'Classroom lesson'}",
        f"Image slot: {slot_index} of {slot_total}.",
    ]
    if slot_cues:
        prompt_lines.append("Primary subject for this image slot:")
        prompt_lines.extend(f"- {cue}" for cue in slot_cues)
        prompt_lines.extend(
            [
                "Generate only the single subject or tightly related mini-scene described by the slot-specific cues above.",
                "Do not include subjects from other image slots on the same slide.",
            ]
        )
    else:
        if description:
            prompt_lines.append(f"Teaching focus: {description}")
        if key_points:
            prompt_lines.append("Key points:")
            prompt_lines.extend(f"- {point}" for point in key_points[:4])

    prompt_lines.extend(
        [
            "Style requirements:",
            "- professional classroom presentation visual",
            "- clear subject focus and realistic composition",
            "- no watermark, no collage, no UI, no borders",
            "- avoid embedded text, labels, captions, and formulas in the image",
            "- suitable for a modern lecture slide",
        ]
    )

    if width > 0 and height > 0:
        prompt_lines.append(
            f"Target image region aspect hint: approximately {width}:{height} inside a 16:9 slide."
        )

    element_count = len((slide_content or {}).get("elements") or [])
    if element_count:
        prompt_lines.append(f"Slide context: this image is one visual element within a slide of {element_count} total elements.")

    return "\n".join(prompt_lines)


def _extract_image_url(payload: dict) -> str:
    choices = payload.get("output", {}).get("choices") or []
    if not choices:
        code = payload.get("code")
        message = payload.get("message")
        if code or message:
            raise RuntimeError(f"Qwen image error: {code} - {message}")
        raise RuntimeError("Qwen image returned empty response")

    content = choices[0].get("message", {}).get("content") or []
    for item in content:
        image_url = item.get("image")
        if image_url:
            return str(image_url)
    raise RuntimeError("Qwen image response missing image URL")


def _guess_extension(url: str, content_type: str | None) -> str:
    content_type = (content_type or "").split(";")[0].strip().lower()
    type_to_ext = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    if content_type in type_to_ext:
        return type_to_ext[content_type]

    suffix = Path(httpx.URL(url).path).suffix.lower().lstrip(".")
    if suffix in {"png", "jpg", "jpeg", "webp", "gif"}:
        return "jpg" if suffix == "jpeg" else suffix
    return "png"


def _degrade_image_element(element: dict) -> dict:
    degraded = {
        "id": element.get("id"),
        "type": "shape",
        "shape": "roundRect",
        "left": element.get("left", 0),
        "top": element.get("top", 0),
        "width": element.get("width", 320),
        "height": element.get("height", 180),
        "fill": "#E5E7EB",
    }
    return degraded


async def generate_qwen_image(*, prompt: str, size: str) -> str:
    if not settings.DASHSCOPE_API_KEY:
        raise RuntimeError("DASHSCOPE_API_KEY not configured for rehearsal image generation")

    base_url = str(settings.REHEARSAL_IMAGE_BASE_URL or "https://dashscope.aliyuncs.com").rstrip("/")
    payload = {
        "model": settings.REHEARSAL_IMAGE_MODEL or "z-image-turbo",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ]
        },
        "parameters": {
            "size": size,
            "watermark": False,
            "prompt_extend": True,
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(settings.REHEARSAL_IMAGE_TIMEOUT_SECONDS, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{base_url}{QWEN_IMAGE_ENDPOINT}", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return _extract_image_url(data)


async def download_generated_media(url: str) -> tuple[bytes, str]:
    timeout = httpx.Timeout(settings.REHEARSAL_IMAGE_TIMEOUT_SECONDS, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content
        if len(content) > DOWNLOAD_MAX_BYTES:
            raise RuntimeError(f"Generated image too large: {len(content)} bytes")
        ext = _guess_extension(url, response.headers.get("content-type"))
        return content, ext


async def upload_generated_media(content: bytes, ext: str, user_id: int, prefix: str) -> str:
    return await upload_bytes(content, ext, user_id, prefix)


async def populate_slide_media(
    slide_content: dict | None,
    outline: dict,
    *,
    user_id: int,
    session_id: int,
    scene_id: int,
) -> dict | None:
    if not slide_content or not isinstance(slide_content, dict):
        return slide_content

    updated_slide = deepcopy(slide_content)
    elements = updated_slide.get("elements")
    if not isinstance(elements, list):
        return updated_slide

    image_size = str(settings.REHEARSAL_IMAGE_SIZE or DEFAULT_IMAGE_SIZE).strip() or DEFAULT_IMAGE_SIZE

    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            continue
        if element.get("type") != "image":
            continue

        src = str(element.get("src") or "").strip()
        if src and src != IMAGE_PLACEHOLDER_SRC:
            continue

        try:
            prompt = build_rehearsal_image_prompt(outline, element, updated_slide)
            remote_url = await generate_qwen_image(prompt=prompt, size=image_size)
            content, ext = await download_generated_media(remote_url)
            oss_url = await upload_generated_media(content, ext, user_id, DEFAULT_IMAGE_PREFIX)
            element["src"] = oss_url
            logger.info(
                "Rehearsal image generated session_id=%s scene_id=%s element_id=%s url=%s",
                session_id,
                scene_id,
                element.get("id"),
                oss_url,
            )
        except Exception as exc:
            logger.warning(
                "Rehearsal image generation failed session_id=%s scene_id=%s element_id=%s: %s",
                session_id,
                scene_id,
                element.get("id"),
                exc,
            )
            elements[index] = _degrade_image_element(element)

    return updated_slide
