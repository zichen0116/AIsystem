# PPT File Generation Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete `creation_type='file'` backend pipeline — a single API endpoint that accepts a document file and/or pasted text, parses the file via ParserFactory, combines inputs, generates a structured outline via AI, and creates page skeletons automatically.

**Architecture:** New route `POST /projects/file-generation` accepts multipart form data, creates project + reference file records, then dispatches a single Celery task `file_generation_task` that sequentially: downloads & parses the file, combines with user text, calls `banana_service.parse_outline_text()` for AI outline generation, and creates PPTPage records. All within existing FastAPI + SQLAlchemy + Celery architecture.

**Tech Stack:** Python 3.12(conda base), FastAPI, SQLAlchemy (async), Celery, Alembic, ParserFactory, BananaAIService

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/generators/ppt/banana_models.py` | Modify | Add `parsed_content` JSONB field to `PPTReferenceFile` |
| `backend/app/generators/ppt/banana_schemas.py` | Modify | Add `parsed_content` to `PPTReferenceFileResponse`; add `FileGenerationResponse` |
| `backend/app/generators/ppt/banana_routes.py` | Modify | Add `POST /projects/file-generation` route |
| `backend/app/generators/ppt/celery_tasks.py` | Modify | Add `file_generation_task` Celery task |
| `backend/alembic/versions/20260407_add_parsed_content_field.py` | Create | Migration for `parsed_content` column |
| `backend/tests/test_file_generation.py` | Create | Tests for route, task, and integration |

---

### Task 1: Add `parsed_content` field to model and schema

**Files:**
- Modify: `backend/app/generators/ppt/banana_models.py:286` (after `parsed_outline` line)
- Modify: `backend/app/generators/ppt/banana_schemas.py:257-272` (`PPTReferenceFileResponse`)

- [ ] **Step 1: Add `parsed_content` field to PPTReferenceFile model**

In `backend/app/generators/ppt/banana_models.py`, add after line 286 (`parsed_outline`):

```python
    parsed_content: Mapped[dict] = mapped_column(JSONB, nullable=True)
    """文件生成用：{normalized_text, chunks_meta, images}"""
```

- [ ] **Step 2: Add `parsed_content` to PPTReferenceFileResponse schema**

In `backend/app/generators/ppt/banana_schemas.py`, update `PPTReferenceFileResponse` (line 257) to add the field after `parsed_outline`:

```python
class PPTReferenceFileResponse(BaseModel):
    """PPT参考文件响应"""
    id: int
    project_id: int
    user_id: int
    filename: str
    oss_path: str
    url: str
    file_type: str
    file_size: Optional[int]
    parse_status: str
    parse_error: Optional[str]
    parsed_outline: Optional[dict]
    parsed_content: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Add `FileGenerationResponse` schema**

In `backend/app/generators/ppt/banana_schemas.py`, add after the `PPTReferenceFileResponse` class (before `# ============= Session Schemas =============`):

```python
class FileGenerationResponse(BaseModel):
    """文件生成一站式入口响应"""
    project_id: int
    task_id: str
    status: str = "processing"
    reference_file_id: Optional[int] = None
```

- [ ] **Step 4: Generate alembic migration**

Run:
```bash
cd backend && alembic revision --autogenerate -m "add parsed_content to ppt_reference_files"
```

Expected: A new migration file is created in `backend/alembic/versions/`.

- [ ] **Step 5: Apply migration**

Run:
```bash
cd backend && alembic upgrade head
```

Expected: Migration applies successfully, `parsed_content` column added to `ppt_reference_files` table.

- [ ] **Step 6: Commit**

```bash
git add backend/app/generators/ppt/banana_models.py backend/app/generators/ppt/banana_schemas.py backend/alembic/versions/*parsed_content*
git commit -m "feat(ppt): add parsed_content field and FileGenerationResponse schema"
```

---

### Task 2: Add `file_generation_task` Celery task

