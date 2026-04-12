# Testing Patterns

**Analysis Date:** 2026-04-12

## Test Framework

**Runner:**
- Backend: `pytest` is the primary runner pattern in `backend/tests/test_lesson_plan_api.py`, `backend/tests/test_file_generation.py`, `backend/tests/test_rehearsal_media_service.py`, and other `backend/tests/test_*.py` modules that use `@pytest.mark.asyncio`.
- Backend also contains `unittest` suites for pure helper logic in files such as `backend/tests/test_rehearsal_generation_service.py` and `backend/tests/test_start_dev_waits.py`.
- Frontend: no Vitest or Jest runner was detected for `teacher-platform/src/`. The only app-owned frontend test is the self-executing Node script `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.
- Config: no `pytest.ini`, `conftest.py`, `tox.ini`, `jest.config.*`, or `vitest.config.*` was detected for the repo-owned applications. `CLAUDE.md` explicitly documents per-file pytest execution rather than a global pytest setup.

**Assertion Library:**
- Backend pytest tests use plain `assert`, for example `backend/tests/test_lesson_plan_api.py` and `backend/tests/test_rehearsal_media_service.py`.
- Backend `unittest` modules use `self.assertEqual`, `self.assertRaises`, and similar methods in `backend/tests/test_rehearsal_generation_service.py` and `backend/tests/test_start_dev_waits.py`.
- Frontend standalone tests use `node:assert/strict` in `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.

**Run Commands:**
```bash
cd backend && python -m pytest tests/test_lesson_plan_api.py
cd backend && python -m pytest tests/test_file_generation.py
cd teacher-platform && node src/composables/rehearsalPlaybackEffects.test.js
```

## Test File Organization

**Location:**
- Backend tests are centralized under `backend/tests/`.
- Frontend app tests are colocated with the source file, currently only `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.
- Some backend files under `backend/tests/` behave more like manual verification scripts than strict automated suites, especially `backend/tests/test_all_parsers.py`, which uses logging and a `__main__` entrypoint.

**Naming:**
- Backend uses `test_*.py`, such as `backend/tests/test_ppt_genai_provider.py` and `backend/tests/test_ppt_renovation.py`.
- Frontend uses the `.test.js` suffix, as in `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.

**Structure:**
```text
backend/tests/test_*.py
teacher-platform/src/**/*.test.js
```

## Test Structure

**Suite Organization:**
```python
@pytest.mark.asyncio
async def test_list_lesson_plans_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/lesson-plan/list", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
```

**Patterns:**
- Async backend endpoint tests use `@pytest.mark.asyncio` with fixture arguments such as `client`, `auth_headers`, `db_session`, and `test_user_id`, as seen in `backend/tests/test_lesson_plan_api.py` and `backend/tests/test_lesson_plan_delete.py`.
- Endpoint tests often create DB state inline, then hit FastAPI routes through `httpx.AsyncClient`, as in `backend/tests/test_lesson_plan_api.py`.
- Pure logic tests frequently use class-based grouping without fixture setup, for example `TestNormalizeParseResult` in `backend/tests/test_file_generation.py` and `RehearsalGenerationServiceTests` in `backend/tests/test_rehearsal_generation_service.py`.
- `unittest.TestCase` remains in use for small helper modules and CLI-oriented code such as `backend/start_dev.py`, tested by `backend/tests/test_start_dev_waits.py`.
- Script-style test files such as `backend/tests/test_all_parsers.py` and `backend/tests/test_video_parser.py` include logging, environment-dependent inputs, and `if __name__ == "__main__"` execution paths. Treat them as smoke/manual checks, not as the cleanest template for new automated tests.

## Mocking

**Framework:** `unittest.mock` plus pytest `monkeypatch`.

**Patterns:**
```python
with patch("app.generators.ppt.banana_routes.dispatch_file_generation_task") as mock_dispatch:
    ...

monkeypatch.setattr(
    "app.services.rehearsal_media_service.generate_qwen_image",
    fake_generate,
)
```

