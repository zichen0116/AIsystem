import os
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.generators.ppt.renovation_service import RenovationService
from app.models.rehearsal import RehearsalSession
from app.services import oss_service

MAX_REHEARSAL_UPLOAD_SIZE = 50 * 1024 * 1024
MAX_REHEARSAL_UPLOAD_PAGES = 30
ALLOWED_REHEARSAL_UPLOAD_EXTENSIONS = {'pdf', 'ppt', 'pptx'}
ALLOWED_REHEARSAL_UPLOAD_MIME_TYPES = {
    'application/pdf': 'pdf',
    'application/vnd.ms-powerpoint': 'ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
}



def normalize_upload_extension(filename: str | None, content_type: str | None) -> str:
    ext = Path(filename or '').suffix.lower().lstrip('.')
    if ext:
        return ext
    return ALLOWED_REHEARSAL_UPLOAD_MIME_TYPES.get((content_type or '').lower(), '')



def count_pdf_pages(file_path: str) -> int:
    try:
        import fitz  # type: ignore
    except ModuleNotFoundError:
        from PyPDF2 import PdfReader

        with open(file_path, 'rb') as handle:
            return len(PdfReader(handle).pages)

    with fitz.open(file_path) as doc:  # type: ignore[attr-defined]
        return len(doc)



def count_pages_for_upload(file_path: str, ext: str) -> int:
    if ext == 'pdf':
        return count_pdf_pages(file_path)

    if ext == 'pptx':
        from pptx import Presentation

        presentation = Presentation(file_path)
        return len(presentation.slides)

    if ext == 'ppt':
        renovation_service = RenovationService()
        pdf_path = renovation_service.convert_to_pdf(file_path, ext)
        return count_pdf_pages(pdf_path)

    raise ValueError('文件类型不支持')



def trigger_rehearsal_processing_task(session_id: int, user_id: int) -> None:
    from app.rehearsal_tasks import process_rehearsal_upload_session

    process_rehearsal_upload_session.delay(session_id, user_id)


async def create_rehearsal_upload_session(db, user_id: int, file: UploadFile) -> dict:
    ext = normalize_upload_extension(file.filename, file.content_type)
    content_type = (file.content_type or '').lower()
    if ext not in ALLOWED_REHEARSAL_UPLOAD_EXTENSIONS or content_type not in ALLOWED_REHEARSAL_UPLOAD_MIME_TYPES:
        raise ValueError('文件类型不支持')

    content = await file.read()
    if len(content) > MAX_REHEARSAL_UPLOAD_SIZE:
        raise ValueError('文件大小超过50MB')

    tmp_dir = tempfile.mkdtemp(prefix='rehearsal_upload_')
    tmp_path = os.path.join(tmp_dir, file.filename or f'upload.{ext}')

    try:
        with open(tmp_path, 'wb') as handle:
            handle.write(content)

        try:
            page_count = count_pages_for_upload(tmp_path, ext)
        except Exception as exc:  # pragma: no cover - defensive translation
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError(f'文件页数检测失败: {exc}') from exc

        if page_count > MAX_REHEARSAL_UPLOAD_PAGES:
            raise ValueError('文件页数超过30页上限')

        await file.seek(0)
        oss_result = await oss_service.upload_file(file, user_id, prefix='rehearsal-upload')

        title = Path(file.filename or '上传预演').stem or '上传预演'
        original_url = oss_result['url']
        session = RehearsalSession(
            user_id=user_id,
            title=title,
            topic=title,
            source='upload',
            status='processing',
            total_scenes=0,
            language='zh-CN',
            original_file_url=original_url,
            original_file_name=oss_result['file_name'],
            converted_pdf_url=original_url if ext == 'pdf' else None,
            total_pages=page_count,
            settings={'enableTTS': True, 'voice': 'Cherry', 'speed': 1.0},
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        trigger_rehearsal_processing_task(session.id, user_id)

        return {
            'session_id': session.id,
            'status': 'uploaded',
            'source': 'upload',
            'total_pages': page_count,
        }
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass
