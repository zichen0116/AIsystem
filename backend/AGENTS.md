# Repository Guidelines

## Project Structure & Module Organization
This repository is the FastAPI backend for the multimodal AI teaching platform. Application code lives in `app/`: API routers in `app/api/`, configuration and database setup in `app/core/`, SQLAlchemy models in `app/models/`, request/response schemas in `app/schemas/`, business logic in `app/services/`, and PPT generation code in `app/generators/`. Database migrations are in `alembic/`. Tests are in `tests/`. Runtime and generated assets are stored under `media/`, `uploads/`, `logs/`, and `chroma_data/`; do not treat these as source modules.

## Build, Test, and Development Commands
Install dependencies with:

```powershell
pip install -r requirements.txt
```

Run the API locally:

```powershell
python run.py
```

Start the full development stack, including Redis, PostgreSQL, FastAPI, and Celery:

```powershell
python start_dev.py
```

Run tests:

```powershell
pytest tests -q
```

Run a focused test while iterating:

```powershell
pytest tests/test_lesson_plan_api.py -q
```


## Coding Style & Naming Conventions
Use Python 3.11+ and follow PEP 8 with 4-space indentation. Prefer explicit type hints on public functions and service boundaries. Name modules and functions with `snake_case`, classes and Pydantic/SQLAlchemy models with `PascalCase`, and constants or environment keys with `UPPER_SNAKE_CASE`. Keep routers thin; place business rules in `app/services/` and persistence definitions in `app/models/`.

## Testing Guidelines
The project uses `pytest`. Add tests under `tests/` using the `test_*.py` naming pattern and descriptive test function names such as `test_lesson_plan_delete_removes_references`. Prefer focused unit tests for parsing, prompt helpers, and service logic; add API tests when changing route behavior. Run the relevant focused tests first, then `pytest tests -q` before submitting larger changes.

## Commit & Pull Request Guidelines
Recent history uses short subjects with prefixes such as `feat:`, `bugfix:`, and `docs:`. Keep commits concise and imperative, for example `feat: add rehearsal media cleanup` or `bugfix: handle empty PPT export`. Pull requests should include a short summary, test evidence, linked issue or task when available, and screenshots or sample outputs for user-visible API/generated-asset changes.

## Security & Configuration Tips
Local secrets belong in `.env`; keep `.env.example` safe and non-sensitive. Do not commit API keys, generated media, uploaded files, Chroma data, logs, or database dumps. When adding configuration, define defaults in `app/core/config.py` and document required environment variables in `.env.example`.
