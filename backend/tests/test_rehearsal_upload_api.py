import io
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

import app.main  # noqa: F401  # ensure full model/router registration
from app.services import rehearsal_upload_service as upload_svc


class FakeDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = len(self.added) + 1
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed.append(obj)



def make_upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_create_rehearsal_upload_session_success(monkeypatch):
    db = FakeDB()
    file = make_upload("lesson.pdf", b"%PDF-1.4 fake rehearsal file", "application/pdf")

    def fake_count_pages(path: str, ext: str) -> int:
        assert ext == "pdf"
        return 12

    async def fake_upload_file(upload_file, user_id: int, prefix: str = "knowledge"):
        assert upload_file.filename == "lesson.pdf"
        assert user_id == 7
        assert prefix == "rehearsal-upload"
        return {
            "url": "https://oss.example/rehearsal-upload/7/lesson.pdf",
            "file_name": "lesson.pdf",
            "file_type": "pdf",
        }

    monkeypatch.setattr(upload_svc, "count_pages_for_upload", fake_count_pages)
    monkeypatch.setattr(upload_svc.oss_service, "upload_file", fake_upload_file)

    result = await upload_svc.create_rehearsal_upload_session(db, 7, file)

    assert result == {
        "session_id": 1,
        "status": "uploaded",
        "source": "upload",
        "total_pages": 12,
    }
    assert db.committed is True
    session = db.added[0]
    assert session.source == "upload"
    assert session.status == "processing"
    assert session.original_file_name == "lesson.pdf"
    assert session.original_file_url == "https://oss.example/rehearsal-upload/7/lesson.pdf"
    assert session.converted_pdf_url == "https://oss.example/rehearsal-upload/7/lesson.pdf"
    assert session.total_pages == 12


@pytest.mark.asyncio
async def test_create_rehearsal_upload_session_rejects_unsupported_file_type():
    db = FakeDB()
    file = make_upload("notes.txt", b"plain text", "text/plain")

    with pytest.raises(ValueError, match="文件类型不支持"):
        await upload_svc.create_rehearsal_upload_session(db, 7, file)


@pytest.mark.asyncio
async def test_create_rehearsal_upload_session_rejects_oversized_file():
    db = FakeDB()
    content = b"a" * (upload_svc.MAX_REHEARSAL_UPLOAD_SIZE + 1)
    file = make_upload("lesson.pdf", content, "application/pdf")

    with pytest.raises(ValueError, match="文件大小超过50MB"):
        await upload_svc.create_rehearsal_upload_session(db, 7, file)


@pytest.mark.asyncio
async def test_create_rehearsal_upload_session_rejects_page_limit(monkeypatch):
    db = FakeDB()
    file = make_upload("lesson.pptx", b"pptx-binary", "application/vnd.openxmlformats-officedocument.presentationml.presentation")

    monkeypatch.setattr(upload_svc, "count_pages_for_upload", lambda path, ext: 31)

    with pytest.raises(ValueError, match="文件页数超过30页上限"):
        await upload_svc.create_rehearsal_upload_session(db, 7, file)
