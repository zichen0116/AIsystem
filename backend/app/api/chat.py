"""
聊天路由
"""
from typing import Annotated, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field
import uuid

from app.core.database import get_db
from app.core.auth import CurrentUser
from app.models.chat_history import ChatHistory
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatHistoryResponse,
    CreateSessionResponse,
    SessionInfo,
    SessionListResponse,
)

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: ChatMessageCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """发送聊天消息"""
    # 保存用户消息
    user_message = ChatHistory(
        session_id=data.session_id,
        user_id=current_user.id,
        role="user",
        content=data.content
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    # TODO: 调用 AI 服务生成回复
    # 这里应该调用 AI 服务来处理用户消息并生成回复
    ai_response_content = "这是 AI 的回复占位符，实际实现需要调用 AI 服务"

    # 保存 AI 消息
    ai_message = ChatHistory(
        session_id=data.session_id,
        user_id=current_user.id,
        role="assistant",
        content=ai_response_content
    )
    db.add(ai_message)
    await db.commit()
    await db.refresh(ai_message)

    return ai_message


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取会话历史"""
    result = await db.execute(
        select(ChatHistory).where(
            and_(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == current_user.id
            )
        ).order_by(ChatHistory.created_at)
    )
    messages = result.scalars().all()

    return ChatHistoryResponse(
        messages=messages,
        session_id=session_id
    )


@router.get("/sessions", response_model=list[uuid.UUID])
async def list_sessions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """获取会话列表"""
    result = await db.execute(
        select(ChatHistory.session_id).where(
            ChatHistory.user_id == current_user.id
        ).distinct()
    )
    sessions = result.scalars().all()
    return sessions


@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(current_user: CurrentUser):
    """创建新会话"""
    new_session_id = uuid.uuid4()
    return CreateSessionResponse(
        session_id=new_session_id,
        message="会话创建成功"
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """删除会话"""
    # 查询并删除该会话的所有消息
    result = await db.execute(
        select(ChatHistory).where(
            and_(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == current_user.id
            )
        )
    )
    messages = result.scalars().all()

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    for msg in messages:
        await db.delete(msg)
    await db.commit()
    return None


# ==================== Human-in-the-loop 接口 ====================

class ResumeChatRequest(BaseModel):
    """恢复聊天的请求"""
    thread_id: str = Field(..., description="线程ID，来自初始响应的 thread_id")
    new_outline: Optional[Dict[str, Any]] = Field(None, description="用户修改后的新大纲")
    user_feedback: Optional[str] = Field(None, description="用户的修改意见")


class ResumeChatResponse(BaseModel):
    """恢复聊天的响应"""
    answer: str = Field(..., description="最终答案")
    outline: Optional[Dict[str, Any]] = Field(None, description="最终大纲（扩写后）")
    status: str = Field(..., description="状态：completed")
    download_url: Optional[str] = Field(None, description="PPT 下载链接")


@router.post("/resume", response_model=ResumeChatResponse)
async def resume_chat(
    data: ResumeChatRequest,
    current_user: CurrentUser
):
    """
    恢复 Agent 执行

    当用户确认或修改大纲后调用此接口继续执行流程

    用法：
    1. 首次调用 send_message 生成大纲
    2. 响应中返回 thread_id，前端展示大纲给用户
    3. 用户确认或修改后，调用此接口
    4. LangGraph 执行 finalize_node 进行内容扩写
    5. 生成 PPT 文件，返回下载链接

    返回：
    - status: "completed"
    - answer: 最终内容
    - outline: 扩写后的完整大纲
    - download_url: PPT 文件下载链接（如果有）
    """
    from app.services.ai.graph.workflow import resume_agent
    from app.generators.ppt_generator import PPTGenerator
    import os
    import uuid
    from pathlib import Path

    try:
        # 1. 恢复 Agent 执行（会触发 finalize_node 进行内容扩写）
        result = await resume_agent(
            thread_id=data.thread_id,
            user_id=current_user.id,
            new_outline=data.new_outline,
            user_feedback=data.user_feedback
        )

        # 2. 获取扩写后的大纲
        outline = result.get("outline")
        answer = result.get("answer", "")

        # 3. 如果有大纲，尝试生成 PPT
        download_url = None
        if outline:
            try:
                # 创建 PPT 生成器
                ppt_generator = PPTGenerator()

                # 生成唯一的文件名
                ppt_filename = f"lesson_{uuid.uuid4().hex[:8]}.pptx"
                output_dir = Path("media/ppt")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / ppt_filename

                # 调用 PPT 生成器
                await ppt_generator.generate(outline, output_path)

                # 构建下载 URL
                # 注意：实际部署时需要配置静态文件服务
                download_url = f"/media/ppt/{ppt_filename}"

                logger.info(f"PPT 生成成功: {output_path}")

            except Exception as ppt_error:
                logger.error(f"PPT 生成失败: {ppt_error}")
                # PPT 生成失败不影响主流程

        # 4. 返回结果
        return ResumeChatResponse(
            answer=answer,
            outline=outline,
            status=result.get("status", "completed"),
            download_url=download_url
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复执行失败: {str(e)}"
        )


class GenerateOutlineRequest(BaseModel):
    """生成大纲的请求"""
    query: str = Field(..., description="用户问题")
    session_id: uuid.UUID = Field(..., description="会话ID")


class GenerateOutlineResponse(BaseModel):
    """生成大纲的响应"""
    answer: str = Field(..., description="当前阶段的答案/大纲（可能是文本或JSON）")
    outline: Optional[Dict[str, Any]] = Field(None, description="结构化大纲")
    thread_id: str = Field(..., description="线程ID，用于后续 resume")
    status: str = Field(..., description="状态：awaiting_approval 或 completed")


@router.post("/outline", response_model=GenerateOutlineResponse)
async def generate_outline(
    data: GenerateOutlineRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    生成大纲（带 Human-in-the-loop）

    此接口会在生成大纲后暂停，等待用户确认
    - 返回 thread_id，前端展示大纲给用户
    - 用户确认后调用 /chat/resume 继续执行
    """
    from app.services.ai.graph.workflow import run_agent_with_checkpoint

    # 保存用户消息
    user_message = ChatHistory(
        session_id=data.session_id,
        user_id=current_user.id,
        role="user",
        content=data.query
    )
    db.add(user_message)
    await db.commit()

    try:
        result = await run_agent_with_checkpoint(
            query=data.query,
            user_id=current_user.id,
            chat_history=None
        )

        # 保存 AI 消息（可能是大纲或部分回答）
        ai_message = ChatHistory(
            session_id=data.session_id,
            user_id=current_user.id,
            role="assistant",
            content=result.get("answer", "")
        )
        db.add(ai_message)
        await db.commit()

        return GenerateOutlineResponse(
            answer=result.get("answer", ""),
            outline=result.get("outline"),
            thread_id=result.get("thread_id", ""),
            status=result.get("status", "awaiting_approval")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成大纲失败: {str(e)}"
        )
