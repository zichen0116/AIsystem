"""
枚举类型定义
"""
from enum import Enum


class CoursewareType(str, Enum):
    """课件类型"""
    PPT = "PPT"
    DOCX = "DOCX"
    GAME = "GAME"


class CoursewareStatus(str, Enum):
    """课件状态"""
    PLANNING = "PLANNING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChatRole(str, Enum):
    """聊天角色"""
    USER = "user"
    ASSISTANT = "assistant"


class FileType(str, Enum):
    """文件类型"""
    PDF = "pdf"
    WORD = "word"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
