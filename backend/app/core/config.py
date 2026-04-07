"""
应用配置管理
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings,SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import os


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = BACKEND_ROOT / ".env"


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

 # SiliconFlow / Docmee / Unsplash 配置
    siliconflow_api_key: str | None = None
    docmee_api_key: str | None = None
    docmee_trust_env: bool = False
    docmee_request_timeout_seconds: int = 60
    docmee_generate_pptx_timeout_seconds: int = 600
    docmee_pptx_poll_attempts: int = 8
    docmee_pptx_poll_delay_seconds: float = 2.0
    unsplash_access_key: str | None = None


    # 使用 model_config 替代 class Config，并设置 extra="ignore"
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    # ========== 阿里云 OSS ==========
    OSS_ENDPOINT: str = ""
    OSS_BUCKET: str = ""
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""

    # ========== Banana-slides AI 配置（PPT生成服务）==========
    # AI Provider SDK 格式：gemini（默认）/ openai / anthropic
    AI_PROVIDER_FORMAT: str = "gemini"
    # Gemini
    GOOGLE_API_KEY: str = ""
    GOOGLE_API_BASE: str = "https://generativelanguage.googleapis.com"
    GENAI_TIMEOUT: float = 300.0
    GENAI_MAX_RETRIES: int = 2
    # 各模型选择（可选，默认用 AI_PROVIDER_FORMAT 对应的模型）
    TEXT_MODEL: str = ""
    IMAGE_MODEL: str = ""
    IMAGE_CAPTION_MODEL: str = ""
    # 国内厂商 API Key（按需填）
    DOUBAO_API_KEY: str = ""
    QWEN_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    GLM_API_KEY: str = ""
    SILICONFLOW_API_KEY: str = ""
    # 并发控制
    MAX_DESCRIPTION_WORKERS: int = 5
    MAX_IMAGE_WORKERS: int = 8
    # MinerU 文档解析（文件生成路径）
    MINERU_TOKEN: str = ""
    MINERU_API_BASE: str = "https://mineru.net"
    # 可编辑 PPTX 导出（文字提取）
    BAIDU_API_KEY: str = ""
    # 输出语言：zh / ja / en / auto
    OUTPUT_LANGUAGE: str = "zh"

    # ========== 短信服务（国阳云） ==========
    SMS_APPCODE: str = ""

    # ========== 其他 API（可选） ==========
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ========== 阿里云 ASR 语音识别 ==========
    ASR_MODEL: str = "qwen3-asr-flash"

    # ========== 阿里云 Vision 视觉理解 ==========
    VISION_MODEL: str = "qwen-vl-plus"

    # ========== Tavily 网络搜索 ==========
    TAVILY_API_KEY: str = ""

    # ========== Dify 工作流（资源推荐等）==========
    # 云端默认 https://api.dify.ai/v1 ；自建请改为你的部署地址（不要末尾多余斜杠）
    DIFY_API_BASE_URL: str = "https://api.dify.ai/v1"
    # Dify 应用「访问 API」中的 API Key（勿提交到公开仓库）
    DIFY_RESOURCE_WORKFLOW_API_KEY: str = ""

    # ========== Neo4j 图数据库 ==========
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # ========== LightRAG ==========
    # 动态绝对路径，锚定 backend/ 目录，避免 CWD 差异导致路径分裂
    LIGHTRAG_WORKING_DIR: str = str(
        Path(__file__).resolve().parent.parent.parent / "lightrag_data"
    )

    # 应用
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_flag(cls, value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    # ========== html 小游戏（OpenAI 兼容接口）==========
    HTML_LLM_API_KEY: str = ""
    HTML_LLM_BASE_URL: str = ""
    HTML_LLM_MODEL: str = ""
    HTML_UPLOAD_DIR: str = "uploads"

    # ========== 邮件服务（QQ SMTP）==========
    EMAIL_SMTP_HOST: str = "smtp.qq.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USER: str = ""
    EMAIL_SMTP_PASSWORD: str = ""
    EMAIL_FROM_NAME: str = "AI教学平台"

    # ========== 讯飞 AI 虚拟人（在线驱动 / VMS）==========
    # 控制台「在线虚拟人驱动」应用：APPID、APIKey、APISecret；形象 ID 在形象列表中查看
    # Web SDK：https://www.xfyun.cn/doc/tts/virtual_human/Web-SDK.html
    # Web API：https://static.xfyun.cn/doc/tts/virtual_human/API.html
    IFLYTEK_VMS_APP_ID: str = ""
    IFLYTEK_VMS_API_KEY: str = ""
    IFLYTEK_VMS_API_SECRET: str = ""
    IFLYTEK_VMS_SERVICE_ID: str = ""
    IFLYTEK_VMS_DEFAULT_AVATAR_ID: str = "111283001"
    IFLYTEK_VMS_HOST: str = "vms.cn-huadong-1.xf-yun.com"
    IFLYTEK_VMS_DEFAULT_WIDTH: int = 1280
    IFLYTEK_VMS_DEFAULT_HEIGHT: int = 720
    IFLYTEK_VMS_STREAM_PROTOCOL: str = "xrtc"

    # Avatar Platform（avatar-sdk-web / 交互）——与 VMS 老版 Web SDK 不同
    # Demo：wss://avatar.cn-huadong-1.xf-yun.com/v1/interact ，需 sceneId（控制台「接口服务」）
    IFLYTEK_AVATAR_SERVER_URL: str = "wss://avatar.cn-huadong-1.xf-yun.com/v1/interact"
    IFLYTEK_AVATAR_SCENE_ID: str = ""
    # Avatar SDK setGlobalParams.tts.vcn 必填，参见讯飞发音人列表（如 x4_xiaoxuan）
    IFLYTEK_AVATAR_TTS_VCN: str = "x4_xiaoxuan"

    # ========== 数据分析（Excel -> 图表）==========
    # 上传的 Excel 存放目录（相对于 backend/ 运行目录）
    DATA_ANALYSIS_UPLOAD_DIR: str = "media/data_analysis/uploads"
    # 生成的图表与报告目录（相对于 backend/ 运行目录）
    DATA_ANALYSIS_OUTPUT_DIR: str = "media/data_analysis/outputs"
    # 可选：指定 Matplotlib 中文字体文件路径（ttf/ttc/otf）
    # 例如 Windows: C:/Windows/Fonts/msyh.ttc
    DATA_ANALYSIS_FONT_PATH: str = ""

    #class Config:
    #    env_file = ".env"
    #    env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


settings = get_settings()
