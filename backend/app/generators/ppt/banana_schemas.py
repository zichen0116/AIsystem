"""
PPT生成模块 - Pydantic Schemas
请求/响应模型定义
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


THEME_MAX_LENGTH = 50


def _normalize_project_style_payload(values: object) -> object:
    """Normalize style-related fields for backward-compatible payloads."""
    if not isinstance(values, dict):
        return values

    normalized = dict(values)
    settings = normalized.get("settings")
    settings_dict = dict(settings) if isinstance(settings, dict) else None

    theme_raw = normalized.get("theme")
    style_raw = normalized.get("template_style")

    theme_text = str(theme_raw or "").strip() if theme_raw is not None else None
    style_text = str(style_raw or "").strip() if style_raw is not None else None

    settings_style_text = None
    if settings_dict is not None and "template_style" in settings_dict:
        settings_style_text = str(settings_dict.get("template_style") or "").strip() or None
        settings_dict["template_style"] = settings_style_text
        normalized["settings"] = settings_dict

    if theme_text is not None:
        if len(theme_text) > THEME_MAX_LENGTH:
            if not style_text and not settings_style_text:
                style_text = theme_text
                normalized["template_style"] = style_text
                if settings_dict is not None:
                    settings_dict["template_style"] = style_text
                    normalized["settings"] = settings_dict
            normalized["theme"] = theme_text[:THEME_MAX_LENGTH]
        else:
            normalized["theme"] = theme_text or None

    if style_raw is not None:
        normalized["template_style"] = style_text or None

    return normalized


# ============= Project Schemas =============

class PPTProjectCreate(BaseModel):
    """创建PPT项目"""
    title: str = Field(default="未命名PPT", max_length=255)
    description: Optional[str] = None
    creation_type: str = Field(default="dialog", pattern="^(dialog|file|renovation)$")
    theme: Optional[str] = Field(default=None, max_length=THEME_MAX_LENGTH)
    template_style: Optional[str] = None
    outline_text: Optional[str] = None
    settings: Optional[dict] = None
    knowledge_library_ids: Optional[list[int]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_style_fields(cls, values: object) -> object:
        return _normalize_project_style_payload(values)
    """用户选择的知识库ID列表，Dialog生成时做RAG检索用"""


class PPTProjectUpdate(BaseModel):
    """更新PPT项目"""
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    outline_text: Optional[str] = None
    theme: Optional[str] = Field(default=None, max_length=THEME_MAX_LENGTH)
    template_style: Optional[str] = None
    settings: Optional[dict] = None
    status: Optional[str] = None
    exported_file_url: Optional[str] = None
    exported_at: Optional[datetime] = None
    knowledge_library_ids: Optional[list[int]] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_style_fields(cls, values: object) -> object:
        return _normalize_project_style_payload(values)
    """用户选择的知识库ID列表"""


class ProjectSettingsUpdate(BaseModel):
    """更新项目设置"""
    description_generation_mode: Optional[str] = Field(default=None, pattern="^(auto|manual)$")
    description_extra_fields: Optional[list[str]] = None
    image_prompt_extra_fields: Optional[list[str]] = None
    extra_fields_config: Optional[list[dict]] = None
    detail_level: Optional[str] = Field(default=None, pattern="^(concise|default|detailed)$")
    theme: Optional[str] = Field(default=None, max_length=THEME_MAX_LENGTH)
    template_style: Optional[str] = None
    template_image_url: Optional[str] = None
    template_oss_key: Optional[str] = None
    aspect_ratio: Optional[str] = Field(default=None, pattern="^(1:1|4:3|16:9|3:4|9:16)$")
    image_resolution: Optional[str] = Field(default=None, pattern="^(1K|2K|4K)$")

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_style_fields(cls, values: object) -> object:
        return _normalize_project_style_payload(values)


class PPTProjectResponse(BaseModel):
    """PPT项目响应"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    creation_type: str
    outline_text: Optional[str]
    description_text: Optional[str] = None
    settings: dict
    theme: Optional[str]
    template_style: Optional[str]
    knowledge_library_ids: list[int]
    status: str
    exported_file_url: Optional[str]
    exported_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PPTProjectListItem(BaseModel):
    """PPT项目列表项（含摘要信息）"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    creation_type: str
    status: str
    template_style: Optional[str]
    created_at: datetime
    updated_at: datetime
    page_count: int = 0
    cover_image_url: Optional[str] = None

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
    renovation_status: Optional[str] = None
    renovation_error: Optional[str] = None
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
    parsed_outline: Optional[dict] = None
    parsed_content: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanningContextRefreshResponse(BaseModel):
    sections: dict
    planning_context_text: str
    partial: bool = False
    pending_reference_files: list[dict] = Field(default_factory=list)
    source_counts: dict = Field(default_factory=dict)
    last_generated_at: Optional[str] = None


class FileGenerationResponse(BaseModel):
    """文件生成一站式入口响应"""
    project_id: int
    task_id: str
    status: str = "processing"
    reference_file_id: Optional[int] = None


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


class PPTIntentSummaryResponse(BaseModel):
    topic: str = ""
    audience: str = ""
    goal: str = ""
    duration: str = ""
    constraints: str = ""
    style: str = ""
    interaction: str = ""
    extra: str = ""


class PPTIntentStateResponse(BaseModel):
    status: str
    confirmed: list[str] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)
    scores: dict[str, int] = Field(default_factory=dict)
    confidence: int = 0
    ready_for_confirmation: bool = False
    summary: str = ""
    intent_summary: PPTIntentSummaryResponse = Field(default_factory=PPTIntentSummaryResponse)
    round: int = 0
    confirmed_at: Optional[str] = None


class PPTIntentEnvelopeResponse(BaseModel):
    intent: PPTIntentStateResponse
    intent_summary: PPTIntentSummaryResponse


class PPTIntentConfirmResponse(BaseModel):
    status: str
    intent: PPTIntentStateResponse
    intent_summary: PPTIntentSummaryResponse


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


class EditImageSelectionBBox(BaseModel):
    """用户框选的编辑区域，坐标基于原图像素尺寸。"""
    x: float = Field(ge=0, description="选区左上角 x 坐标")
    y: float = Field(ge=0, description="选区左上角 y 坐标")
    width: float = Field(gt=0, description="选区宽度")
    height: float = Field(gt=0, description="选区高度")


class EditImageContext(BaseModel):
    """编辑图片的上下文图片"""
    use_template: bool = Field(default=False, description="是否使用模板图片")
    desc_image_urls: list[str] = Field(default_factory=list, description="描述中的图片URL列表")
    uploaded_image_ids: list[str] = Field(default_factory=list, description="上传的图片文件ID列表")


    selection_bbox: Optional[EditImageSelectionBBox] = None


# ============= Dialog Schemas =============

class GenerateOutlineRequest(BaseModel):
    """Dialog页面生成大纲请求"""
    content: Optional[str] = None
    """可选，用户补充输入"""


class GenerateOutlineStreamRequest(BaseModel):
    """流式生成大纲请求"""
    idea_prompt: Optional[str] = None
    planning_context_text: Optional[str] = None
    """可选，覆盖项目级的 idea_prompt"""
    language: str = Field(default="zh", description="输出语言")


class GenerateDescriptionsStreamRequest(BaseModel):
    """流式生成描述请求"""
    language: str = Field(default="zh", description="输出语言")
    detail_level: str = Field(default="default", description="详细程度：concise/default/detailed")
    page_ids: Optional[list[int]] = Field(default=None, description="可选：只生成这些页面")


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
