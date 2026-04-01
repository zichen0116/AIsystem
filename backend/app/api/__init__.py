"""
API 路由导出
"""
from fastapi import APIRouter
from app.api import auth, courseware, chat, knowledge, libraries, data_analysis, digital_human
from app.api import html_upload, html_chat, html_export
from app.api import lesson_plan, question_generate, question_paper, mindmap, resource_search, upload

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(digital_human.router)
api_router.include_router(courseware.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(libraries.router)
api_router.include_router(data_analysis.router)

api_router.include_router(html_upload.router, prefix="/html", tags=["html"])
api_router.include_router(html_chat.router, prefix="/html", tags=["html"])
api_router.include_router(html_export.router, prefix="/html", tags=["html"])
api_router.include_router(lesson_plan.router)
api_router.include_router(question_generate.router)
api_router.include_router(question_paper.router)
api_router.include_router(mindmap.router)
api_router.include_router(resource_search.router)
api_router.include_router(upload.router)

__all__ = ["api_router"]
