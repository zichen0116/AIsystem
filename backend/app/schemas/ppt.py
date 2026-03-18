"""
PPT相关请求/响应Schema
"""
from datetime import datetime
from pydantic import BaseModel, Field


# ========== 会话 ==========

class PptSessionCreate(BaseModel):
    title: str = Field(default="新建PPT", max_length=255)


class PptSessionBrief(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PptOutlineBrief(BaseModel):
    id: int
    version: int
    content: str
    image_urls: dict | None = None
    template_id: str | None = None
    knowledge_library_ids: list | None = None
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PptMessageBrief(BaseModel):
    id: int
    role: str
    message_type: str
    content: str
    metadata_: dict | None = Field(None, alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class PptResultBrief(BaseModel):
    id: int
    version: int
    is_current: bool
    template_id: str | None = None
    docmee_ppt_id: str | None = None
    file_url: str | None = None
    status: str
    current_page: int
    total_pages: int
    has_edit_snapshot: bool = False
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PptResultDetail(PptResultBrief):
    source_pptx_property: str | None = None
    edited_pptx_property: str | None = None
    outline_id: int


class PptSessionDetail(BaseModel):
    id: int
    title: str
    status: str
    current_outline_id: int | None = None
    current_result_id: int | None = None
    messages: list[PptMessageBrief] = []
    outlines: list[PptOutlineBrief] = []
    results: list[PptResultBrief] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========== 大纲 ==========

class OutlineStreamRequest(BaseModel):
    session_id: int
    user_input: str = Field(..., min_length=1)
    knowledge_library_ids: list[int] = Field(default_factory=list)
    template_id: str | None = None


class OutlineApproveRequest(BaseModel):
    content: str | None = None
    image_urls: dict | None = None


# ========== PPT生成 ==========

class PptGenerateRequest(BaseModel):
    session_id: int
    outline_id: int
    template_id: str | None = None


class PptModifyRequest(BaseModel):
    instruction: str = Field(..., min_length=1)


# ========== 编辑快照 ==========

class EditSnapshotRequest(BaseModel):
    edited_pptx_property: str


# ========== 版本 ==========

class VersionSummary(BaseModel):
    outline_versions: list[PptOutlineBrief] = []
    result_versions: list[PptResultBrief] = []


# ========== 模板 ==========

class PptTemplate(BaseModel):
    id: str
    title: str | None = None
    cover_url: str | None = None
    category: str | None = None