**Files:**
- Modify: `backend/app/generators/ppt/celery_tasks.py` (add new task at end of file)
- Test: `backend/tests/test_file_generation.py`

- [ ] **Step 1: Write test for the Celery task core logic**

Create `backend/tests/test_file_generation.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py -v
```

Expected: All tests FAIL with `ImportError` (functions not yet defined).

- [ ] **Step 3: Implement helper functions in celery_tasks.py**

Add the following at the end of `backend/app/generators/ppt/celery_tasks.py` (before any closing comments, after the last existing task):

```python
# ---------------------------------------------------------------------------
# 文件生成 - 辅助函数
# ---------------------------------------------------------------------------

def _normalize_parse_result(parse_result) -> tuple[str, dict]:
    """
    将 ParserFactory 返回的 ParseResult 标准化为大纲生成输入。

    Returns:
        (normalized_text, parsed_content_dict)
    """
    chunks_meta = []
    text_parts = []

    for chunk in parse_result.chunks:
        text_parts.append(chunk.content)
        chunks_meta.append({
            "content": chunk.content,
            **chunk.metadata,
        })

    normalized_text = "\n\n".join(text_parts)

    parsed_content = {
        "normalized_text": normalized_text,
        "chunks_meta": chunks_meta,
        "images": list(parse_result.images),
    }

    return normalized_text, parsed_content


def _combine_outline_source(
    normalized_text: str | None,
    source_text: str | None,
) -> str:
    """
    组合文件解析结果和用户文本为统一的大纲输入源。

    规则：
    - 有文件无文本 → 文件内容
    - 无文件有文本 → 用户文本
    - 两者都有 → 文件为主，用户文本为补充
    """
    has_file = bool(normalized_text and normalized_text.strip())
    has_text = bool(source_text and source_text.strip())

    if has_file and has_text:
        return f"{normalized_text}\n\n---\n用户补充说明：\n{source_text}"
    elif has_file:
        return normalized_text
    elif has_text:
        return source_text
    else:
        return ""


def _parse_outline_pages(data) -> list[dict]:
    """
    将 AI 生成的大纲 JSON 解析为 flat 页面列表。

    支持三种格式：
    1. list[{title, points}]          — simple
    2. list[{part, pages: [...]}]     — part-based
    3. dict{pages: [...]}             — wrapped
    """
    if isinstance(data, dict):
        if "pages" in data:
            return _parse_outline_pages(data["pages"])
        return []

    if not isinstance(data, list):
        return []

    pages = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "pages" in item and "part" in item:
            # part-based format
            part_name = item["part"]
            for p in item["pages"]:
                if isinstance(p, dict):
                    p["part"] = part_name
                    pages.append(p)
        else:
            pages.append(item)

    return pages
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/generators/ppt/celery_tasks.py backend/tests/test_file_generation.py
git commit -m "feat(ppt): add file generation helper functions with tests"
```

---

### Task 3: Implement the `file_generation_task` Celery task

**Files:**
- Modify: `backend/app/generators/ppt/celery_tasks.py` (add task after helpers from Task 2)
- Test: `backend/tests/test_file_generation.py` (add integration-level test)

- [ ] **Step 1: Write test for the full task flow**

Append to `backend/tests/test_file_generation.py`:

```python
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
                task_id="test-task-001",
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
                task_id_str="test-task-001",
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
                select(PPTTask).where(PPTTask.task_id == "test-task-001")
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py::TestFileGenerationTask -v
```

Expected: FAIL with `ImportError` (`file_generation_task` not found).

- [ ] **Step 3: Implement `file_generation_task`**

Add after the helper functions in `backend/app/generators/ppt/celery_tasks.py`:

