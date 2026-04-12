import io
from datetime import datetime, timezone

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

import app.main  # noqa: F401
import app.rehearsal_tasks as rehearsal_tasks
from app.models.rehearsal import RehearsalScene, RehearsalSession
from app.schemas.rehearsal import RehearsalSessionDetail
from app.services import rehearsal_upload_service as upload_svc


class FakeDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, obj):
        if getattr(obj, 'id', None) is None:
            obj.id = len(self.added) + 1
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed.append(obj)


class FakeResult:
    def __init__(self, session):
        self._session = session

    def scalar_one_or_none(self):
        return self._session


class FakeAsyncSession:
    def __init__(self, session):
        self.session = session
        self.commit_calls = 0
        self.rollback_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt):
        return FakeResult(self.session)

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1



def make_upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({'content-type': content_type}),
    )



def make_session(filename: str = 'lesson.pptx') -> RehearsalSession:
    session = RehearsalSession(
        id=11,
        user_id=7,
        title='上传预演',
        topic='上传预演',
        source='upload',
        status='processing',
        total_scenes=0,
        language='zh-CN',
        original_file_url='https://oss.example/rehearsal-upload/7/file.pptx',
        original_file_name=filename,
        converted_pdf_url=None,
        total_pages=3,
        error_message=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.scenes = []
    return session


@pytest.mark.asyncio
async def test_create_rehearsal_upload_session_dispatches_background_processing(monkeypatch):
    db = FakeDB()
    file = make_upload('lesson.pdf', b'%PDF-1.4 fake rehearsal file', 'application/pdf')
    dispatched = []

    monkeypatch.setattr(upload_svc, 'count_pages_for_upload', lambda path, ext: 12)

    async def fake_upload_file(upload_file, user_id: int, prefix: str = 'knowledge'):
        return {
            'url': 'https://oss.example/rehearsal-upload/7/lesson.pdf',
            'file_name': 'lesson.pdf',
            'file_type': 'pdf',
        }

    monkeypatch.setattr(upload_svc.oss_service, 'upload_file', fake_upload_file)
    monkeypatch.setattr(
        upload_svc,
        'trigger_rehearsal_processing_task',
        lambda session_id, user_id: dispatched.append((session_id, user_id)),
        raising=False,
    )

    result = await upload_svc.create_rehearsal_upload_session(db, 7, file)

    assert result['session_id'] == 1
    assert dispatched == [(1, 7)]



def test_process_rehearsal_upload_session_marks_failed_on_conversion_error(monkeypatch):
    session = make_session('lesson.pptx')
    fake_async_db = FakeAsyncSession(session)

    monkeypatch.setattr(rehearsal_tasks, 'AsyncSessionLocal', lambda: fake_async_db, raising=False)

    async def fake_process(db, session_obj):
        raise RuntimeError('PPT 转换失败: LibreOffice unavailable')

    monkeypatch.setattr(rehearsal_tasks, 'process_rehearsal_session_assets', fake_process, raising=False)

    rehearsal_tasks.process_rehearsal_upload_session(11, 7)

    assert session.status == 'failed'
    assert '转换失败' in (session.error_message or '')
    assert fake_async_db.commit_calls >= 1



def test_process_rehearsal_upload_session_persists_assets_for_session_detail(monkeypatch):
    session = make_session('lesson.pdf')
    fake_async_db = FakeAsyncSession(session)

    monkeypatch.setattr(rehearsal_tasks, 'AsyncSessionLocal', lambda: fake_async_db, raising=False)

    async def fake_process(db, session_obj):
        session_obj.converted_pdf_url = 'https://oss.example/rehearsal-pdf/7/file.pdf'
        scene = RehearsalScene(
            id=101,
            session_id=session_obj.id,
            scene_order=0,
            title='Page 1',
            scene_status='ready',
            original_page_number=1,
            is_skipped=False,
            page_image_url='https://oss.example/rehearsal-pages/7/page-1.png',
            page_text='# Page 1',
            audio_status='pending',
        )
        session_obj.scenes = [scene]
        session_obj.total_scenes = 1
        session_obj.total_pages = 1
        return {'scene_count': 1, 'converted_pdf_url': session_obj.converted_pdf_url}

    monkeypatch.setattr(rehearsal_tasks, 'process_rehearsal_session_assets', fake_process, raising=False)

    rehearsal_tasks.process_rehearsal_upload_session(11, 7)

    detail = RehearsalSessionDetail.model_validate(session)
    assert session.status == 'ready'
    assert detail.converted_pdf_url == 'https://oss.example/rehearsal-pdf/7/file.pdf'
    assert detail.scenes[0].page_image_url == 'https://oss.example/rehearsal-pages/7/page-1.png'
    assert detail.scenes[0].page_text == '# Page 1'
