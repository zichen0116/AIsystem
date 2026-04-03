"""
PPT生成模块（banana-slides集成）

路由挂载: /api/v1/ppt/
"""
from .banana_models import (
    PPTProject,
    PPTPage,
    PPTTask,
    PPTMaterial,
    PPTReferenceFile,
    PPTSession,
    UserTemplate,
    PageImageVersion,
)
from .banana_schemas import (
    PPTProjectCreate,
    PPTProjectUpdate,
    PPTProjectResponse,
    PPTPageResponse,
    PPTTaskResponse,
    PPTMaterialResponse,
    PPTReferenceFileResponse,
    PPTSessionResponse,
    ChatMessageRequest,
    PageReorderRequest,
    ProjectSettingsUpdate,
    UserTemplateCreate,
    UserTemplateUpdate,
    UserTemplateResponse,
    PageImageVersionResponse,
    RefineOutlineRequest,
    RefineDescriptionsRequest,
    EditImageRequest,
    GenerateOutlineRequest,
    ExportRequest,
    ExportTaskResponse,
)
from .banana_routes import router as ppt_router
from .banana_providers import (
    TextProvider,
    ImageProvider,
    GenAITextProvider,
    GenAIImageProvider,
    OpenAITextProvider,
    OpenAIImageProvider,
    AnthropicTextProvider,
    get_text_provider,
    get_image_provider,
    get_text_provider_singleton,
    get_image_provider_singleton,
)

__all__ = [
    # Router
    "ppt_router",
    # Providers
    "TextProvider",
    "ImageProvider",
    "GenAITextProvider",
    "GenAIImageProvider",
    "OpenAITextProvider",
    "OpenAIImageProvider",
    "AnthropicTextProvider",
    "get_text_provider",
    "get_image_provider",
    "get_text_provider_singleton",
    "get_image_provider_singleton",
    # Models
    "PPTProject",
    "PPTPage",
    "PPTTask",
    "PPTMaterial",
    "PPTReferenceFile",
    "PPTSession",
    "UserTemplate",
    "PageImageVersion",
    # Schemas - Project
    "PPTProjectCreate",
    "PPTProjectUpdate",
    "PPTProjectResponse",
    "ProjectSettingsUpdate",
    # Schemas - Page
    "PPTPageResponse",
    "PageReorderRequest",
    # Schemas - Task
    "PPTTaskResponse",
    # Schemas - Material
    "PPTMaterialResponse",
    # Schemas - Reference File
    "PPTReferenceFileResponse",
    # Schemas - Session
    "PPTSessionResponse",
    "ChatMessageRequest",
    # Schemas - Template
    "UserTemplateCreate",
    "UserTemplateUpdate",
    "UserTemplateResponse",
    # Schemas - Image Version
    "PageImageVersionResponse",
    # Schemas - Refine
    "RefineOutlineRequest",
    "RefineDescriptionsRequest",
    "EditImageRequest",
    # Schemas - Dialog
    "GenerateOutlineRequest",
    # Schemas - Export
    "ExportRequest",
    "ExportTaskResponse",
]
