"""
Tests for PPT file generation backend.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


@dataclass
class FakeChunk:
    content: str
    metadata: dict


@dataclass
class FakeParseResult:
    chunks: list
    images: list


class TestNormalizeParseResult:
    """Test the _normalize_parse_result helper."""

    def test_chunks_joined_in_order(self):
        from app.generators.ppt.celery_tasks import _normalize_parse_result

        chunks = [
            FakeChunk(content="Chapter 1: Introduction", metadata={"page": 1}),
            FakeChunk(content="This is the body text.", metadata={"page": 1}),
            FakeChunk(content="Chapter 2: Methods", metadata={"page": 2}),
        ]
        result = FakeParseResult(chunks=chunks, images=[])
        normalized_text, parsed_content = _normalize_parse_result(result)

        assert "Chapter 1: Introduction" in normalized_text
        assert "Chapter 2: Methods" in normalized_text
        assert normalized_text.index("Chapter 1") < normalized_text.index("Chapter 2")
        assert parsed_content["normalized_text"] == normalized_text
        assert len(parsed_content["chunks_meta"]) == 3
        assert parsed_content["images"] == []

    def test_empty_chunks(self):
        from app.generators.ppt.celery_tasks import _normalize_parse_result

        result = FakeParseResult(chunks=[], images=[])
        normalized_text, parsed_content = _normalize_parse_result(result)
        assert normalized_text == ""
        assert parsed_content["chunks_meta"] == []

    def test_images_preserved(self):
        from app.generators.ppt.celery_tasks import _normalize_parse_result

        chunks = [FakeChunk(content="Some text", metadata={"page": 1})]
        result = FakeParseResult(chunks=chunks, images=["img1.png", "img2.png"])
        _, parsed_content = _normalize_parse_result(result)
        assert parsed_content["images"] == ["img1.png", "img2.png"]


class TestCombineOutlineSource:
    """Test the _combine_outline_source helper."""

    def test_file_only(self):
        from app.generators.ppt.celery_tasks import _combine_outline_source

        result = _combine_outline_source("file content here", None)
        assert result == "file content here"

    def test_text_only(self):
        from app.generators.ppt.celery_tasks import _combine_outline_source

        result = _combine_outline_source(None, "user pasted text")
        assert result == "user pasted text"

    def test_file_and_text_combined(self):
        from app.generators.ppt.celery_tasks import _combine_outline_source

        result = _combine_outline_source("file content", "user notes")
        assert "file content" in result
        assert "user notes" in result
        assert result.index("file content") < result.index("user notes")

    def test_empty_text_treated_as_none(self):
        from app.generators.ppt.celery_tasks import _combine_outline_source

        result = _combine_outline_source("file content", "   ")
        assert result == "file content"


class TestParseOutlinePages:
    """Test the _parse_outline_pages helper."""

    def test_simple_format(self):
        from app.generators.ppt.celery_tasks import _parse_outline_pages

        data = [
            {"title": "Title Page", "points": ["subtitle"]},
            {"title": "Chapter 1", "points": ["point1", "point2"]},
        ]
        pages = _parse_outline_pages(data)
        assert len(pages) == 2
        assert pages[0]["title"] == "Title Page"
        assert pages[1]["points"] == ["point1", "point2"]

    def test_part_based_format(self):
        from app.generators.ppt.celery_tasks import _parse_outline_pages

        data = [
            {
                "part": "Part 1",
                "pages": [
                    {"title": "Page 1", "points": ["a"]},
                    {"title": "Page 2", "points": ["b"]},
                ],
            }
        ]
        pages = _parse_outline_pages(data)
        assert len(pages) == 2
        assert pages[0]["part"] == "Part 1"
        assert pages[1]["part"] == "Part 1"

    def test_dict_with_pages_key(self):
        from app.generators.ppt.celery_tasks import _parse_outline_pages

        data = {"pages": [{"title": "P1", "points": []}]}
        pages = _parse_outline_pages(data)
        assert len(pages) == 1

    def test_empty_returns_empty(self):
        from app.generators.ppt.celery_tasks import _parse_outline_pages

        assert _parse_outline_pages([]) == []
        assert _parse_outline_pages({}) == []


class TestFileGenerationRoute:
    """Test the POST /projects/file-generation endpoint."""

    @pytest.mark.asyncio
    async def test_text_only_returns_processing(self):
        """Text-only request should create project and return task info."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.core.auth import get_current_user

        mock_user = MagicMock()
        mock_user.id = 1

        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with patch(
                "app.generators.ppt.banana_routes.dispatch_file_generation_task"
            ) as mock_dispatch:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/ppt/projects/file-generation",
                        data={"source_text": "这是关于人工智能的教学内容"},
                    )

                assert response.status_code == 200
                body = response.json()
                assert body["status"] == "processing"
                assert body["project_id"] > 0
                assert body["task_id"] is not None
                assert body["reference_file_id"] is None
                mock_dispatch.assert_called_once()
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            from app.core.database import engine
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_no_input_returns_400(self):
        """Request with neither file nor text should return 400."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.core.auth import get_current_user

        mock_user = MagicMock()
        mock_user.id = 1

        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/ppt/projects/file-generation",
                    data={},
                )

            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            from app.core.database import engine
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_unsupported_file_type_returns_400(self):
        """Uploading an unsupported file type should return 400."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.core.auth import get_current_user
        import io

        mock_user = MagicMock()
        mock_user.id = 1

        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/ppt/projects/file-generation",
                    files={"file": ("test.mp4", io.BytesIO(b"fake"), "video/mp4")},
                )

            assert response.status_code == 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            from app.core.database import engine
            await engine.dispose()


