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
    library_id: int


class KnowledgeAssetUpdate(BaseModel):
    """更新知识资产请求"""
    vector_status: str | None = None


class KnowledgeAssetResponse(BaseModel):
    """知识资产响应"""
    id: int
    user_id: int
    library_id: int | None
    file_name: str
    file_type: FileType
    file_path: str
    vector_status: str
    chunk_count: int
    image_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeAssetStatusResponse(BaseModel):
    """知识资产状态响应（轻量）"""
    id: int
    vector_status: str
    chunk_count: int
    image_count: int

    model_config = {"from_attributes": True}


class KnowledgeAssetListResponse(BaseModel):
    """知识资产列表响应"""
    items: list[KnowledgeAssetResponse]
    total: int