**What to Mock:**
- External AI, network, and storage boundaries are mocked aggressively in `backend/tests/test_rehearsal_media_service.py` by replacing `generate_qwen_image`, `download_generated_media`, and `upload_generated_media`.
- FastAPI dependency edges and async collaborators are mocked with `MagicMock` and `AsyncMock` in `backend/tests/test_file_generation.py` and `backend/tests/test_ppt_renovation.py`.
- CLI and subprocess boundaries are patched in `backend/tests/test_start_dev_waits.py` and `backend/tests/test_ppt_renovation.py`.
- Configuration access is patched at import or construction time when a module would otherwise read runtime settings, as in `_import_renovation_service()` inside `backend/tests/test_ppt_renovation.py`.

**What NOT to Mock:**
- Pure normalization and transformation helpers are tested directly without mocks in `backend/tests/test_ppt_genai_provider.py`, `backend/tests/test_rehearsal_generation_service.py`, and `backend/tests/test_rehearsal_media_service.py`.
- For new tests, keep prompt builders, parsers of already-available payloads, and immutable action-normalization logic as direct unit tests unless they cross a network, database, or subprocess boundary.

## Fixtures and Factories

**Test Data:**
```python
@dataclass
class FakeChunk:
    content: str
    metadata: dict
```

**Location:**
- Test data is usually defined inline inside the test module itself, as in the `FakeChunk` and `FakeParseResult` dataclasses in `backend/tests/test_file_generation.py`.
- Many tests use literal dict payloads for slide content, outlines, and action lists, as in `backend/tests/test_rehearsal_media_service.py` and `backend/tests/test_rehearsal_generation_service.py`.
- No shared fixtures directory, factory module, or repo-visible `conftest.py` was detected.
- Some API tests rely on fixtures named `client`, `auth_headers`, `db_session`, and `test_user_id` in `backend/tests/test_lesson_plan_api.py`, but no in-repo fixture definition was found. If you add more tests in that style, either add an explicit fixture source or keep the fixture local to the module.

## Coverage

**Requirements:** None enforced. No coverage threshold or coverage config was detected in `backend/pyproject.toml`, repo root config, or `teacher-platform/package.json`.

**View Coverage:**
```bash
# No repository-owned coverage command or config detected
```

## Test Types

**Unit Tests:**
- Pure helper and transformation tests dominate `backend/tests/test_ppt_genai_provider.py`, `backend/tests/test_rehearsal_generation_service.py`, and `backend/tests/test_start_dev_waits.py`.
- Frontend unit coverage is minimal and currently limited to the small composable test in `teacher-platform/src/composables/rehearsalPlaybackEffects.test.js`.

**Integration Tests:**
- Backend API tests exercise FastAPI routes with `httpx.AsyncClient`, `ASGITransport`, dependency overrides, and sometimes real DB session fixtures in `backend/tests/test_file_generation.py` and `backend/tests/test_lesson_plan_api.py`.
- Some service tests integrate multiple internal steps while still mocking the expensive external boundary, such as `backend/tests/test_rehearsal_media_service.py`.

**E2E Tests:**
- Not used. No app-owned Playwright, Cypress, or browser E2E suite was detected for `teacher-platform/` or `backend/`.

## Common Patterns

**Async Testing:**
```python
transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    response = await client.post("/api/v1/ppt/projects/file-generation", data={"source_text": "..."})
```

**Error Testing:**
```python
with pytest.raises(FileNotFoundError, match="未找到 LibreOffice"):
    svc.convert_to_pdf("/tmp/test.pptx", "pptx")

with self.assertRaises(TimeoutError):
    start_dev.wait_for_condition("PostgreSQL", checker, retries=2, interval=0)
```

---

*Testing analysis: 2026-04-12*
