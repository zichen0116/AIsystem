import json
import re
from typing import Any


DEFAULT_EXTRA_FIELDS = [
    {"key": "visual_element", "label": "视觉元素", "active": True, "image_prompt": True},
    {"key": "visual_focus", "label": "视觉焦点", "active": True, "image_prompt": True},
    {"key": "layout", "label": "排版布局", "active": True, "image_prompt": True},
    {"key": "notes", "label": "演讲者备注", "active": True, "image_prompt": False},
]

_BASE_SECTION_LABELS = {
    "页面主题内容",
    "页面标题",
    "页面文字",
    "讲稿",
    "图片素材",
    "演讲者备注",
}

_SECTION_PATTERN = re.compile(r"^(?:[-*•]\s*)?([^:\n：]+)[:：]\s*(.*)$")
_HEADING_PATTERN = re.compile(r"^#{1,6}\s*(.+?)\s*$")


def extract_page_points(page: Any) -> list[str]:
    """Read outline points from config first, then fallback to legacy JSON in description."""
    config = getattr(page, "config", None) or {}
    config_points = config.get("points")
    if isinstance(config_points, list):
        return [str(item).strip() for item in config_points if str(item).strip()]

    description = getattr(page, "description", None)
    if not description or not isinstance(description, str):
        return []

    try:
        parsed = json.loads(description)
    except (json.JSONDecodeError, TypeError, ValueError):
        return []

    if not isinstance(parsed, list):
        return []

    return [str(item).strip() for item in parsed if str(item).strip()]


def get_active_extra_fields_config(settings: dict | None) -> list[dict]:
    """Return normalized active extra field configs from project settings."""
    settings = settings or {}
    saved_fields = settings.get("extra_fields_config")
    if isinstance(saved_fields, list) and saved_fields:
        normalized_fields = []
        for item in saved_fields:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            label = str(item.get("label") or "").strip()
            if not key or not label or not item.get("active", True):
                continue
            normalized_fields.append(
                {
                    "key": key,
                    "label": label,
                    "active": True,
                    "image_prompt": bool(item.get("image_prompt", True)),
                }
            )
        if normalized_fields:
            return normalized_fields

    legacy_keys = settings.get("description_extra_fields")
    if isinstance(legacy_keys, list) and legacy_keys:
        default_by_key = {field["key"]: field for field in DEFAULT_EXTRA_FIELDS}
        normalized_fields = []
        for key in legacy_keys:
            key = str(key or "").strip()
            if not key:
                continue
            field = default_by_key.get(key, {"key": key, "label": key, "image_prompt": True})
            normalized_fields.append(
                {
                    "key": field["key"],
                    "label": field["label"],
                    "active": True,
                    "image_prompt": bool(field.get("image_prompt", True)),
                }
            )
        if normalized_fields:
            return normalized_fields

    return [field.copy() for field in DEFAULT_EXTRA_FIELDS if field.get("active", True)]


def split_generated_description(text: str, extra_fields_config: list[dict] | None) -> dict:
    """
    Split generated description text into main description, notes, and extra fields.
    Falls back to preserving the full text as description if parsing is inconclusive.
    """
    raw_text = (text or "").strip()
    if not raw_text:
        return {"description": "", "notes": "", "extra_fields": {}}

    extra_fields_config = extra_fields_config or []
    label_to_key = {}
    for field in extra_fields_config:
        if not isinstance(field, dict):
            continue
        label = _normalize_label(field.get("label"))
        key = str(field.get("key") or "").strip()
        if label and key:
            label_to_key[label] = key

    base_labels = {"页面主题内容", "页面标题", "页面文字", "讲稿"}
    normalized_base_labels = {_normalize_label(label) for label in base_labels}
    sections: dict[str, list[str]] = {}
    current_label: str | None = None

    for raw_line in raw_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            if current_label and sections.get(current_label):
                sections[current_label].append("")
            continue

        match = _SECTION_PATTERN.match(stripped)
        if match:
            label = _normalize_label(match.group(1))
            value = match.group(2).strip()
            if label in normalized_base_labels or label in label_to_key:
                current_label = label
                sections.setdefault(label, [])
                if value:
                    sections[label].append(value)
                continue

        heading_match = _HEADING_PATTERN.match(stripped)
        if heading_match:
            label = _normalize_label(heading_match.group(1))
            if label in normalized_base_labels or label in label_to_key:
                current_label = label
                sections.setdefault(label, [])
                continue

        if current_label:
            sections.setdefault(current_label, []).append(stripped)

    has_base_section = any(label in sections for label in normalized_base_labels)
    if not has_base_section:
        return {"description": raw_text, "notes": "", "extra_fields": {}}

    description = _build_main_description(sections)

    extra_fields: dict[str, str] = {}
    notes = ""
    for label, key in label_to_key.items():
        values = _normalize_section_values(sections.get(label, []))
        if not values:
            continue
        value = "\n".join(values).strip()
        if key == "notes":
            notes = value
        else:
            extra_fields[key] = value

    return {
        "description": description,
        "notes": notes,
        "extra_fields": extra_fields,
    }


