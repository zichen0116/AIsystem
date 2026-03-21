from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class QuestionPaperCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="试卷名称")
    subject: str = Field(default="", max_length=128)
    difficulty: str = Field(default="medium", max_length=20)
    questions: List[Any] = Field(..., min_length=1, description="题目列表（与生成接口返回一致）")


class QuestionPaperListItem(BaseModel):
    id: int
    title: str
    subject: str
    difficulty: str
    question_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionPaperDetail(BaseModel):
    id: int
    title: str
    subject: str
    difficulty: str
    questions: List[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionPaperListResponse(BaseModel):
    items: List[QuestionPaperListItem]


class QuestionPaperCreateResponse(BaseModel):
    paper: QuestionPaperDetail
