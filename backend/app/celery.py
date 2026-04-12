"""
Celery 异步任务配置
"""
from celery import Celery
import os

# 配置 Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_teaching",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks", "app.rehearsal_tasks", "app.generators.ppt.celery_tasks"]
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 分钟超时
    task_soft_time_limit=25 * 60,
    task_routes={
        "app.tasks.*": {"queue": "default"},
        "banana-slides.*": {"queue": "default"},
        "app.generators.ppt.celery_tasks.*": {"queue": "default"},
    },
)
