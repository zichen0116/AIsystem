from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path

from app.core.config import settings
from app.schemas.html_schemas import ChatRequest, ChatResponse
from app.services.html_extract import extract_text_from_file
from app.services.html_llm import chat_with_llm, chat_with_llm_stream

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


async def _stream_generator(user_msg: str, context_file_id: str | None):
    """SSE 流生成器：向前端推送大模型逐字输出。"""
    import json
    context_text = _get_upload_text(context_file_id)
    if not settings.HTML_LLM_API_KEY:
        reply = (
            f"收到您的消息：「{user_msg}」。"
            + ("已结合您上传的教学材料理解上下文。" if context_file_id else "")
            + "请配置 HTML_LLM_API_KEY 以使用真实大模型。"
        )
        yield f"data: {json.dumps({'content': reply}, ensure_ascii=False)}\n\n"
        return
    try:
        async for chunk in chat_with_llm_stream(user_msg, context_text):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """流式对话接口。返回 SSE 流，前端可逐字显示。"""
    user_msg = (req.message or "").strip()
    if not user_msg:
        raise HTTPException(400, detail="消息不能为空")
    return StreamingResponse(
        _stream_generator(user_msg, req.context_file_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
