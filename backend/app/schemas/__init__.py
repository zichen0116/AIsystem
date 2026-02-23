"""
Schema 导出
"""
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from app.schemas.courseware import (
    CoursewareCreate,
    CoursewareUpdate,
    CoursewareResponse,
    CoursewareListResponse,
    MasterLessonJSON,
)
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatHistoryResponse
from app.schemas.knowledge import (
    KnowledgeAssetCreate,
    KnowledgeAssetUpdate,
    KnowledgeAssetResponse,
    KnowledgeAssetListResponse,
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "UserResponse",
    "CoursewareCreate",
    "CoursewareUpdate",
    "CoursewareResponse",
    "CoursewareListResponse",
    "MasterLessonJSON",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatHistoryResponse",
    "KnowledgeAssetCreate",
    "KnowledgeAssetUpdate",
    "KnowledgeAssetResponse",
    "KnowledgeAssetListResponse",
]