```python
# ---------------------------------------------------------------------------
# 任务：文件生成（解析文件 → 组合文本 → 生成大纲 → 创建页面骨架）
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="banana-slides.file_generation")
def file_generation_task(
    self: Task,
    project_id: int,
    file_id: int | None = None,
    source_text: str | None = None,
    task_id_str: str | None = None,
):
    """
    文件生成一站式任务：

    1. 解析参考文件（如有）
    2. 组合输入源（文件 + 用户文本）
    3. AI 生成结构化大纲
    4. 创建页面骨架
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.generators.ppt.banana_models import PPTProject, PPTPage, PPTReferenceFile
    import shutil
    import json

    async def _run():
        normalized_text = None

        # ------ Step 1: 文件解析 ------
        if file_id is not None:
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                )
                ref_file = res.scalar_one_or_none()
                if not ref_file:
                    logger.error("文件生成任务: 参考文件 %d 不存在", file_id)
                    if task_id_str:
                        await _update_task_status(
                            db, task_id_str, "FAILED", 0,
                            {"error": f"参考文件 {file_id} 不存在"},
                        )
                    return
                ref_file.parse_status = "processing"
                await db.commit()

            if task_id_str:
                async with AsyncSessionLocal() as db:
                    await _update_task_status(db, task_id_str, "PROCESSING", 10)

            # 下载文件到临时目录
            tmp_dir = tempfile.mkdtemp(prefix="ppt_filegen_")
            try:
                oss_svc = _get_oss_service_safe()

                async with AsyncSessionLocal() as db:
                    res = await db.execute(
                        select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                    )
                    ref_file = res.scalar_one()
                    oss_path = ref_file.oss_path
                    filename = ref_file.filename

                tmp_path = os.path.join(tmp_dir, filename)

                if oss_svc is not None:
                    try:
                        oss_svc.download_file(oss_path, tmp_path)
                    except Exception as e:
                        logger.error("文件下载失败 oss_path=%s: %s", oss_path, e)
                        async with AsyncSessionLocal() as db:
                            res = await db.execute(
                                select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                            )
                            rf = res.scalar_one()
                            rf.parse_status = "failed"
                            rf.parse_error = f"文件下载失败: {e}"
                            await db.commit()
                            await _update_task_status(
                                db, task_id_str, "FAILED", 10,
                                {"error": f"文件下载失败: {e}"},
                            )
                        return
                else:
                    # OSS 不可用时尝试本地路径
                    if not os.path.exists(oss_path):
                        async with AsyncSessionLocal() as db:
                            res = await db.execute(
                                select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                            )
                            rf = res.scalar_one()
                            rf.parse_status = "failed"
                            rf.parse_error = "OSS不可用且本地文件不存在"
                            await db.commit()
                            await _update_task_status(
                                db, task_id_str, "FAILED", 10,
                                {"error": "OSS不可用且本地文件不存在"},
                            )
                        return
                    import shutil as _shutil
                    _shutil.copy2(oss_path, tmp_path)

                # 调用 ParserFactory 解析
                from app.services.parsers.factory import ParserFactory

                parse_result = await ParserFactory.parse_file(tmp_path)
                if parse_result is None:
                    async with AsyncSessionLocal() as db:
                        res = await db.execute(
                            select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                        )
                        rf = res.scalar_one()
                        rf.parse_status = "failed"
                        rf.parse_error = "不支持的文件类型或解析返回空结果"
                        await db.commit()
                        await _update_task_status(
                            db, task_id_str, "FAILED", 20,
                            {"error": "不支持的文件类型或解析返回空结果"},
                        )
                    return

                normalized_text, parsed_content = _normalize_parse_result(parse_result)

                # 持久化解析结果
                async with AsyncSessionLocal() as db:
                    res = await db.execute(
                        select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                    )
                    rf = res.scalar_one()
                    rf.parsed_content = parsed_content
                    rf.parse_status = "completed"
                    rf.parse_error = None
                    await db.commit()

                if task_id_str:
                    async with AsyncSessionLocal() as db:
                        await _update_task_status(db, task_id_str, "PROCESSING", 30)

            except Exception as e:
                logger.exception("文件生成任务: 文件解析异常 file_id=%d", file_id)
                async with AsyncSessionLocal() as db:
                    res = await db.execute(
                        select(PPTReferenceFile).where(PPTReferenceFile.id == file_id)
                    )
                    rf = res.scalar_one_or_none()
                    if rf:
                        rf.parse_status = "failed"
                        rf.parse_error = str(e)
                    await db.commit()
                    if task_id_str:
                        await _update_task_status(
                            db, task_id_str, "FAILED", 20,
                            {"error": f"文件解析失败: {e}"},
                        )
                return
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        # ------ Step 2: 组合输入源 ------
        outline_source = _combine_outline_source(normalized_text, source_text)

        if not outline_source.strip():
            async with AsyncSessionLocal() as db:
                if task_id_str:
                    await _update_task_status(
                        db, task_id_str, "FAILED", 40,
                        {"error": "没有有效的输入内容"},
                    )
                res = await db.execute(
                    select(PPTProject).where(PPTProject.id == project_id)
                )
                proj = res.scalar_one_or_none()
                if proj:
                    proj.status = "FAILED"
                await db.commit()
            return

        # 写入 outline_text（作为输入源）
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(PPTProject).where(PPTProject.id == project_id)
            )
            project = res.scalar_one()
            project.outline_text = outline_source
            await db.commit()

        if task_id_str:
            async with AsyncSessionLocal() as db:
                await _update_task_status(db, task_id_str, "PROCESSING", 40)

        # ------ Step 3: AI 生成大纲 ------
        try:
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PPTProject).where(PPTProject.id == project_id)
                )
                project = res.scalar_one()
                theme = project.template_style or project.theme
                language = (project.settings or {}).get("language", "zh")

            banana_svc = get_banana_service()
            outline_data = await banana_svc.parse_outline_text(
                outline_source, theme=theme, language=language,
            )

            # 检查是否返回了错误
            if isinstance(outline_data, dict) and "error" in outline_data:
                raise ValueError(f"大纲生成失败: {outline_data['error']}")

        except Exception as e:
            logger.exception("文件生成任务: 大纲生成失败 project_id=%d", project_id)
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PPTProject).where(PPTProject.id == project_id)
                )
                proj = res.scalar_one()
                proj.status = "FAILED"
                await db.commit()
                if task_id_str:
                    await _update_task_status(
                        db, task_id_str, "FAILED", 70,
                        {"error": f"大纲生成失败: {e}"},
                    )
            return

        if task_id_str:
            async with AsyncSessionLocal() as db:
                await _update_task_status(db, task_id_str, "PROCESSING", 70)

        # ------ Step 4: 创建页面骨架 ------
        pages_data = _parse_outline_pages(outline_data)

        if not pages_data:
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(PPTProject).where(PPTProject.id == project_id)
                )
                proj = res.scalar_one()
                proj.status = "FAILED"
                await db.commit()
                if task_id_str:
                    await _update_task_status(
                        db, task_id_str, "FAILED", 80,
                        {"error": "AI返回的大纲无法解析为页面"},
                    )
            return

        async with AsyncSessionLocal() as db:
            # 删除项目现有页面（如重试场景）
            existing = await db.execute(
                select(PPTPage).where(PPTPage.project_id == project_id)
            )
            for ep in existing.scalars().all():
                await db.delete(ep)
            await db.flush()

            for i, page_data in enumerate(pages_data):
                cfg = {}
                if page_data.get("part"):
                    cfg["part"] = page_data["part"]
                if page_data.get("points") is not None:
                    cfg["points"] = page_data.get("points", [])

                page = PPTPage(
                    project_id=project_id,
                    page_number=i + 1,
                    title=page_data.get("title", f"第{i+1}页"),
                    config=cfg,
                )
                db.add(page)

            # 覆写 outline_text 为结构化 JSON 结果
            res = await db.execute(
                select(PPTProject).where(PPTProject.id == project_id)
            )
            project = res.scalar_one()
            project.outline_text = json.dumps(outline_data, ensure_ascii=False)
            project.status = "PLANNING"
            await db.commit()

        # ------ Step 5: 完成 ------
        if task_id_str:
            async with AsyncSessionLocal() as db:
                await _update_task_status(
                    db, task_id_str, "COMPLETED", 100,
                    {"status": "completed", "pages_count": len(pages_data)},
                )

        logger.info(
            "文件生成任务完成: project_id=%d, pages=%d",
            project_id, len(pages_data),
        )

    asyncio.run(_run())
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py::TestFileGenerationTask -v
```

