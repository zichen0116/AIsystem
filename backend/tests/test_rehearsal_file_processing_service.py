from pathlib import Path

import pytest

import app.main  # noqa: F401  # ensure model registration
from app.models.rehearsal import RehearsalSession
from app.services import rehearsal_file_processing_service as file_svc


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
    def __init__(self, *, pdf_path, page_paths, image_paths, page_texts, convert_should_run=False):
        self._pdf_path = pdf_path
        self._page_paths = page_paths
        self._image_paths = image_paths
        self._page_texts = page_texts
        self._convert_should_run = convert_should_run

    def convert_to_pdf(self, file_path: str, file_ext: str) -> str:
        if not self._convert_should_run:
            raise AssertionError('convert_to_pdf should not run for direct PDF uploads')
        assert file_ext == 'pptx'
        return self._pdf_path

    async def split_pdf_to_pages(self, pdf_path: str, output_dir: str) -> list[str]:
        assert pdf_path == self._pdf_path
        return [str(path) for path in self._page_paths]

    def render_pdf_to_images(self, pdf_path: str, output_dir: str) -> list[str | None]:
        assert pdf_path == self._pdf_path
        return [str(path) for path in self._image_paths]

    async def parse_page_markdown(self, page_pdf_path: str, filename: str):
        return self._page_texts[filename], None


def make_session(filename: str, original_url: str, *, converted_pdf_url: str | None = None) -> RehearsalSession:
    session = RehearsalSession(
        user_id=7,
        title='上传预演',
        topic='上传预演',
        source='upload',
        status='processing',
        total_scenes=0,
        language='zh-CN',
        original_file_url=original_url,
        original_file_name=filename,
        converted_pdf_url=converted_pdf_url,
        total_pages=None,
    )
    session.id = 11
    session.scenes = []
    return session


@pytest.mark.asyncio
async def test_process_rehearsal_session_assets_keeps_direct_pdf_and_persists_page_assets(tmp_path, monkeypatch):
    db = FakeDB()
    pdf_path = tmp_path / 'lesson.pdf'
    page_1_pdf = tmp_path / 'page_1.pdf'
    page_2_pdf = tmp_path / 'page_2.pdf'
    page_1_png = tmp_path / 'page_1.png'
    page_2_png = tmp_path / 'page_2.png'

    pdf_path.write_bytes(b'%PDF-1.4 pdf')
    page_1_pdf.write_bytes(b'%PDF-1.4 page1')
    page_2_pdf.write_bytes(b'%PDF-1.4 page2')
    page_1_png.write_bytes(b'png-1')
    page_2_png.write_bytes(b'png-2')

    session = make_session(
        'lesson.pdf',
        'https://oss.example/rehearsal-upload/7/lesson.pdf',
        converted_pdf_url='https://oss.example/rehearsal-upload/7/lesson.pdf',
    )

    page_texts = {
        page_1_pdf.name: '# Page 1',
        page_2_pdf.name: '# Page 2',
    }
    upload_calls = []

    monkeypatch.setattr(file_svc.oss_service, 'download_to_temp', lambda url: str(pdf_path))

    async def fake_upload_bytes(content: bytes, ext: str, user_id: int, prefix: str = 'rehearsal-audio') -> str:
        upload_calls.append((content, ext, user_id, prefix))
        return f'https://oss.example/{prefix}/{len(upload_calls)}.{ext}'

    monkeypatch.setattr(file_svc.oss_service, 'upload_bytes', fake_upload_bytes)
    monkeypatch.setattr(
        file_svc,
        'RenovationService',
        lambda: FakeRenovationService(
            pdf_path=str(pdf_path),
            page_paths=[page_1_pdf, page_2_pdf],
            image_paths=[page_1_png, page_2_png],
            page_texts=page_texts,
            convert_should_run=False,
        ),
    )

    result = await file_svc.process_rehearsal_session_assets(db, session)

    assert result['scene_count'] == 2
    assert result['converted_pdf_url'] == 'https://oss.example/rehearsal-upload/7/lesson.pdf'
    assert session.converted_pdf_url == 'https://oss.example/rehearsal-upload/7/lesson.pdf'
    assert session.total_scenes == 2
    assert db.flushed is True
    assert len(session.scenes) == 2
    assert session.scenes[0].original_page_number == 1
    assert session.scenes[0].page_text == '# Page 1'
    assert session.scenes[0].page_image_url == 'https://oss.example/rehearsal-pages/1.png'
    assert session.scenes[1].original_page_number == 2
    assert session.scenes[1].page_text == '# Page 2'
    assert session.scenes[1].page_image_url == 'https://oss.example/rehearsal-pages/2.png'
    assert [call[3] for call in upload_calls] == ['rehearsal-pages', 'rehearsal-pages']


@pytest.mark.asyncio
async def test_process_rehearsal_session_assets_converts_pptx_and_uploads_pdf(tmp_path, monkeypatch):
    db = FakeDB()
    pptx_path = tmp_path / 'lesson.pptx'
    converted_pdf_path = tmp_path / 'lesson.pdf'
    page_1_pdf = tmp_path / 'page_1.pdf'
    page_1_png = tmp_path / 'page_1.png'

    pptx_path.write_bytes(b'pptx-binary')
    converted_pdf_path.write_bytes(b'%PDF-1.4 converted')
    page_1_pdf.write_bytes(b'%PDF-1.4 page1')
    page_1_png.write_bytes(b'png-1')

    session = make_session('lesson.pptx', 'https://oss.example/rehearsal-upload/7/lesson.pptx')

    upload_calls = []
    monkeypatch.setattr(file_svc.oss_service, 'download_to_temp', lambda url: str(pptx_path))

    async def fake_upload_bytes(content: bytes, ext: str, user_id: int, prefix: str = 'rehearsal-audio') -> str:
        upload_calls.append((content, ext, user_id, prefix))
        return f'https://oss.example/{prefix}/{len(upload_calls)}.{ext}'

    monkeypatch.setattr(file_svc.oss_service, 'upload_bytes', fake_upload_bytes)
    monkeypatch.setattr(
        file_svc,
        'RenovationService',
        lambda: FakeRenovationService(
            pdf_path=str(converted_pdf_path),
            page_paths=[page_1_pdf],
            image_paths=[page_1_png],
            page_texts={page_1_pdf.name: '# Converted Page 1'},
            convert_should_run=True,
        ),
    )

    result = await file_svc.process_rehearsal_session_assets(db, session)

    assert result['scene_count'] == 1
    assert session.converted_pdf_url == 'https://oss.example/rehearsal-pdf/1.pdf'
    assert session.total_scenes == 1
    assert len(session.scenes) == 1
    assert session.scenes[0].page_text == '# Converted Page 1'
    assert session.scenes[0].page_image_url == 'https://oss.example/rehearsal-pages/2.png'
    assert [call[3] for call in upload_calls] == ['rehearsal-pdf', 'rehearsal-pages']
