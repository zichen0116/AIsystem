import asyncio
import logging

from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.celery import celery_app
from app.core.database import AsyncSessionLocal
from app.models.rehearsal import RehearsalSession
from app.services.rehearsal_file_processing_service import process_rehearsal_session_assets
from app.services.rehearsal_session_service import compute_session_status
from app.services.rehearsal_upload_generation_service import generate_upload_session_narration

logger = logging.getLogger(__name__)


class RehearsalUploadTask(Task):
    """Callback-enabled base task for rehearsal upload processing."""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info('Rehearsal upload task %s completed: %s', task_id, retval)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error('Rehearsal upload task %s failed: %s', task_id, exc)


async def _run_rehearsal_upload_processing(session_id: int, user_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RehearsalSession)
            .options(selectinload(RehearsalSession.scenes))
            .where(RehearsalSession.id == session_id, RehearsalSession.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            logger.warning(
                'Rehearsal upload session missing: session_id=%s, user_id=%s',
                session_id,
                user_id,
            )
            return {'status': 'missing', 'session_id': session_id}

        try:
            payload = await process_rehearsal_session_assets(db, session)
            generation_payload = await generate_upload_session_narration(db, session)
            session.status = compute_session_status(session)
            session.error_message = None
            await db.commit()
            return {
                'status': session.status,
                'session_id': session.id,
                'scene_count': payload.get('scene_count', 0),
                'converted_pdf_url': session.converted_pdf_url,
                'generated_scene_count': generation_payload.get('generated_scene_count', 0),
            }
        except Exception as exc:
            session.status = 'failed'
            session.error_message = str(exc)
            await db.commit()
            logger.exception(
                'Rehearsal upload processing failed: session_id=%s',
                session_id,
            )
            return {
                'status': 'failed',
                'session_id': session_id,
                'error_message': session.error_message,
            }


@celery_app.task(
    bind=True,
    base=RehearsalUploadTask,
    name='app.rehearsal_tasks.process_rehearsal_upload_session',
)
def process_rehearsal_upload_session(self, session_id: int, user_id: int):
    """Process uploaded rehearsal files in the background."""
    logger.info(
        'Starting rehearsal upload processing: session_id=%s, user_id=%s',
        session_id,
        user_id,
    )
    return asyncio.run(_run_rehearsal_upload_processing(session_id, user_id))
