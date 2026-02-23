"""
知识资产相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.enums import FileType


class KnowledgeAssetCreate(BaseModel):
    """创建知识资产请求"""
    file_name: str = Field(..., min_length=1, max_length=255)
    file_type: FileType
    file_path: str = Field(..., max_length=500)


class KnowledgeAssetUpdate(BaseModel):
    """更新知识资产请求"""
    vector_status: bool | None = None


class KnowledgeAssetResponse(BaseModel):
    """知识资产响应"""
    id: int
    user_id: int
    file_name: str
    file_type: FileType
    file_path: str
    vector_status: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeAssetListResponse(BaseModel):
    """知识资产列表响应"""
    items: list[KnowledgeAssetResponse]
    total: int
