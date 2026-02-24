"""
知识库相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime


class KnowledgeLibraryCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_system: bool = False
    is_public: bool = False


class KnowledgeLibraryUpdate(BaseModel):
    """更新知识库请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool | None = None


class KnowledgeLibraryResponse(BaseModel):
    """知识库响应"""
    id: int
    owner_id: int
    name: str
    description: str | None
    is_system: bool
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeLibraryListResponse(BaseModel):
    """知识库列表响应"""
    items: list[KnowledgeLibraryResponse]
    total: int
