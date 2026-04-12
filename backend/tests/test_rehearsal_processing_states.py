from pathlib import Path
from types import SimpleNamespace

import pytest

import app.main  # noqa: F401
from app.models.rehearsal import RehearsalSession
from app.services import rehearsal_file_processing_service as file_svc
from app.services.rehearsal_session_service import compute_session_status


class FakeDB:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, obj):
        if getattr(obj, 'id', None) is None:
            obj.id = len(self.added) + 1
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


class FakeRenovationService:
    def __init__(self, *, pdf_path, page_paths, image_paths, parse_results):
        self._pdf_path = pdf_path
        self._page_paths = page_paths
        self._image_paths = image_paths
        self._parse_results = parse_results

    def convert_to_pdf(self, file_path: str, file_ext: str) -> str:
        raise AssertionError('convert_to_pdf should not run in these tests')

    async def split_pdf_to_pages(self, pdf_path: str, output_dir: str) -> list[str]:
        return [str(path) for path in self._page_paths]

    def render_pdf_to_images(self, pdf_path: str, output_dir: str) -> list[str | None]:
        return [str(path) if path else None for path in self._image_paths]

    async def parse_page_markdown(self, page_pdf_path: str, filename: str):
        return self._parse_results[filename]


class SessionStub(SimpleNamespace):
    @property
    def ready_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == 'ready')

    @property
    def fallback_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == 'fallback')

    @property
    def skipped_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == 'skipped' or scene.is_skipped)

    @property
    def failed_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == 'failed')

    @property
    def playable_count(self) -> int:
        return self.ready_count + self.fallback_count


def make_session(filename: str) -> RehearsalSession:
    session = RehearsalSession(
        user_id=7,
        title='上传预演',
        topic='上传预演',
        source='upload',
        status='processing',
        total_scenes=0,
        language='zh-CN',
        original_file_url='https://oss.example/rehearsal-upload/7/lesson.pdf',
        original_file_name=filename,
        converted_pdf_url='https://oss.example/rehearsal-upload/7/lesson.pdf',
    )
    session.id = 11
    session.scenes = []
    return session


@pytest.mark.asyncio
async def test_process_rehearsal_session_assets_marks_blank_page_as_skipped(tmp_path, monkeypatch):
    db = FakeDB()
    pdf_path = tmp_path / 'lesson.pdf'
    page_pdf = tmp_path / 'page_1.pdf'
    page_png = tmp_path / 'page_1.png'
    pdf_path.write_bytes(b'%PDF-1.4 pdf')
    page_pdf.write_bytes(b'%PDF-1.4 page1')
    page_png.write_bytes(b'png-1')

    monkeypatch.setattr(file_svc.oss_service, 'download_to_temp', lambda url: str(pdf_path))

    async def fake_upload_bytes(content: bytes, ext: str, user_id: int, prefix: str = 'rehearsal-audio') -> str:
        return f'https://oss.example/{prefix}/page-1.{ext}'

    monkeypatch.setattr(file_svc.oss_service, 'upload_bytes', fake_upload_bytes)
    monkeypatch.setattr(
        file_svc,
        'RenovationService',
        lambda: FakeRenovationService(
            pdf_path=str(pdf_path),
            page_paths=[page_pdf],
            image_paths=[page_png],
            parse_results={page_pdf.name: ('', None)},
        ),
    )

    session = make_session('lesson.pdf')
    await file_svc.process_rehearsal_session_assets(db, session)

    assert session.scenes[0].scene_status == 'skipped'
    assert session.scenes[0].is_skipped is True
    assert session.scenes[0].skip_reason == '空白页'
    assert session.scenes[0].page_image_url == 'https://oss.example/rehearsal-pages/page-1.png'


@pytest.mark.asyncio
async def test_process_rehearsal_session_assets_keeps_image_as_fallback_when_parse_fails(tmp_path, monkeypatch):
    db = FakeDB()
    pdf_path = tmp_path / 'lesson.pdf'
    page_pdf = tmp_path / 'page_1.pdf'
    page_png = tmp_path / 'page_1.png'
    pdf_path.write_bytes(b'%PDF-1.4 pdf')
    page_pdf.write_bytes(b'%PDF-1.4 page1')
    page_png.write_bytes(b'png-1')

    monkeypatch.setattr(file_svc.oss_service, 'download_to_temp', lambda url: str(pdf_path))

    async def fake_upload_bytes(content: bytes, ext: str, user_id: int, prefix: str = 'rehearsal-audio') -> str:
        return f'https://oss.example/{prefix}/page-1.{ext}'

    monkeypatch.setattr(file_svc.oss_service, 'upload_bytes', fake_upload_bytes)
    monkeypatch.setattr(
        file_svc,
        'RenovationService',
        lambda: FakeRenovationService(
            pdf_path=str(pdf_path),
            page_paths=[page_pdf],
            image_paths=[page_png],
            parse_results={page_pdf.name: (None, 'markdown 解析失败')},
        ),
    )

    session = make_session('lesson.pdf')
    await file_svc.process_rehearsal_session_assets(db, session)

    assert session.scenes[0].scene_status == 'fallback'
    assert session.scenes[0].page_image_url == 'https://oss.example/rehearsal-pages/page-1.png'
    assert session.scenes[0].error_message == 'markdown 解析失败'



def test_compute_session_status_returns_partial_when_fallback_and_failed_pages_coexist():
    session = SessionStub(
        source='upload',
        scenes=[
            SimpleNamespace(scene_status='fallback', is_skipped=False),
            SimpleNamespace(scene_status='failed', is_skipped=False),
        ],
    )

    assert compute_session_status(session) == 'partial'