def build_page_image_prompt(
    page: Any,
    extra_fields_config: list[dict] | None = None,
    project_settings: dict | None = None,
) -> str:
    explicit_prompt = str(getattr(page, "image_prompt", "") or "").strip()
    if explicit_prompt:
        content = explicit_prompt
    else:
        content = _build_image_prompt_content(page, extra_fields_config)

    if not content:
        content = str(getattr(page, "title", "") or "").strip() or "Professional PPT slide"

    template_guidance = _build_template_guidance(project_settings)
    prompt_parts = [
        "你是一位专业的PPT视觉设计师。请根据以下页面内容生成一张适合幻灯片的整页视觉设计。",
        "请只输出图片，不要返回说明文字、讲稿、备注、Markdown 或代码块。",
    ]
    if template_guidance:
        prompt_parts.append(template_guidance)
    prompt_parts.append(content)
    return "\n\n".join(part for part in prompt_parts if part).strip()


def _build_template_guidance(project_settings: dict | None) -> str:
    settings = project_settings or {}
    template_image_url = str(settings.get("template_image_url") or "").strip()
    template_oss_key = str(settings.get("template_oss_key") or "").strip()
    template_style = str(settings.get("template_style") or "").strip()
    aspect_ratio = str(settings.get("aspect_ratio") or "").strip()

    has_template = bool(template_image_url or template_oss_key)
    guidance_lines: list[str] = []

    if has_template:
        guidance_lines.extend(
            [
                "如果提供了模板参考图，请严格参考模板图的配色、版式、设计语言与整体氛围。",
                "只参考模板风格，不要直接复用模板图中的文字、Logo、页码或水印。",
                "优先保持模板的视觉层次、留白关系和核心构图，再根据当前页面内容完成信息替换。",
            ]
        )
    elif template_style:
        guidance_lines.append("如果没有模板参考图，请严格按照补充风格要求完成整页视觉设计。")

    if template_style:
        if has_template:
            guidance_lines.append(f"补充风格要求：{template_style}")
        else:
            guidance_lines.append(f"风格要求：{template_style}")

    if aspect_ratio:
        guidance_lines.append(f"页面比例：{aspect_ratio}")

    return "\n".join(guidance_lines).strip()


def _build_image_prompt_content(page: Any, extra_fields_config: list[dict] | None = None) -> str:
    title = str(getattr(page, "title", "") or "").strip()
    description = str(getattr(page, "description", "") or "").strip()
    sanitized_description = _sanitize_description_for_image_prompt(description, extra_fields_config)

    parts: list[str] = []
    if sanitized_description:
        if title and title not in sanitized_description:
            parts.append(f"页面标题：{title}")
        parts.append(sanitized_description)
    elif title:
        parts.append(f"页面标题：{title}")

    parts.extend(_collect_image_prompt_extra_fields(page, extra_fields_config))
    return "\n".join(part for part in parts if part).strip()


