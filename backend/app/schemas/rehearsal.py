# backend/app/schemas/rehearsal.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


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
    audio_status: str
    error_message: str | None = None

    model_config = {"from_attributes": True}


class RehearsalSessionSummary(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    total_scenes: int
    language: str
    created_at: datetime
    updated_at: datetime
    # 汇总信息
    ready_count: int = 0
    failed_count: int = 0

    model_config = {"from_attributes": True}


class RehearsalSessionDetail(BaseModel):
    id: int
    title: str
    topic: str
    status: str
    total_scenes: int
    playback_snapshot: dict | None = None
    language: str
    settings: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    scenes: list[RehearsalSceneResponse]

    model_config = {"from_attributes": True}


class RehearsalSessionListResponse(BaseModel):
    sessions: list[RehearsalSessionSummary]
