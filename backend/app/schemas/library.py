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


class AddToGraphRequest(BaseModel):
    """添加到知识图谱请求"""
    asset_ids: list[int] = Field(..., min_length=1, description="知识资产 ID 列表")


class AddToGraphResponse(BaseModel):
    """添加到知识图谱响应"""
    task_id: str
    message: str