class TestFileGenerationTask:
    """Test the file_generation_task end-to-end (mocked AI + DB)."""

    @pytest.mark.asyncio
    async def test_text_only_creates_pages(self):
        """Pure text input should generate outline and create pages."""
        from app.core.database import AsyncSessionLocal
        from app.generators.ppt.banana_models import PPTProject, PPTPage, PPTTask
        from sqlalchemy import select

        # Create a test project + task
        async with AsyncSessionLocal() as db:
            project = PPTProject(
                user_id=1,
                title="Test File Gen",
                creation_type="file",
                status="GENERATING",
                settings={},
                knowledge_library_ids=[],
            )
            db.add(project)
            await db.flush()

            task = PPTTask(
                project_id=project.id,
                task_id="test-filegen-001",
                task_type="file_generation",
                status="PENDING",
                progress=0,
            )
            db.add(task)
            await db.commit()
            project_id = project.id

        # Mock AI to return a simple outline
        mock_outline = [
            {"title": "Title Slide", "points": ["subtitle"]},
            {"title": "Chapter 1", "points": ["point A", "point B"]},
        ]

        import nest_asyncio
        nest_asyncio.apply()

        with patch(
            "app.generators.ppt.celery_tasks.get_banana_service"
        ) as mock_svc_factory:
            mock_svc = MagicMock()
            mock_svc.parse_outline_text = AsyncMock(return_value=mock_outline)
            mock_svc_factory.return_value = mock_svc

            from app.generators.ppt.celery_tasks import file_generation_task
            file_generation_task(
                project_id=project_id,
                file_id=None,
                source_text="这是关于人工智能的课程大纲",
                task_id_str="test-filegen-001",
            )

        # Verify results
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(PPTProject).where(PPTProject.id == project_id)
            )
            project = res.scalar_one()
            assert project.status == "PLANNING"
            assert project.outline_text is not None

            res = await db.execute(
                select(PPTPage)
                .where(PPTPage.project_id == project_id)
                .order_by(PPTPage.page_number)
            )
            pages = res.scalars().all()
            assert len(pages) == 2
            assert pages[0].title == "Title Slide"
            assert pages[1].config.get("points") == ["point A", "point B"]

            res = await db.execute(
                select(PPTTask).where(PPTTask.task_id == "test-filegen-001")
            )
            task = res.scalar_one()
            assert task.status == "COMPLETED"
            assert task.progress == 100

        # Cleanup
        async with AsyncSessionLocal() as db:
            await db.execute(
                PPTPage.__table__.delete().where(PPTPage.project_id == project_id)
            )
            await db.execute(
                PPTTask.__table__.delete().where(PPTTask.project_id == project_id)
            )
            await db.execute(
                PPTProject.__table__.delete().where(PPTProject.id == project_id)
            )
            await db.commit()
