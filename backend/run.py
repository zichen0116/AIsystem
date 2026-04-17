"""
应用启动脚本
开发环境使用: python run.py
"""
import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from app.core.config import settings
from app.core.logging_setup import configure_logging

configure_logging(settings.DEBUG)


def main():
    """启动应用"""
    print("=" * 50)
    print("多模态 AI 互动式教学智能体")
    print("=" * 50)
    print(f"启动地址: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
