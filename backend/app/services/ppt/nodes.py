"""
PPT LangGraph 节点实现

围绕业务主链路：知识检索 -> 大纲生成 -> 自动配图 -> 审批中断 -> PPT生成
"""
import copy
import logging
import json
import re
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.ppt.state import PptAgentState
from app.services.ppt.image_search import auto_assign_images

logger = logging.getLogger(__name__)

TITLE_PLACEHOLDER_TYPES = {"title", "ctrtitle", "centeredtitle"}
SUBTITLE_PLACEHOLDER_TYPES = {"subtitle", "ctrsubtitle", "subsubtitle"}
BODY_PLACEHOLDER_TYPES = {"body", "content", "text", "obj"}


def _get_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


async def retrieve_knowledge(state: PptAgentState) -> dict:
    """检索知识库获取相关上下文"""
    library_ids = state.get("selected_library_ids", [])
    user_input = state.get("user_input", "")

    if not library_ids or not user_input:
        return {"retrieved_context": ""}

    try:
        from app.services.rag.hybrid_retriever import HybridRetriever
        retriever = HybridRetriever(user_id=state["user_id"])
        docs = await retriever.retrieve(user_input, library_ids=library_ids, top_k=5)
        context = "\n\n".join(doc.page_content for doc in docs)
        return {"retrieved_context": context}
    except Exception as e:
        logger.warning(f"Knowledge retrieval failed: {e}")
        return {"retrieved_context": ""}


async def generate_outline_streaming(state: PptAgentState) -> AsyncIterator[str]:
    """流式生成大纲，yield每个文本块"""
    user_input = state.get("user_input", "")
    context = state.get("retrieved_context", "")
    template_id = state.get("template_id")

    system_prompt = """你是一个专业的PPT大纲生成助手。根据用户需求生成结构化的PPT大纲。

要求：
1. 使用Markdown格式
2. 一级标题(#)为PPT主题
3. 二级标题(##)为每页标题
4. 每页下用要点列表描述内容
5. 页数控制在8-15页
6. 内容专业、结构清晰"""

    if context:
        system_prompt += f"\n\n参考知识库内容：\n{context}"

    if template_id:
        system_prompt += f"\n\n使用模板ID: {template_id}"

    client = _get_llm_client()
    stream = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下主题生成PPT大纲：\n{user_input}"},
        ],
        temperature=0.7,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def generate_outline(state: PptAgentState) -> dict:
    """非流式生成大纲（用于LangGraph节点）"""
    full_text = ""
    async for chunk in generate_outline_streaming(state):
        full_text += chunk

    return {
        "outline_markdown": full_text,
        "messages": [AIMessage(content=full_text)],
        "next_action": "auto_image",
    }


async def auto_image_node(state: PptAgentState) -> dict:
    """自动配图节点"""
    markdown = state.get("outline_markdown", "")
    image_urls = await auto_assign_images(markdown)
    return {
        "image_urls": image_urls,
        "next_action": "approve",
    }


async def approval_node(state: PptAgentState) -> dict:
    """审批中断节点 - 等待用户确认大纲"""
    return {
        "outline_approved": False,
        "next_action": "waiting_approval",
    }


async def modify_outline_streaming(state: PptAgentState) -> AsyncIterator[str]:
    """流式修改大纲"""
    user_input = state.get("user_input", "")
    current_outline = state.get("outline_markdown", "")

    client = _get_llm_client()
    stream = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是PPT大纲修改助手。根据用户的修改意见，在现有大纲基础上进行调整。保持Markdown格式。"},
            {"role": "user", "content": f"当前大纲：\n{current_outline}\n\n修改要求：\n{user_input}"},
        ],
        temperature=0.7,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def modify_slide_json(
    instruction: str,
    pptx_obj: dict,
    slide_index: int,
) -> dict:
    """基于当前单页 JSON 直接修改 PPT 页面结构。"""
    pages = pptx_obj.get("pages") or []
    if slide_index < 0 or slide_index >= len(pages):
        raise ValueError("slide_index out of range")

    current_page = pages[slide_index]
    safe_edit = _extract_safe_text_edit(instruction)
    if safe_edit:
        updated_page = _update_page_text(
            current_page,
            target=safe_edit["target"],
            replacement_text=safe_edit["replacement_text"],
        )
        if updated_page is not None:
            return updated_page

    client = _get_llm_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "你是 PPT JSON 编辑助手。"
                    "用户会给你一页当前 PPT 的 page JSON 和修改要求。"
                    "你必须只返回修改后的单页 JSON 对象，不要返回 markdown，不要解释。"
                    "必须保留页面现有的 id、pid、type、extInfo、children 等结构，"
                    "只做满足要求所需的最小修改，确保结果仍然是合法 JSON。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": instruction,
                        "slide_index": slide_index,
                        "total_slides": len(pages),
                        "current_page": current_page,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("LLM 未返回页面 JSON")

    try:
        updated_page = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM 返回的页面 JSON 解析失败") from exc

    if not isinstance(updated_page, dict):
        raise RuntimeError("LLM 返回的页面结构无效")

    return updated_page


