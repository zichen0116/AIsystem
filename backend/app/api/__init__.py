"""
API 路由导出
"""
from fastapi import APIRouter
from app.api import auth, courseware, chat, knowledge

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(courseware.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)

__all__ = ["api_router"]
