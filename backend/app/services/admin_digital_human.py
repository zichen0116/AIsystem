"""Admin digital human chat helpers."""

from __future__ import annotations

import re
from typing import Literal


PROJECT_INTRO_TEXT = (
    "我是 EduPrep 管理员端数字人。EduPrep 是一个面向教学与备课场景的智能平台，"
    "管理员端主要用于查看平台运行情况、数据中台看板和核心业务概览。"
    "当前大屏会集中展示教师备课任务、完成率和系统响应情况等关键指标，"
    "帮助管理员快速了解平台状态。"
)

ADMIN_CHAT_SYSTEM_PROMPT = (
    "你是 EduPrep 管理员端数字人。"
    "你可以介绍 EduPrep 项目、管理员端能力和数据中台用途，也可以与管理员进行轻量闲聊。"
    "如果用户问到未接入的实时数据、内部细节或你不知道的事实，要明确说明当前无法确认，不能编造。"
    "回答必须简短、自然、适合口播，不使用 Markdown、列表符号或代码块。"
)

INTRO_PATTERNS = (
    re.compile(r"(介绍|讲解|说明).*(项目|平台|系统|产品)"),
    re.compile(r"(项目|平台|系统|产品).*(是什么|做什么|干什么)"),
    re.compile(r"(介绍|讲解|说明).*(大屏|数据中台|看板)"),
    re.compile(r"(大屏|数据中台|看板).*(是什么|做什么|怎么看)"),
)


def is_intro_query(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text or "")
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in INTRO_PATTERNS)


def trim_history(history: list[dict] | list[object], max_items: int = 6) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in history or []:
        role = getattr(item, "role", None)
        content = getattr(item, "content", None)
        if isinstance(item, dict):
            role = item.get("role", role)
            content = item.get("content", content)
        role = (role or "").strip().lower()
        content = (content or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        items.append({"role": role, "content": content})
    return items[-max_items:]


def sanitize_speak_text(text: str, max_chars: int = 180) -> str:
    cleaned = re.sub(r"`{1,3}.*?`{1,3}", " ", text or "", flags=re.DOTALL)
    cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=\*\*|__|\*|_)", "", cleaned)
    cleaned = re.sub(r"(?<=\*\*)\s+(?=[\u4e00-\u9fff])", "", cleaned)
    cleaned = re.sub(r"(?<=__)\s+(?=[\u4e00-\u9fff])", "", cleaned)
    cleaned = re.sub(r"(?<=\*)\s+(?=[\u4e00-\u9fff])", "", cleaned)
    cleaned = re.sub(r"(?<=_)\s+(?=[\u4e00-\u9fff])", "", cleaned)
    cleaned = re.sub(r"(\*\*|__|\*|_)", "", cleaned)
    cleaned = re.sub(r"^[#>*\-\d\.\s]+", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "抱歉，我刚刚没有组织好回答，请再说一遍。"
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip("，,。.;；:： ") + "。"
    return cleaned


async def generate_admin_chat_response(
    *,
    message: str,
    history: list[dict] | list[object] | None,
    llm_invoke,
) -> dict[str, str]:
    message = (message or "").strip()
    normalized_history = trim_history(history or [])

    if is_intro_query(message):
        answer = PROJECT_INTRO_TEXT
        return {
            "answer": answer,
            "speak_text": sanitize_speak_text(answer),
            "mode": "intro",
        }

    messages = [{"role": "system", "content": ADMIN_CHAT_SYSTEM_PROMPT}]
    messages.extend(normalized_history)
    messages.append({"role": "user", "content": message})

    answer = ""
    try:
        llm_message = await llm_invoke(messages)
        answer = (getattr(llm_message, "content", "") or "").strip()
    except Exception:
        answer = ""

    if not answer:
        answer = "我是 EduPrep 管理员端数字人。目前我可以介绍项目情况，也可以和你简单聊聊。"

    return {
        "answer": sanitize_speak_text(answer, max_chars=260),
        "speak_text": sanitize_speak_text(answer),
        "mode": "chat",
    }
