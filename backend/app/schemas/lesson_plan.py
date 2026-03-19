from typing import Optional

from pydantic import BaseModel, ConfigDict


# --- Request schemas ---

class LessonPlanGenerateRequest(BaseModel):
    query: str
    library_ids: list[int] = []
    file_ids: list[int] = []
    session_id: Optional[str] = None


class LessonPlanModifyRequest(BaseModel):
    lesson_plan_id: int
    instruction: str
    current_content: str
    file_ids: list[int] = []
    library_ids: list[int] = []


class LessonPlanSaveRequest(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None


class LessonPlanExportRequest(BaseModel):
    content: str
    title: str = "教案"


# --- Response schemas ---

class LessonPlanInfo(BaseModel):
    id: int
    session_id: str
    title: str
    content: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class MessageInfo(BaseModel):
    role: str
    content: str


class FileInfo(BaseModel):
    id: int
    filename: str


class LessonPlanLatestResponse(BaseModel):
    lesson_plan: Optional[LessonPlanInfo] = None
    messages: list[MessageInfo] = []
    files: list[FileInfo] = []


class LessonPlanSaveResponse(BaseModel):
    id: int
    updated_at: str


class LessonPlanUploadResponse(BaseModel):
    file_id: int
    filename: str


class LessonPlanListItem(BaseModel):
    id: int
    session_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    model_config = ConfigDict(from_attributes=True)


class LessonPlanListResponse(BaseModel):
    items: list[LessonPlanListItem]
    total: int


class ChatMessageInfo(BaseModel):
    role: str
    content: str
    created_at: str


class LessonPlanMessagesResponse(BaseModel):
    messages: list[ChatMessageInfo]