def _sanitize_description_for_image_prompt(
    description: str,
    extra_fields_config: list[dict] | None = None,
) -> str:
    cleaned = _remove_markdown_images(description).strip()
    if not cleaned:
        return ""

    sections = _parse_structured_sections(cleaned, extra_fields_config)
    if not sections:
        return cleaned

    content_values = _normalize_section_values(sections.get(_normalize_label("页面主题内容"), []))
    if content_values:
        return "\n".join(content_values).strip()

    title_values = _normalize_section_values(sections.get(_normalize_label("页面标题"), []))
    text_values = _normalize_section_values(sections.get(_normalize_label("页面文字"), []))

    prompt_parts: list[str] = []
    if title_values:
        prompt_parts.append(f"页面标题：{title_values[0]}")
        prompt_parts.extend(title_values[1:])
    if text_values:
        prompt_parts.append("页面文字：")
        prompt_parts.extend(text_values)
    return "\n".join(prompt_parts).strip()


def _collect_image_prompt_extra_fields(
    page: Any,
    extra_fields_config: list[dict] | None = None,
) -> list[str]:
    config = getattr(page, "config", None) or {}
    stored_extra_fields = config.get("extra_fields")
    if not isinstance(stored_extra_fields, dict) or not stored_extra_fields:
        return []

    field_defs = extra_fields_config or [field.copy() for field in DEFAULT_EXTRA_FIELDS]
    lines: list[str] = []
    known_keys: set[str] = set()

    for field in field_defs:
        key = str(field.get("key") or "").strip()
        if not key:
            continue
        known_keys.add(key)
        if not field.get("image_prompt", True):
            continue
        value = str(stored_extra_fields.get(key) or "").strip()
        if not value:
            continue
        label = str(field.get("label") or key).strip() or key
        lines.append(f"{label}：{value}")

    for key, raw_value in stored_extra_fields.items():
        normalized_key = str(key or "").strip()
        if not normalized_key or normalized_key in known_keys:
            continue
        value = str(raw_value or "").strip()
        if value:
            lines.append(f"{normalized_key}：{value}")

    return lines


def _parse_structured_sections(
    text: str,
    extra_fields_config: list[dict] | None = None,
) -> dict[str, list[str]]:
    extra_fields_config = extra_fields_config or []
    recognized_labels = {_normalize_label(label) for label in _BASE_SECTION_LABELS}
    for field in extra_fields_config:
        label = _normalize_label(field.get("label"))
        if label:
            recognized_labels.add(label)

    sections: dict[str, list[str]] = {}
    current_label: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            if current_label and sections.get(current_label):
                sections[current_label].append("")
            continue

        match = _SECTION_PATTERN.match(stripped)
        if match:
            label = _normalize_label(match.group(1))
            value = match.group(2).strip()
            if label in recognized_labels:
                current_label = label
                sections.setdefault(label, [])
                if value:
                    sections[label].append(value)
                continue

        heading_match = _HEADING_PATTERN.match(stripped)
        if heading_match:
            label = _normalize_label(heading_match.group(1))
            if label in recognized_labels:
                current_label = label
                sections.setdefault(label, [])
                continue

        if current_label:
            sections.setdefault(current_label, []).append(stripped)

    return sections


def _remove_markdown_images(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", "", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _build_main_description(sections: dict[str, list[str]]) -> str:
    content_values = _normalize_section_values(sections.get(_normalize_label("页面主题内容"), []))
    if content_values:
        return "\n".join(content_values).strip()

    title_values = _normalize_section_values(sections.get(_normalize_label("页面标题"), []))
    text_values = _normalize_section_values(sections.get(_normalize_label("页面文字"), []))
    script_values = _normalize_section_values(sections.get(_normalize_label("讲稿"), []))

    description_parts: list[str] = []
    if title_values:
        description_parts.append(f"页面标题：{title_values[0]}")
        description_parts.extend(title_values[1:])
    if text_values:
        description_parts.append("页面文字：")
        description_parts.extend(text_values)
    if script_values:
        description_parts.append(f"讲稿：{script_values[0]}")
        description_parts.extend(script_values[1:])
    return "\n".join(description_parts).strip()


def _normalize_section_values(values: list[str]) -> list[str]:
    normalized = []
    for item in values:
        text = str(item or "").strip()
        if text:
            normalized.append(text)
    return normalized


def _normalize_label(label: Any) -> str:
    return re.sub(r"\s+", "", str(label or "").strip())
