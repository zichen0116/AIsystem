from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    context_file_id: Optional[str] = None  # 关联已上传的文件


class ChatResponse(BaseModel):
    message: str
    suggestions: Optional[List[str]] = None