Expected: PASS (with mocked AI service).

- [ ] **Step 5: Commit**

```bash
git add backend/app/generators/ppt/celery_tasks.py backend/tests/test_file_generation.py
git commit -m "feat(ppt): implement file_generation_task Celery task"
```

---

### Task 4: Add `POST /projects/file-generation` route

**Files:**
- Modify: `backend/app/generators/ppt/banana_routes.py` (add route in the Reference Files section)
- Test: `backend/tests/test_file_generation.py` (add route test)

- [ ] **Step 1: Write test for the route**

Append to `backend/tests/test_file_generation.py`:

```python
class TestFileGenerationRoute:
    """Test the POST /projects/file-generation endpoint."""

    @pytest.mark.asyncio
    async def test_text_only_returns_processing(self):
        """Text-only request should create project and return task info."""
        from unittest.mock import patch, MagicMock
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        # Mock auth to return a fake user
        mock_user = MagicMock()
        mock_user.id = 1

        # Mock Celery task delay
        with patch(
            "app.generators.ppt.banana_routes.get_current_user",
            return_value=mock_user,
        ), patch(
            "app.generators.ppt.celery_tasks.file_generation_task.delay"
        ) as mock_delay:
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
            mock_delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_input_returns_400(self):
        """Request with neither file nor text should return 400."""
        from unittest.mock import patch, MagicMock
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        mock_user = MagicMock()
        mock_user.id = 1

        with patch(
            "app.generators.ppt.banana_routes.get_current_user",
            return_value=mock_user,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/ppt/projects/file-generation",
                    data={},
                )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unsupported_file_type_returns_400(self):
        """Uploading an unsupported file type should return 400."""
        from unittest.mock import patch, MagicMock
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        import io

        mock_user = MagicMock()
        mock_user.id = 1

        with patch(
            "app.generators.ppt.banana_routes.get_current_user",
            return_value=mock_user,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/ppt/projects/file-generation",
                    files={"file": ("test.mp4", io.BytesIO(b"fake"), "video/mp4")},
                )

            assert response.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py::TestFileGenerationRoute -v
```

