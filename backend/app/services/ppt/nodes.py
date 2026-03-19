"""
PPT LangGraph 节点实现

围绕业务主链路：知识检索 -> 大纲生成 -> 自动配图 -> 审批中断 -> PPT生成
"""
import logging
import json
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.ppt.state import PptAgentState
from app.services.ppt.image_search import auto_assign_images

logger = logging.getLogger(__name__)


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
