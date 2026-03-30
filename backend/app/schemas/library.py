"""
知识库相关 Schema
"""
from pydantic import BaseModel, Field
from datetime import datetime


class KnowledgeLibraryCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    is_system: bool = False
    is_public: bool = False


class KnowledgeLibraryUpdate(BaseModel):
    """更新知识库请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    is_public: bool | None = None


class KnowledgeLibraryResponse(BaseModel):
    """知识库响应"""
    id: int
    owner_id: int
    name: str
    description: str | None
    is_system: bool
    is_public: bool
    tags: list[str] = Field(default_factory=list)
    asset_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeLibraryListResponse(BaseModel):
    """知识库列表响应"""
    items: list[KnowledgeLibraryResponse]
    total: int


class TagRenameRequest(BaseModel):
    """标签重命名请求"""
    old_name: str = Field(..., min_length=1)
    new_name: str = Field(..., min_length=1)


class TagRenameResponse(BaseModel):
    """标签重命名响应"""
    updated_count: int


class AddToGraphRequest(BaseModel):
    """添加到知识图谱请求"""
    asset_ids: list[int] = Field(..., min_length=1, description="知识资产 ID 列表")


class AddToGraphResponse(BaseModel):
    """添加到知识图谱响应"""
    task_id: str
    message: str