def _extract_safe_text_edit(instruction: str) -> dict | None:
    text = (instruction or "").strip()
    if not text:
        return None

    target_specs = [
        ("subtitle", ["副标题"]),
        ("title", ["主标题", "标题"]),
        ("body", ["正文", "内容", "文案"]),
    ]

    for target, keywords in target_specs:
        if target == "title" and "副标题" in text:
            continue
        replacement_text = _extract_replacement_text(text, keywords)
        if replacement_text:
            return {
                "target": target,
                "replacement_text": replacement_text,
            }
    return None


def _extract_replacement_text(instruction: str, keywords: list[str]) -> str | None:
    keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
    patterns = [
        rf"(?:{keyword_pattern}).*?(?:改成|改为|换成|改一下为|写成|替换成)\s*[《“\"]([^》”\"\n]+)[》”\"]",
        rf"(?:{keyword_pattern}).*?(?:改成|改为|换成|改一下为|写成|替换成)\s*[:：]?\s*([^\n]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, instruction, re.IGNORECASE)
        if not match:
            continue
        candidate = match.group(1).strip()
        candidate = re.sub(r"[。！!；;，,]+$", "", candidate).strip()
        if candidate:
            return candidate
    return None


def _update_page_text(page: dict, target: str, replacement_text: str) -> dict | None:
    updated_page = copy.deepcopy(page)
    text_nodes = _find_text_nodes(updated_page)
    if not text_nodes:
        return None

    target_node = _select_text_node_for_target(text_nodes, target)
    if target_node is None:
        return None

    runs = _collect_text_runs(target_node)
    if not runs:
        return None

    runs[0]["text"] = replacement_text
    for run in runs[1:]:
        if "text" in run:
            run["text"] = ""
    return updated_page


def _select_text_node_for_target(text_nodes: list[dict], target: str) -> dict | None:
    placeholder_types = [_get_placeholder_type(node) for node in text_nodes]

    if target == "title":
        for index, placeholder_type in enumerate(placeholder_types):
            if placeholder_type in TITLE_PLACEHOLDER_TYPES:
                return text_nodes[index]
        return text_nodes[0] if text_nodes else None

    if target == "subtitle":
        for index, placeholder_type in enumerate(placeholder_types):
            if placeholder_type in SUBTITLE_PLACEHOLDER_TYPES:
                return text_nodes[index]
        non_title_nodes = [
            node for node, placeholder_type in zip(text_nodes, placeholder_types)
            if placeholder_type not in TITLE_PLACEHOLDER_TYPES
        ]
        return non_title_nodes[0] if non_title_nodes else None

    if target == "body":
        for index, placeholder_type in enumerate(placeholder_types):
            if placeholder_type in BODY_PLACEHOLDER_TYPES:
                return text_nodes[index]
        for node, placeholder_type in zip(text_nodes, placeholder_types):
            if placeholder_type not in TITLE_PLACEHOLDER_TYPES | SUBTITLE_PLACEHOLDER_TYPES:
                return node
        return text_nodes[-1] if text_nodes else None

    return None


def _get_placeholder_type(node: dict) -> str:
    placeholder_type = (
        (((node.get("extInfo") or {}).get("property") or {}).get("placeholder") or {}).get("type")
    )
    if not isinstance(placeholder_type, str):
        return ""
    return placeholder_type.strip().lower()


def _find_text_nodes(node: dict) -> list[dict]:
    nodes: list[dict] = []

    def walk(current: dict) -> None:
        if not isinstance(current, dict):
            return
        if current.get("type") in {"text", "freeform"}:
            nodes.append(current)
        for child in current.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(node)
    return nodes


def _collect_text_runs(node: dict) -> list[dict]:
    runs: list[dict] = []

    def walk(current: dict) -> None:
        if not isinstance(current, dict):
            return
        if isinstance(current.get("text"), str):
            runs.append(current)
        for child in current.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    walk(node)
    return runs
