"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置"""

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/ai_teaching"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@db:5432/ai_teaching"

    # Redis
    REDIS_URL: str = "redis://cache:6379/0"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "chroma_data"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ========== 阿里云百炼 API ==========
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"
    EMBEDDING_MODEL: str = "tongyi-embedding-vision-flash"
    RERANK_MODEL: str = "qwen3-vl-rerank"

    # ========== 阿里云 OSS ==========
    OSS_ENDPOINT: str = ""
    OSS_BUCKET: str = ""
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""

    # ========== 其他 API（可选） ==========
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ========== 阿里云 ASR 语音识别 ==========
    ASR_MODEL: str = "qwen3-asr-flash"

    # ========== 阿里云 Vision 视觉理解 ==========
    VISION_MODEL: str = "qwen-vl-plus"

    # ========== Tavily 网络搜索 ==========
    TAVILY_API_KEY: str = ""

    # 应用
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # ========== html 小游戏（OpenAI 兼容接口）==========
    HTML_LLM_API_KEY: str = ""
    HTML_LLM_BASE_URL: str = ""
    HTML_LLM_MODEL: str = ""
    HTML_UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


settings = get_settings()