Expected: FAIL (route not yet defined, 404 or import error).

- [ ] **Step 3: Implement the route**

In `backend/app/generators/ppt/banana_routes.py`, add the following route **before** the existing `# ============= Reference Files =============` section (around line 1812):

```python
# ============= File Generation =============

@router.post("/projects/file-generation", response_model=FileGenerationResponse)
async def file_generation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    file: Optional[UploadFile] = File(None),
    source_text: Optional[str] = Form(None),
    title: str = Form("未命名PPT"),
    theme: Optional[str] = Form(None),
    template_style: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
):
    """
    文件生成一站式入口。

    支持三种输入方式：
    - 仅上传文件（pdf/doc/docx）
    - 仅粘贴文本
    - 文件 + 文本组合
    """
    # 校验：至少提供一种输入
    has_file = file is not None and file.filename
    has_text = bool(source_text and source_text.strip())
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="请上传文件或输入文本内容")

    # 校验文件类型
    ALLOWED_FILE_EXTS = {"pdf", "doc", "docx"}
    file_ext = None
    if has_file:
        file_ext = _normalize_file_ext(file.filename, file.content_type)
        if file_ext not in ALLOWED_FILE_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，仅支持 pdf/doc/docx",
            )

    # 解析 settings JSON
    parsed_settings = {}
    if settings:
        try:
            parsed_settings = json.loads(settings)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="settings 格式错误，需要有效的JSON")

    # 1. 创建项目
    project = PPTProject(
        user_id=current_user.id,
        title=title,
        creation_type="file",
        theme=theme,
        template_style=template_style or parsed_settings.get("template_style"),
        settings=parsed_settings,
        knowledge_library_ids=[],
        status="GENERATING",
    )
    _sync_project_template_style_to_settings(project)
    db.add(project)
    await db.flush()

    # 2. 保存参考文件（如有）
    ref_file_id = None
    if has_file:
        content = await file.read()
        oss_key = f"ppt/{project.id}/reference/{uuid.uuid4()}/{file.filename}"

        # 上传到 OSS
        from app.generators.ppt.file_service import get_oss_service
        try:
            oss_svc = get_oss_service()
            file_url = oss_svc.upload_bytes(content, oss_key)
        except Exception:
            # OSS 不可用时保存到本地
            local_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "exports", "uploads"
            )
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, f"{uuid.uuid4()}_{file.filename}")
            with open(local_path, "wb") as f:
                f.write(content)
            file_url = local_path
            oss_key = local_path

        ref_file = PPTReferenceFile(
            project_id=project.id,
            user_id=current_user.id,
            filename=file.filename,
            oss_path=oss_key,
            url=file_url,
            file_type=file_ext,
            file_size=len(content),
            parse_status="pending",
        )
        db.add(ref_file)
        await db.flush()
        ref_file_id = ref_file.id

    # 3. 创建任务记录
    task_id = str(uuid.uuid4())
    task = PPTTask(
        project_id=project.id,
        task_id=task_id,
        task_type="file_generation",
        status="PENDING",
        progress=0,
    )
    db.add(task)
    await db.commit()

    # 4. 启动 Celery 任务
    from app.generators.ppt.celery_tasks import file_generation_task
    file_generation_task.delay(
        project_id=project.id,
        file_id=ref_file_id,
        source_text=source_text if has_text else None,
        task_id_str=task_id,
    )

    return FileGenerationResponse(
        project_id=project.id,
        task_id=task_id,
        status="processing",
        reference_file_id=ref_file_id,
    )
```

