from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators.ppt.banana_models import PPTProject, PPTProjectIntent, PPTReferenceFile
from app.generators.ppt.intent_service import serialize_intent_record

logger = logging.getLogger(__name__)

SECTION_ORDER = [
    "intent_summary",
    "materials_summary",
    "knowledge_summary",
    "generation_strategy",
]

SECTION_TITLES = {
    "intent_summary": "用户意图摘要",
    "materials_summary": "项目资料提炼",
    "knowledge_summary": "知识库补充",
    "generation_strategy": "生成策略",
}

EMPTY_TEXT = "暂无"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.split(r"[\s,，。；;？?\-_/\\|()\[\]{}]+", _clean_text(text))
        if token
    ]


def format_planning_context_text(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for key in SECTION_ORDER:
        title = SECTION_TITLES[key]
        content = _clean_text(sections.get(key)) or EMPTY_TEXT
        parts.append(f"## {title}\n{content}")
    return "\n\n".join(parts).strip()


def score_material_chunk(query: str, chunk: dict[str, Any]) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    title = _clean_text(chunk.get("title"))
    content = _clean_text(chunk.get("content"))
    keywords = " ".join(_clean_text(item) for item in (chunk.get("keywords") or []))

    haystacks = {
        "title": title,
        "content": content,
        "keywords": keywords,
    }

    score = 0.0
    for token in query_tokens:
        if token in haystacks["title"]:
            score += 3.0
        if token in haystacks["keywords"]:
            score += 2.0
        if token in haystacks["content"]:
            score += 1.0

    if title and any(token in title for token in query_tokens):
        score += 0.5

    return score


def select_relevant_material_snippets(
    query: str,
    chunks: Iterable[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        score = score_material_chunk(query, chunk)
        if score <= 0:
            continue
        ranked.append((score, chunk))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in ranked[: max(limit, 0)]]


def build_strategy_fallback(
    intent_summary: dict[str, str],
    *,
    has_materials: bool,
    has_knowledge: bool,
) -> str:
    topic = _clean_text(intent_summary.get("topic")) or "当前主题"
    constraints = _clean_text(intent_summary.get("constraints"))
    style = _clean_text(intent_summary.get("style"))

    parts = [
        f"建议围绕“{topic}”组织封面、导入、核心内容、案例/活动和总结页面。",
    ]
    if constraints:
        parts.append(f"页数和结构优先遵守“{constraints}”的限制。")
    if style:
        parts.append(f"整体表达风格保持为“{style}”。")
    if has_materials:
        parts.append("优先吸收参考资料中的知识点、案例和视觉线索。")
    if has_knowledge:
        parts.append("使用知识库内容补充标准定义、重难点和准确表述。")
    parts.append("生成大纲时先保证结构清晰，再按页面主题分配内容密度。")
    return "\n".join(parts)


def get_saved_planning_context(project: PPTProject) -> dict[str, Any]:
    settings = dict(project.settings or {})
    return {
        "sections": settings.get("planning_context_sections") or {},
        "planning_context_text": _clean_text(settings.get("planning_context_text")),
        "meta": settings.get("planning_context_meta") or {},
    }


def _build_intent_summary_text(intent_summary: dict[str, str]) -> str:
    label_map = {
        "topic": "主题",
        "audience": "受众",
        "goal": "目标",
        "duration": "课时/时长",
        "constraints": "约束",
        "style": "风格",
        "interaction": "互动",
        "extra": "其他",
    }
    lines = []
    for key, label in label_map.items():
        value = _clean_text(intent_summary.get(key))
        if value:
            lines.append(f"{label}：{value}")
    return "\n".join(lines).strip() or "暂无明确的用户意图摘要。"


def _extract_reference_chunks(ref_file: PPTReferenceFile) -> list[dict[str, Any]]:
    parsed_content = ref_file.parsed_content or {}
    chunks_meta = parsed_content.get("chunks_meta") or []
    snippets: list[dict[str, Any]] = []

    for idx, chunk in enumerate(chunks_meta, start=1):
        if not isinstance(chunk, dict):
            continue
        content = _clean_text(chunk.get("content") or chunk.get("raw_content"))
        if not content:
            continue

        keywords = []
        for item in (chunk.get("knowledge_points") or []):
            text = _clean_text(item)
            if text:
                keywords.append(text)
        for item in (chunk.get("style_cues") or []):
            text = _clean_text(item)
            if text:
                keywords.append(text)

        image_descs = chunk.get("image_descriptions") or []
        for desc in image_descs:
            if isinstance(desc, dict):
                text = _clean_text(desc.get("description"))
                if text:
                    keywords.append(text[:80])

        snippets.append(
            {
                "title": f"{ref_file.filename} / 片段{idx}",
                "content": content,
                "keywords": keywords,
                "file_id": ref_file.id,
                "filename": ref_file.filename,
                "parse_status": ref_file.parse_status,
            }
        )

    searchable_text = _clean_text(parsed_content.get("searchable_text"))
    if searchable_text and not snippets:
        snippets.append(
            {
                "title": ref_file.filename,
                "content": searchable_text,
                "keywords": [],
                "file_id": ref_file.id,
                "filename": ref_file.filename,
                "parse_status": ref_file.parse_status,
            }
        )

    return snippets


def _build_query_from_intent(intent_summary: dict[str, str], extra: str | None = None) -> str:
    values = [
        _clean_text(intent_summary.get("topic")),
        _clean_text(intent_summary.get("goal")),
        _clean_text(intent_summary.get("constraints")),
        _clean_text(intent_summary.get("style")),
        _clean_text(extra),
    ]
    return " ".join(value for value in values if value).strip()


def _format_material_summary(snippets: list[dict[str, Any]], completed_files: list[PPTReferenceFile]) -> str:
    if snippets:
        return "\n".join(
            f"- {item['title']}：{_clean_text(item.get('content'))[:180]}"
            for item in snippets
        )

    if completed_files:
        return "\n".join(
            f"- {ref.filename}：已完成解析，可用于内容参考。"
            for ref in completed_files[:3]
        )

    return "暂无已完成解析的项目资料。"


def _format_generation_evidence(snippets: list[dict[str, Any]], knowledge_text: str) -> dict[str, str]:
    materials_text = "\n".join(
        f"- {item['title']}：{_clean_text(item.get('content'))[:200]}"
        for item in snippets
    ).strip()
    return {
        "materials_text": materials_text or "暂无与当前页面强相关的项目资料片段。",
        "knowledge_text": knowledge_text or "暂无与当前页面强相关的知识库补充。",
    }


async def _fetch_project_intent(db: AsyncSession, project: PPTProject) -> dict[str, Any]:
    result = await db.execute(select(PPTProjectIntent).where(PPTProjectIntent.project_id == project.id))
    intent = result.scalar_one_or_none()
    if intent is None:
        return {
            "intent_summary": {
                "topic": _clean_text(project.theme or project.outline_text),
                "audience": "",
                "goal": "",
                "duration": "",
                "constraints": "",
                "style": "",
                "interaction": "",
                "extra": "",
            }
        }
    return serialize_intent_record(intent)


async def _fetch_reference_files(
    db: AsyncSession,
    project: PPTProject,
    user_id: int,
) -> list[PPTReferenceFile]:
    result = await db.execute(
        select(PPTReferenceFile)
        .where(PPTReferenceFile.project_id == project.id, PPTReferenceFile.user_id == user_id)
        .order_by(PPTReferenceFile.created_at.asc())
    )
    return list(result.scalars().all())


async def _fetch_knowledge_context(
    query: str,
    project: PPTProject,
    user_id: int,
    *,
    k: int = 5,
) -> tuple[str, int]:
    if not query or not project.knowledge_library_ids:
        return "", 0

    try:
        from app.services.rag.hybrid_retriever import get_hybrid_retriever

        retriever = get_hybrid_retriever()
        docs = await retriever.search(
            query=query,
            user_id=user_id,
            k=k,
            library_ids=list(project.knowledge_library_ids or []),
        )
    except Exception as exc:
        logger.warning("Knowledge retrieval failed for PPT planning context: %s", exc)
        return "", 0

    parts: list[str] = []
    for doc in docs:
        text = _clean_text(getattr(doc, "page_content", doc))
        if text:
            parts.append(text[:300])

    return "\n\n".join(parts).strip(), len(parts)


async def build_generation_evidence(
    db: AsyncSession,
    project: PPTProject,
    user_id: int,
    *,
    extra_query: str | None = None,
    material_limit: int = 3,
    knowledge_k: int = 3,
) -> dict[str, Any]:
    intent_payload = await _fetch_project_intent(db, project)
    intent_summary = intent_payload.get("intent_summary") or {}
    query = _build_query_from_intent(intent_summary, extra=extra_query)

    ref_files = await _fetch_reference_files(db, project, user_id)
    completed_files = [ref for ref in ref_files if ref.parse_status == "completed" and ref.parsed_content]
    pending_files = [ref for ref in ref_files if ref.parse_status in {"pending", "processing"}]

    all_snippets: list[dict[str, Any]] = []
    for ref in completed_files:
        all_snippets.extend(_extract_reference_chunks(ref))

    selected_snippets = select_relevant_material_snippets(query, all_snippets, limit=material_limit)
    knowledge_text, knowledge_count = await _fetch_knowledge_context(
        query,
        project,
        user_id,
        k=knowledge_k,
    )
    formatted = _format_generation_evidence(selected_snippets, knowledge_text)

    return {
        "query": query,
        "intent_summary": intent_summary,
        "reference_files": ref_files,
        "completed_reference_files": completed_files,
        "pending_reference_files": pending_files,
        "selected_material_snippets": selected_snippets,
        "materials_text": formatted["materials_text"],
        "knowledge_text": formatted["knowledge_text"],
        "knowledge_count": knowledge_count,
    }


async def build_planning_context(
    db: AsyncSession,
    project: PPTProject,
    user_id: int,
    *,
    extra_query: str | None = None,
) -> dict[str, Any]:
    intent_payload = await _fetch_project_intent(db, project)
    intent_summary = intent_payload.get("intent_summary") or {}
    intent_text = _build_intent_summary_text(intent_summary)

    evidence = await build_generation_evidence(
        db,
        project,
        user_id,
        extra_query=extra_query,
        material_limit=3,
        knowledge_k=5,
    )

    materials_text = _format_material_summary(
        evidence["selected_material_snippets"],
        evidence["completed_reference_files"],
    )
    knowledge_summary = evidence["knowledge_text"] or "暂无可用的知识库补充内容。"
    strategy_text = build_strategy_fallback(
        intent_summary,
        has_materials=bool(evidence["completed_reference_files"]),
        has_knowledge=evidence["knowledge_count"] > 0,
    )

    sections = {
        "intent_summary": intent_text,
        "materials_summary": materials_text,
        "knowledge_summary": knowledge_summary,
        "generation_strategy": strategy_text,
    }
    planning_context_text = format_planning_context_text(sections)
    partial = bool(evidence["pending_reference_files"])
    last_generated_at = datetime.now(timezone.utc).isoformat()

    meta = {
        "partial": partial,
        "pending_reference_files": [
            {
                "id": ref.id,
                "filename": ref.filename,
                "parse_status": ref.parse_status,
            }
            for ref in evidence["pending_reference_files"]
        ],
        "source_counts": {
            "reference_files_total": len(evidence["reference_files"]),
            "reference_files_completed": len(evidence["completed_reference_files"]),
            "reference_snippets_used": len(evidence["selected_material_snippets"]),
            "knowledge_hits": evidence["knowledge_count"],
        },
        "last_generated_at": last_generated_at,
    }

    return {
        "sections": sections,
        "planning_context_text": planning_context_text,
        "partial": partial,
        "pending_reference_files": meta["pending_reference_files"],
        "source_counts": meta["source_counts"],
        "last_generated_at": last_generated_at,
        "meta": meta,
    }


async def persist_planning_context(
    db: AsyncSession,
    project: PPTProject,
    user_id: int,
    *,
    extra_query: str | None = None,
) -> dict[str, Any]:
    context = await build_planning_context(db, project, user_id, extra_query=extra_query)
    settings = dict(project.settings or {})
    settings["planning_context_sections"] = context["sections"]
    settings["planning_context_text"] = context["planning_context_text"]
    settings["planning_context_meta"] = context["meta"]
    project.settings = settings
    await db.commit()
    await db.refresh(project)
    return context
