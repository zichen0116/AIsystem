"""
聊天相关 Schema
"""
from pydantic import BaseModel, Field
import uuid
from datetime import datetime
from app.models.enums import ChatRole


class ChatMessageCreate(BaseModel):
    """发送聊天消息请求"""
    session_id: uuid.UUID
    content: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    """聊天消息响应"""
    id: int
    session_id: uuid.UUID
    user_id: int
    role: ChatRole
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """聊天历史响应"""
    messages: list[ChatMessageResponse]
    session_id: uuid.UUID


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    session_id: uuid.UUID
    message: str = "会话创建成功"


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: uuid.UUID
    created_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """会话列表响应"""
    items: list[SessionInfo]
    total: int
