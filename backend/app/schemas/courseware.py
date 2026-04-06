"""
课件相关 Schema
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from app.models.enums import CoursewareType, CoursewareStatus


class CoursewareBase(BaseModel):
    """课件基础字段"""
    title: str = Field(..., min_length=1, max_length=255)
    type: CoursewareType = Field(default=CoursewareType.PPT)


class CoursewareCreate(CoursewareBase):
    """创建课件请求"""
    pass


class CoursewareUpdate(BaseModel):
    """更新课件请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content_json: Optional[dict] = None
    status: Optional[str] = None
    file_url: Optional[str] = None
    tags: Optional[str] = Field(None, max_length=500)
    remark: Optional[str] = None
    file_type: Optional[str] = None

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v):
        if v is not None and v not in ("pdf", "ppt", "word", "video", "image"):
            raise ValueError("file_type must be one of: pdf, ppt, word, video, image")
        return v


class SlideContent(BaseModel):
    """幻灯片内容（Master Lesson JSON 结构）"""
    title: str
    content: str
    image_prompt: str | None = None
    notes: str | None = None


class LessonPlanDetails(BaseModel):
    """教案细节"""
    objectives: list[str] = []
    duration: str | None = None
    materials: list[str] = []
    assessment: str | None = None


class InteractiveElement(BaseModel):
    """互动元素"""
    type: str  # "quiz", "game", "discussion"
    question: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None
    game_logic: dict | None = None


class MasterLessonJSON(BaseModel):
    """
    Master Lesson JSON 协议

    AI 生成的标准化课件结构，包含：
    - slides: 幻灯片数组
    - lesson_plan_details: 教案细节
    - interactive_elements: 互动元素
    """
    title: str
    slides: list[SlideContent]
    lesson_plan_details: LessonPlanDetails
    interactive_elements: list[InteractiveElement] = []


class CoursewareResponse(CoursewareBase):
    """课件响应"""
    id: int
    user_id: int
    content_json: dict | None
    status: CoursewareStatus
    file_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CoursewareListResponse(BaseModel):
    """课件列表响应"""
    items: list[CoursewareResponse]
    total: int


class CoursewareAggregateItem(BaseModel):
    id: str                           # prefixed: ppt_123, lp_456, up_789
    source_type: str                  # ppt / lesson_plan / uploaded
    name: str
    file_type: str                    # pdf / ppt / word / video / image
    file_size: Optional[int] = None   # bytes
    status: Optional[str] = None
    cover_image: Optional[str] = None
    updated_at: datetime
    source_id: int                    # raw DB id
    tags: Optional[str] = None
    remark: Optional[str] = None
    file_url: Optional[str] = None
    page_count: Optional[int] = None  # only for PPT


class CoursewareAggregateResponse(BaseModel):
    items: list[CoursewareAggregateItem]
    total: int
