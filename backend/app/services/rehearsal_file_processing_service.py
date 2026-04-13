import os
import shutil
import tempfile
from pathlib import Path

from app.generators.ppt.renovation_service import RenovationService
from app.models.rehearsal import RehearsalScene, RehearsalSession
from app.services import oss_service
from app.services.rehearsal_upload_service import normalize_upload_extension

PDF_ASSET_PREFIX = 'rehearsal-pdf'
PAGE_IMAGE_PREFIX = 'rehearsal-pages'
BACK_COVER_KEYWORDS = ('谢谢', 'thank you', 'q&a', 'qa', 'questions', '联系方式', 'contact us')


async def _upload_local_asset(file_path: str, user_id: int, prefix: str) -> str:
    ext = Path(file_path).suffix.lower().lstrip('.') or 'bin'
    with open(file_path, 'rb') as handle:
        content = handle.read()
    return await oss_service.upload_bytes(content, ext, user_id, prefix=prefix)



def _get_or_create_scene(session: RehearsalSession, scene_order: int) -> RehearsalScene:
    for scene in session.scenes or []:
        if scene.scene_order == scene_order:
            return scene

    scene = RehearsalScene(
        session_id=session.id,
        scene_order=scene_order,
        title=f'第{scene_order + 1}页',
        scene_status='pending',
        audio_status='pending',
    )
    session.scenes.append(scene)
    return scene



def _classify_skipped_page(page_text: str | None) -> tuple[bool, str | None]:
    normalized = (page_text or '').strip()
    if not normalized:
        return True, '空白页'

    lowered = normalized.lower()
    if any(keyword in lowered for keyword in BACK_COVER_KEYWORDS):
        return True, '封底页'

    return False, None


async def process_rehearsal_session_assets(db, session: RehearsalSession) -> dict:
    if not session.original_file_url:
        raise ValueError('原始文件地址不能为空')

    ext = normalize_upload_extension(session.original_file_name, None)
    if ext not in {'pdf', 'ppt', 'pptx'}:
        raise ValueError('文件类型不支持')

    renovation_service = RenovationService()
    source_path = oss_service.download_to_temp(session.original_file_url)
    work_dir = tempfile.mkdtemp(prefix='rehearsal_processing_')

    try:
        pdf_path = source_path
        if ext in {'ppt', 'pptx'}:
            pdf_path = renovation_service.convert_to_pdf(source_path, ext)
            session.converted_pdf_url = await _upload_local_asset(pdf_path, session.user_id, PDF_ASSET_PREFIX)
        else:
            session.converted_pdf_url = session.converted_pdf_url or session.original_file_url

        page_pdf_paths = await renovation_service.split_pdf_to_pages(pdf_path, work_dir)
        page_image_paths = renovation_service.render_pdf_to_images(pdf_path, work_dir)

        for index, page_pdf_path in enumerate(page_pdf_paths):
            scene = _get_or_create_scene(session, index)
            scene.session_id = session.id
            scene.scene_order = index
            scene.original_page_number = index + 1
            scene.title = scene.title or f'第{index + 1}页'
            scene.is_skipped = False
            scene.skip_reason = None
            scene.error_message = None
            scene.scene_status = 'pending'

            page_image_path = page_image_paths[index] if index < len(page_image_paths) else None
            if page_image_path and os.path.exists(page_image_path):
                scene.page_image_url = await _upload_local_asset(page_image_path, session.user_id, PAGE_IMAGE_PREFIX)

            page_text, parse_error = await renovation_service.parse_page_markdown(
                page_pdf_path,
                Path(page_pdf_path).name,
            )
            scene.page_text = page_text
            scene.error_message = parse_error

            if parse_error and scene.page_image_url:
                scene.scene_status = 'fallback'
            elif parse_error:
                scene.scene_status = 'failed'
            else:
                is_skipped, skip_reason = _classify_skipped_page(page_text)
                if is_skipped:
                    scene.scene_status = 'skipped'
                    scene.is_skipped = True
                    scene.skip_reason = skip_reason
                else:
                    scene.scene_status = 'ready'

            if getattr(scene, 'id', None) is None and hasattr(db, 'add'):
                db.add(scene)

        session.total_scenes = len(page_pdf_paths)
        session.total_pages = len(page_pdf_paths)
        await db.flush()

        return {
            'session_id': session.id,
            'scene_count': len(page_pdf_paths),
            'converted_pdf_url': session.converted_pdf_url,
        }
    finally:
        try:
            if source_path and os.path.exists(source_path):
                os.remove(source_path)
        except OSError:
            pass
        shutil.rmtree(work_dir, ignore_errors=True)