Also add the import for `FileGenerationResponse` at the top of `banana_routes.py` where other schemas are imported. Find the existing import line for schemas (e.g., where `PPTReferenceFileResponse` is imported) and add `FileGenerationResponse`:

```python
from app.generators.ppt.banana_schemas import (
    ...,
    FileGenerationResponse,
)
```

Also ensure `Form` is imported from `fastapi`:

```python
from fastapi import ..., Form, ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py::TestFileGenerationRoute -v
```

Expected: All route tests PASS.

- [ ] **Step 5: Run all tests together**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/generators/ppt/banana_routes.py backend/app/generators/ppt/banana_schemas.py backend/tests/test_file_generation.py
git commit -m "feat(ppt): add POST /projects/file-generation one-stop route"
```

---

### Task 5: Final integration verification

**Files:**
- All files from previous tasks

- [ ] **Step 1: Run all file generation tests**

Run:
```bash
cd backend && python -m pytest tests/test_file_generation.py -v
```

Expected: All tests PASS.

- [ ] **Step 2: Run existing PPT tests to verify no regressions**

Run:
```bash
cd backend && python -m pytest tests/ -k "ppt" -v --tb=short
```

Expected: All existing PPT tests still PASS.

- [ ] **Step 3: Verify server starts without import errors**

Run:
```bash
cd backend && python -c "from app.generators.ppt.banana_routes import router; print('Routes OK')"
```

Expected: `Routes OK` printed, no import errors.

- [ ] **Step 4: Commit any final fixes if needed**

Only if previous steps revealed issues:
```bash
git add -A
git commit -m "fix(ppt): address integration issues in file generation"
```
