"""
Structured PPT outline payload helpers.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_outline_payload(
    title: str,
    clarification: dict[str, Any] | None,
    sections: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    payload = {
        "title": title.strip() if title else "",
        "clarification": deepcopy(clarification or {}),
        "sections": deepcopy(sections or []),
    }
    return normalize_outline_payload(payload)


def normalize_outline_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    safe_payload["title"] = (safe_payload.get("title") or "").strip()
    safe_payload["clarification"] = deepcopy(safe_payload.get("clarification") or {})
    normalized_sections: list[dict[str, Any]] = []

    for section_index, section in enumerate(safe_payload.get("sections") or [], start=1):
        safe_section = deepcopy(section or {})
        normalized_pages: list[dict[str, Any]] = []
        for page_index, page in enumerate(safe_section.get("pages") or [], start=1):
            safe_page = deepcopy(page or {})
            safe_page["id"] = safe_page.get("id") or f"page-{page_index}"
            safe_page["title"] = safe_page.get("title") or ""
            safe_page["subtitle"] = safe_page.get("subtitle") or ""
            safe_page["blocks"] = deepcopy(safe_page.get("blocks") or [])
            safe_page["image_candidates"] = deepcopy(safe_page.get("image_candidates") or [])
            safe_page["selected_image_id"] = safe_page.get("selected_image_id")
            safe_page["speaker_notes"] = _normalize_speaker_notes(safe_page)
            normalized_pages.append(safe_page)

        normalized_sections.append(
            {
                "id": safe_section.get("id") or f"section-{section_index}",
                "title": safe_section.get("title") or "",
                "pages": normalized_pages,
            }
        )

    safe_payload["sections"] = normalized_sections
    return safe_payload


def markdown_to_outline_payload(markdown: str, image_urls: dict[str, Any] | None = None) -> dict[str, Any]:
    image_urls = image_urls or {}
    lines = [raw_line.strip() for raw_line in (markdown or "").splitlines() if raw_line.strip()]
    has_level3_pages = any(line.startswith("### ") for line in lines)
    page_heading_prefix = "### " if has_level3_pages else "## "
    page_count = sum(1 for line in lines if line.startswith(page_heading_prefix))
    legacy_image_offset = (
        not has_level3_pages
        and image_urls.get("0") is not None
        and image_urls.get(str(page_count)) is not None
    )

    title = "未命名PPT"
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    current_page: dict[str, Any] | None = None
    current_block: dict[str, Any] | None = None
    page_index = -1

    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip() or title
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            if has_level3_pages:
                current_section = {
                    "id": f"section-{len(sections) + 1}",
                    "title": heading,
                    "pages": [],
                }
                sections.append(current_section)
                current_page = None
                current_block = None
            else:
                current_section = _ensure_default_section(sections)
                page_index += 1
                current_page = _create_page(page_index, heading, image_urls, page_count, legacy_image_offset)
                current_section["pages"].append(current_page)
                current_block = None
            continue

        if line.startswith("### "):
            current_section = current_section or _ensure_default_section(sections)
            page_index += 1
            current_page = _create_page(page_index, line[4:].strip(), image_urls, page_count, legacy_image_offset)
            current_section["pages"].append(current_page)
            current_block = None
            continue

        if line.startswith("#### "):
            if current_page is None:
                continue
            current_block = {
                "id": f"{current_page['id']}-block-{len(current_page['blocks']) + 1}",
                "title": line[5:].strip(),
                "content": [],
            }
            current_page["blocks"].append(current_block)
            continue

        normalized_line = line[2:].strip() if line.startswith("- ") else line
        if current_page is None:
            continue
        if current_block is None:
            current_block = {
                "id": f"{current_page['id']}-block-{len(current_page['blocks']) + 1}",
                "title": "",
                "content": [],
            }
            current_page["blocks"].append(current_block)
        current_block["content"].append(normalized_line)

    return build_outline_payload(title, clarification=None, sections=sections)


def payload_to_docmee_markdown(payload: dict[str, Any]) -> str:
    normalized_payload = normalize_outline_payload(payload)
    title = normalized_payload.get("title", "").strip() or "未命名PPT"
    lines: list[str] = [f"# {title}", ""]

    sections = normalized_payload.get("sections") or []
    for section in sections:
        section_title = (section or {}).get("title", "").strip()
        if section_title:
            lines.extend([f"## {section_title}", ""])

        pages = (section or {}).get("pages") or []
        for page in pages:
            page_title = (page or {}).get("title", "").strip() or "未命名页面"
            lines.extend([f"### {page_title}", ""])

            subtitle = (page or {}).get("subtitle", "").strip()
            if subtitle:
                lines.extend([subtitle, ""])

            blocks = (page or {}).get("blocks") or []
            for block in blocks:
                block_title = (block or {}).get("title", "").strip()
                if block_title:
                    lines.extend([f"#### {block_title}", ""])

                content = (block or {}).get("content", "")
                normalized_content = _normalize_block_content(content)
                for paragraph in normalized_content:
                    lines.append(f"- {paragraph}")
                if normalized_content:
                    lines.append("")

            image_markdown = build_page_image_markdown(page)
            if image_markdown:
                lines.extend([image_markdown, ""])

    return "\n".join(_trim_trailing_blank_lines(lines)).strip()


def build_page_image_markdown(page: dict[str, Any], alt_prefix: str = "配图") -> str:
    selected_image_id = (page or {}).get("selected_image_id")
    if not selected_image_id:
        return ""

    candidates = (page or {}).get("image_candidates") or []
    for index, candidate in enumerate(candidates, start=1):
        if candidate.get("id") != selected_image_id:
            continue
        url = (candidate.get("url") or "").strip()
        if not url:
            return ""
        return f"![{alt_prefix}{index}]({url})"

    return ""


def outline_payload_has_renderable_content(payload: dict[str, Any] | None) -> bool:
    if not payload or not isinstance(payload, dict):
        return False

    for section in payload.get("sections") or []:
        for page in (section or {}).get("pages") or []:
            if (page or {}).get("title", "").strip():
                return True
            for block in (page or {}).get("blocks") or []:
                if _normalize_block_content((block or {}).get("content")):
                    return True
    return False


def _normalize_block_content(content: Any) -> list[str]:
    if content is None:
        return []
    if isinstance(content, list):
        return [str(item).strip() for item in content if str(item).strip()]

    lines = [line.strip() for line in str(content).splitlines()]
    return [line for line in lines if line]


def _trim_trailing_blank_lines(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and trimmed[-1] == "":
        trimmed.pop()
    return trimmed


def _build_page_candidates(
    page_index: int,
    image_urls: dict[str, Any],
    page_count: int,
    legacy_image_offset: bool,
) -> list[dict[str, Any]]:
    value = image_urls.get(str(page_index + 1)) if legacy_image_offset else image_urls.get(str(page_index))
    if value is None and image_urls.get(str(page_index + 1)) is not None and image_urls.get(str(page_count)) is not None:
        value = image_urls.get(str(page_index + 1))
    if not value:
        return []
    candidates = value if isinstance(value, list) else [value]
    result = []
    for idx, candidate in enumerate(candidates[:2], start=1):
        if not candidate:
            continue
        if isinstance(candidate, dict):
            url = candidate.get("url") or ""
            candidate_id = candidate.get("id") or f"page-{page_index + 1}-img-{idx}"
        else:
            url = str(candidate)
            candidate_id = f"page-{page_index + 1}-img-{idx}"
        if url:
            result.append({"id": candidate_id, "url": url})
    return result


def _create_page(
    page_index: int,
    title: str,
    image_urls: dict[str, Any],
    page_count: int,
    legacy_image_offset: bool,
) -> dict[str, Any]:
    return {
        "id": f"page-{page_index + 1}",
        "title": title,
        "subtitle": "",
        "blocks": [],
        "speaker_notes": "",
        "image_candidates": _build_page_candidates(page_index, image_urls, page_count, legacy_image_offset),
        "selected_image_id": None,
    }


def _ensure_default_section(sections: list[dict[str, Any]]) -> dict[str, Any]:
    if sections:
        return sections[0]
    section = {"id": "section-1", "title": "内容大纲", "pages": []}
    sections.append(section)
    return section


def build_speaker_notes_for_page(page_title: str, subtitle: str, blocks: list[dict[str, Any]]) -> str:
    topic = (page_title or "").strip() or "本页内容"
    details: list[str] = []

    if (subtitle or "").strip():
        details.append(subtitle.strip())

    for block in blocks or []:
        block_title = (block.get("title") or "").strip()
        if block_title:
            details.append(block_title)
        for item in _normalize_block_content(block.get("content"))[:3]:
            details.append(item)
        if len(details) >= 3:
            break

    unique_details: list[str] = []
    for detail in details:
        if detail and detail not in unique_details:
            unique_details.append(detail)

    if not unique_details:
        return f"这一页主要讲{topic}，可以先说明核心主题，再自然过渡到下一页。"

    first_detail = unique_details[0]
    if len(unique_details) == 1:
        return f"这一页主要讲{topic}，可以先点出{first_detail}，再补充课堂里的关键含义。"

    second_detail = unique_details[1]
    return f"这一页主要讲{topic}，先说明{first_detail}，再结合{second_detail}展开，最后用一句话做好过渡。"


def _normalize_speaker_notes(page: dict[str, Any]) -> str:
    current_notes = (page.get("speaker_notes") or "").strip()
    if current_notes:
        return current_notes
    return build_speaker_notes_for_page(
        page.get("title") or "",
        page.get("subtitle") or "",
        page.get("blocks") or [],
    )
