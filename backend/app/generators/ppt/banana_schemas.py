"""
PPT生成模块 - Pydantic Schemas
请求/响应模型定义
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============= Project Schemas =============

class PPTProjectCreate(BaseModel):
    """创建PPT项目"""
    title: str = Field(default="未命名PPT", max_length=255)
    description: Optional[str] = None
    creation_type: str = Field(default="dialog", pattern="^(dialog|file|renovation)$")
    theme: Optional[str] = Field(default=None, max_length=50)
    outline_text: Optional[str] = None
    settings: Optional[dict] = None
    knowledge_library_ids: Optional[list[int]] = Field(default_factory=list)
    """用户选择的知识库ID列表，Dialog生成时做RAG检索用"""


class PPTProjectUpdate(BaseModel):
    """更新PPT项目"""
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    outline_text: Optional[str] = None
    theme: Optional[str] = Field(default=None, max_length=50)
    settings: Optional[dict] = None
    status: Optional[str] = None
    exported_file_url: Optional[str] = None
    exported_at: Optional[datetime] = None
    knowledge_library_ids: Optional[list[int]] = None
    """用户选择的知识库ID列表"""


class ProjectSettingsUpdate(BaseModel):
    """更新项目设置"""
    description_generation_mode: Optional[str] = Field(default=None, pattern="^(auto|manual)$")
    description_extra_fields: Optional[list[str]] = None
    image_prompt_extra_fields: Optional[list[str]] = None
    detail_level: Optional[str] = Field(default=None, pattern="^(concise|default|detailed)$")
    theme: Optional[str] = Field(default=None, max_length=50)


class PPTProjectResponse(BaseModel):
    """PPT项目响应"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    creation_type: str
    outline_text: Optional[str]
    settings: dict
    theme: Optional[str]
    knowledge_library_ids: list[int]
    status: str
    exported_file_url: Optional[str]
    exported_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============= Page Schemas =============

class PPTPageCreate(BaseModel):
    """创建PPT页面"""
    project_id: Optional[int] = None
    page_number: int = 1
    title: Optional[str] = None
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    notes: Optional[str] = None
    config: Optional[dict] = None
    description_mode: str = "auto"
    points: Optional[list[str]] = None
    """前端大纲编辑器传入的要点列表，自动序列化为description"""
    part: Optional[str] = None
    """页面所属分类（如封面/目录/内容/总结），存入config"""


class PPTPageUpdate(BaseModel):
    """更新PPT页面"""
    title: Optional[str] = None
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    notes: Optional[str] = None
    config: Optional[dict] = None
    image_url: Optional[str] = None
    description_mode: Optional[str] = None
    material_ids: Optional[list[int]] = None
    points: Optional[list[str]] = None
    """前端大纲编辑器传入的要点列表"""
    part: Optional[str] = None
    """页面所属分类"""


