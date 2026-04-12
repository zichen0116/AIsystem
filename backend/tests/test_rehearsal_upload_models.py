from datetime import datetime, timezone
from types import SimpleNamespace

from app.schemas.rehearsal import RehearsalSessionDetail
from app.services.rehearsal_session_service import (
    compute_session_status,
    summarize_session_counts,
)


def make_scene(order: int, status: str, *, page_image_url: str | None = None, is_skipped: bool = False):
    return SimpleNamespace(
        id=order,
        session_id=1,
        scene_order=order,
        title=f"Scene {order}",
        scene_status=status,
        slide_content=None,
        actions=None,
        key_points=None,
        audio_status="pending",
        error_message=None,
        original_page_number=order + 1,
        is_skipped=is_skipped,
        skip_reason="空白页" if is_skipped else None,
        page_image_url=page_image_url,
        page_text=None,
        script_text=None,
        audio_url=None,
    )


class SessionStub(SimpleNamespace):
    @property
    def ready_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == "ready")

    @property
    def fallback_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == "fallback")

    @property
    def skipped_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == "skipped" or scene.is_skipped)

    @property
    def failed_count(self) -> int:
        return sum(1 for scene in self.scenes if scene.scene_status == "failed")

    @property
    def playable_count(self) -> int:
        return self.ready_count + self.fallback_count



def make_session(*scenes, source: str = "upload"):
    return SessionStub(
        id=1,
        user_id=7,
        title="上传预演",
        topic="",
        status="processing",
        total_scenes=len(scenes),
        playback_snapshot=None,
        language="zh-CN",
        settings=None,
        error_message=None,
        source=source,
        original_file_url="https://oss.example/rehearsal-upload/7/file.pdf",
        original_file_name="lesson.pdf",
        converted_pdf_url="https://oss.example/rehearsal-upload/7/file.pdf",
        total_pages=5,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        scenes=list(scenes),
    )



def test_compute_session_status_returns_processing_for_upload_session_with_pending_scene():
    session = make_session(make_scene(0, "pending"), make_scene(1, "ready", page_image_url="https://oss.example/page-1.png"))

    assert compute_session_status(session) == "processing"



def test_summarize_session_counts_treats_fallback_as_playable_and_skipped_separately():
    session = make_session(
        make_scene(0, "ready", page_image_url="https://oss.example/page-1.png"),
        make_scene(1, "fallback", page_image_url="https://oss.example/page-2.png"),
        make_scene(2, "skipped", is_skipped=True),
        make_scene(3, "failed"),
    )

    counts = summarize_session_counts(session)

    assert counts == {
        "ready_count": 1,
        "fallback_count": 1,
        "playable_count": 2,
        "skipped_count": 1,
        "failed_count": 1,
    }



def test_rehearsal_session_detail_exposes_upload_metadata_fields():
    session = make_session(
        make_scene(0, "ready", page_image_url="https://oss.example/page-1.png"),
        make_scene(1, "skipped", is_skipped=True),
    )

    detail = RehearsalSessionDetail.model_validate(session)

    assert detail.source == "upload"
    assert detail.original_file_name == "lesson.pdf"
    assert detail.total_pages == 5
    assert detail.playable_count == 1
    assert detail.skipped_count == 1
    assert detail.scenes[0].original_page_number == 1
    assert detail.scenes[0].page_image_url == "https://oss.example/page-1.png"
