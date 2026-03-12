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
from app.schemas.data_analysis import (
    UploadAndAnalyzeResponse,
    GenerateChartsRequest,
    GenerateChartsResponse,
    ChartOption,
    DataColumnInfo,
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
    "UploadAndAnalyzeResponse",
    "GenerateChartsRequest",
    "GenerateChartsResponse",
    "ChartOption",
    "DataColumnInfo",
]