class PPTPageResponse(BaseModel):
    """PPT页面响应"""
    id: int
    project_id: int
    page_number: int
    title: Optional[str]
    description: Optional[str]
    image_prompt: Optional[str]
    notes: Optional[str]
    image_url: Optional[str]
    image_version: int
    config: dict
    description_mode: str
    is_description_generating: bool
    is_image_generating: bool
    material_ids: list[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageReorderRequest(BaseModel):
    """页面重排序请求"""
    page_ids: list[int] = Field(min_length=1)


# ============= Task Schemas =============

class PPTTaskResponse(BaseModel):
    """PPT异步任务响应"""
    id: int
    project_id: int
    task_id: str
    task_type: str
    status: str
    progress: int
    result: Optional[dict]
    page_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ============= Material Schemas =============

class PPTMaterialResponse(BaseModel):
    """PPT素材响应"""
    id: int
    user_id: int
    project_id: Optional[int]
    filename: str
    oss_path: str
    url: str
    file_type: str
    file_size: Optional[int]
    material_type: str
    is_parsed: bool
    parsed_content: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


# ============= Reference File Schemas =============

class PPTReferenceFileResponse(BaseModel):
    """PPT参考文件响应"""
    id: int
    project_id: int
    user_id: int
    filename: str
    oss_path: str
    url: str
    file_type: str
    file_size: Optional[int]
    parse_status: str
    parse_error: Optional[str]
    parsed_outline: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


# ============= Session Schemas =============

class ChatMessageRequest(BaseModel):
    """对话框发送消息"""
    content: str
    round: Optional[int] = None
    metadata: Optional[dict] = None


class PPTSessionResponse(BaseModel):
    """PPT会话消息响应"""
    id: int
    project_id: int
    user_id: int
    role: str
    content: str
    metadata: Optional[dict] = Field(default=None, alias='session_metadata')
    round: int
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ============= Template Schemas =============

class UserTemplateCreate(BaseModel):
    """创建用户模板"""
    name: str = Field(max_length=100)
    description: Optional[str] = None
    template_data: dict
    cover_url: Optional[str] = None


class UserTemplateUpdate(BaseModel):
    """更新用户模板"""
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    template_data: Optional[dict] = None
    cover_url: Optional[str] = None


class UserTemplateResponse(BaseModel):
    """用户模板响应"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    template_data: dict
    cover_url: Optional[str]
    source: str
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============= Image Version Schemas =============

class PageImageVersionResponse(BaseModel):
    """页面图片版本响应"""
    id: int
    page_id: int
    user_id: int
    version: int
    image_url: str
    operation: str
    prompt: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ============= SSE Event Schemas =============

class SSEPageGenerateEvent(BaseModel):
    """SSE页面生成事件"""
    event: str = "message"
    data: dict = Field(default_factory=dict)


# ============= Refine Schemas =============

class RefineOutlineRequest(BaseModel):
    """自然语言精调大纲请求"""
    user_requirement: str = Field(min_length=1, description="用户修改要求，如'增加一页关于XXX的内容'")
    language: str = Field(default="zh", description="输出语言：zh/en/ja/auto")


class RefineDescriptionsRequest(BaseModel):
    """自然语言精调描述请求"""
    user_requirement: str = Field(min_length=1, description="用户修改要求，如'让描述更详细一些'")
    language: str = Field(default="zh", description="输出语言：zh/en/ja/auto")


class EditImageRequest(BaseModel):
    """编辑页面图片请求（支持JSON或multipart/form-data）"""
    edit_instruction: str = Field(min_length=1, description="自然语言编辑指令，如'把背景改成蓝色'")
    context_images: Optional["EditImageContext"] = None


class EditImageContext(BaseModel):
    """编辑图片的上下文图片"""
    use_template: bool = Field(default=False, description="是否使用模板图片")
    desc_image_urls: list[str] = Field(default_factory=list, description="描述中的图片URL列表")
    uploaded_image_ids: list[str] = Field(default_factory=list, description="上传的图片文件ID列表")


# ============= Dialog Schemas =============

class GenerateOutlineRequest(BaseModel):
    """Dialog页面生成大纲请求"""
    content: Optional[str] = None
    """可选，用户补充输入"""


class GenerateOutlineStreamRequest(BaseModel):
    """流式生成大纲请求"""
    idea_prompt: Optional[str] = None
    """可选，覆盖项目级的 idea_prompt"""
    language: str = Field(default="zh", description="输出语言")


class GenerateDescriptionsStreamRequest(BaseModel):
    """流式生成描述请求"""
    language: str = Field(default="zh", description="输出语言")
    detail_level: str = Field(default="default", description="详细程度：concise/default/detailed")


# ============= Material Generate Schema =============

class MaterialGenerateRequest(BaseModel):
    """AI生成素材图片请求"""
    prompt: str = Field(min_length=1, description="生成素材的提示词")
    aspect_ratio: str = Field(default="1:1", description="图片比例：1:1 / 16:9 / 4:3")


# ============= Export Schemas =============

class ExportRequest(BaseModel):
    """导出请求"""
    format: str = Field(pattern="^(pptx|pdf|images|editable_pptx)$")


class ExportTaskResponse(BaseModel):
    """导出任务响应（同步返回）"""
    task_id: Optional[str]
    url: Optional[str]
    status: str = "completed"
    message: Optional[str] = None
