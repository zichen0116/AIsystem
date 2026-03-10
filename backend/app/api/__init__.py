"""
API 路由导出
"""
from fastapi import APIRouter
from app.api import auth, courseware, chat, knowledge, libraries
from app.api import html_upload, html_chat, html_export

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(courseware.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(libraries.router)

api_router.include_router(html_upload.router, prefix="/html", tags=["html"])
api_router.include_router(html_chat.router, prefix="/html", tags=["html"])
api_router.include_router(html_export.router, prefix="/html", tags=["html"])

__all__ = ["api_router"]
