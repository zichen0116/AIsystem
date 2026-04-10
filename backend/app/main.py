"""
FastAPI 应用入口
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.core.logging_setup import configure_logging
# 导入所有模型，确保 Base.metadata 包含所有表
from app.models import *  # noqa: F401, F403
from app.api import api_router

configure_logging(settings.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化数据库
    await init_db()
    yield
    # 关闭时：清理资源


# 创建 FastAPI 应用
app = FastAPI(
    title="多模态 AI 互动式教学智能体",
    description="服务外包大赛 A04 赛题后端 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/doc.html",
    redoc_url="/redoc.html"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")

# ==================== 静态文件映射 ====================
# 挂载 backend/media 目录，用于下载 PPT/图表/解析图片等
# 访问路径: http://host:port/media/...
media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
if os.path.exists(media_dir):
    app.mount("/media", StaticFiles(directory=media_dir), name="media")
    print(f"静态文件映射: /media -> {media_dir}")
else:
    print(f"警告: media 目录不存在: {media_dir}")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
