# backend/app/schemas/rehearsal.py
from datetime import datetime

from pydantic import BaseModel, Field


# ---------- 请求 ----------

class RehearsalGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="zh-CN")
    enable_tts: bool = Field(default=True)
    voice: str = Field(default="Cherry")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class RehearsalSnapshotUpdate(BaseModel):
    playback_snapshot: dict = Field(..., description="{sceneIndex, actionIndex}")


# ---------- 响应 ----------

class RehearsalSceneResponse(BaseModel):
    id: int
    scene_order: int
    title: str
    scene_status: str
    slide_content: dict | None = None
    actions: list | None = None
    key_points: list | None = None
    original_page_number: int | None = None
    is_skipped: bool = False
    skip_reason: str | None = None
    page_image_url: str | None = None
    page_text: str | None = None
    script_text: str | None = None
    audio_url: str | None = None
    audio_status: str
    error_message: str | None = None

    model_config = {"from_attributes": True}


class RehearsalSessionSummary(BaseModel):
    id: int
    title: str
    topic: str
    source: str = "topic"
    status: str
    total_scenes: int
    total_pages: int | None = None
    original_file_name: str | None = None
    language: str
    created_at: datetime
    updated_at: datetime
    ready_count: int = 0
    failed_count: int = 0
    fallback_count: int = 0
    skipped_count: int = 0
    playable_count: int = 0

    model_config = {"from_attributes": True}


class RehearsalSessionDetail(BaseModel):
    id: int
    title: str
    topic: str
    source: str = "topic"
    status: str
    total_scenes: int
    total_pages: int | None = None
    original_file_url: str | None = None
    original_file_name: str | None = None
    converted_pdf_url: str | None = None
    playback_snapshot: dict | None = None
    language: str
    settings: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    ready_count: int = 0
    failed_count: int = 0
    fallback_count: int = 0
    skipped_count: int = 0
    playable_count: int = 0
    scenes: list[RehearsalSceneResponse]

    model_config = {"from_attributes": True}


class RehearsalUploadResponse(BaseModel):
    session_id: int
    status: str
    source: str = "upload"
    total_pages: int


class RehearsalSessionListResponse(BaseModel):
    sessions: list[RehearsalSessionSummary]
