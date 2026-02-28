from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.core.config import settings
from app.schemas.html_schemas import ChatRequest, ChatResponse
from app.services.html_extract import extract_text_from_file
from app.services.html_llm import chat_with_llm

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_upload_text(file_id: str | None) -> str | None:
    if not file_id:
        return None
    upload_dir = Path(settings.HTML_UPLOAD_DIR)
    for ext in [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".txt"]:
        p = upload_dir / f"{file_id}{ext}"
        if p.exists():
            return extract_text_from_file(p)
    return None


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """对话接口。配置了 LLM_API_KEY 时调用大模型，否则返回模拟回复。"""
    user_msg = (req.message or "").strip()
    if not user_msg:
        raise HTTPException(400, detail="消息不能为空")

    context_text = _get_upload_text(req.context_file_id)
    reply, suggestions = await chat_with_llm(user_msg, context_text)

    if reply:
        return ChatResponse(message=reply, suggestions=suggestions)

    # 未配置大模型或调用失败时使用模拟回复
    reply = (
        f"收到您的消息：「{user_msg}」。"
        + ("已结合您上传的教学材料理解上下文。" if req.context_file_id else "")
        + "我是对话小助手，可结合您上传的文件内容回答问题。请确保已配置 LLM_API_KEY 以使用真实大模型。"
    )
    suggestions = [
        "帮我概括这份教案的重点",
        "根据这份教案设计几个课堂提问",
        "帮我把教学内容改写成适合学生理解的说法",
    ]
    return ChatResponse(message=reply, suggestions=suggestions)
