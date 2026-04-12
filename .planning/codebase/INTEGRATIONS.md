# External Integrations

**Analysis Date:** 2026-04-12

## APIs & External Services

**LLM / Multimodal AI:**
- Alibaba DashScope - primary AI provider for chat, embeddings, rerank, ASR, TTS, vision, and rehearsal image generation.
  - SDK/Client: `httpx` wrappers in `backend/app/services/ai/dashscope_service.py`, `backend/app/services/ai/vision_service.py`, `backend/app/services/ai/asr_service.py`, `backend/app/services/tts_service.py`, `backend/app/services/rag/reranker.py`, `backend/app/services/rag/graph_store.py`, and `backend/app/services/rehearsal_media_service.py`.
  - Auth: `DASHSCOPE_API_KEY` from `backend/app/core/config.py`.
- Google Gemini / GenAI - PPT text/image generation provider in `backend/app/generators/ppt/banana_providers.py`.
  - SDK/Client: `google-genai` via `genai.Client`.
  - Auth: `GOOGLE_API_KEY`, optional `GOOGLE_API_BASE`.
- OpenAI-compatible chat endpoints - HTML mini-game chat and lesson-plan streaming use generic OpenAI-compatible `/chat/completions` APIs in `backend/app/services/html_llm.py` and `backend/app/services/lesson_plan_service.py`.
  - SDK/Client: `httpx`.
  - Auth: `HTML_LLM_API_KEY`, plus `HTML_LLM_BASE_URL` and `HTML_LLM_MODEL`.
- OpenAI / Anthropic provider paths - PPT providers support direct OpenAI and Anthropic clients in `backend/app/generators/ppt/banana_providers.py`.
  - SDK/Client: `openai.OpenAI`, `anthropic.Anthropic`.
  - Auth: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.

**Search / Workflow APIs:**
- Dify Workflow - resource recommendation workflow invoked from `backend/app/services/dify_resource_recommend.py` and exposed by `backend/app/api/resource_search.py`.
  - SDK/Client: `httpx.AsyncClient`.
  - Auth: `DIFY_RESOURCE_WORKFLOW_API_KEY`, plus `DIFY_API_BASE_URL`.
- Tavily Web Search - preferred web search tool inside agent tooling in `backend/app/services/ai/tools.py`.
  - SDK/Client: `tavily.TavilyClient`.
  - Auth: `TAVILY_API_KEY`.
- DuckDuckGo Search - fallback web search in `backend/app/services/ai/tools.py`.
  - SDK/Client: `duckduckgo_search.DDGS`.
  - Auth: none.

**Document / Media Processing:**
- MinerU - remote document parsing for PPT/PDF extraction in `backend/app/generators/ppt/ppt_parse_service.py`.
  - SDK/Client: `requests` against `MINERU_API_BASE`.
  - Auth: `MINERU_TOKEN`.
- iFlytek Virtual Human / Avatar Platform - digital human session control and browser-side avatar streaming in `backend/app/api/digital_human.py`, `backend/app/services/iflytek_vms_client.py`, and `teacher-platform/src/components/DigitalHumanAssistant.vue`.
  - SDK/Client: backend `httpx` + HMAC signing in `backend/app/services/iflytek_vms_auth.py`; frontend dynamically imports bundled SDK from `teacher-platform/src/libs/avatar-sdk-web_3.1.2.1002/index.js`.
  - Auth: `IFLYTEK_VMS_APP_ID`, `IFLYTEK_VMS_API_KEY`, `IFLYTEK_VMS_API_SECRET`, plus scene/avatar settings in `backend/app/core/config.py`.
- iFlytek dev proxy endpoints - local frontend development proxies `/vmss` and `/individuation` to iFlytek domains in `teacher-platform/vite.config.js`.
  - SDK/Client: Vite dev proxy.
  - Auth: handled by proxied SDK/browser requests.

**Communications:**
- QQ SMTP - email verification in `backend/app/services/email.py`.
  - SDK/Client: Python `smtplib`.
  - Auth: `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`.
- Aliyun Market SMS - phone verification in `backend/app/services/sms.py`.
  - SDK/Client: `httpx.AsyncClient`.
  - Auth: `SMS_APPCODE`.

**Storage-adjacent services:**
- Alibaba OSS - upload/download for knowledge assets, generated media, ASR audio staging, and PPT export assets in `backend/app/services/oss_service.py`, `backend/app/generators/ppt/file_service.py`, and `backend/app/services/ai/asr_service.py`.
  - SDK/Client: `oss2`.
  - Auth: `OSS_ENDPOINT`, `OSS_BUCKET`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`.

**Config-only placeholders (no active call site detected beyond `backend/app/core/config.py`):**
- SiliconFlow, Docmee, Unsplash, and Baidu API fields exist in `backend/app/core/config.py`, but concrete client usage is not detected in the current code paths I read.

## Data Storage

**Databases:**
- PostgreSQL
  - Connection: `DATABASE_URL`, `DATABASE_URL_SYNC` in `backend/app/core/config.py`, `backend/app/core/database.py`, and `backend/alembic/env.py`.
  - Client: SQLAlchemy asyncio + `asyncpg` in `backend/app/core/database.py`.
- Neo4j
  - Connection: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `backend/app/core/config.py`.
  - Client: LightRAG `Neo4JStorage` wrapper in `backend/app/services/rag/graph_store.py`.
- Chroma vector store
  - Connection: local persist dir `CHROMA_PERSIST_DIR` from `backend/app/core/config.py`.
  - Client: `langchain_chroma.Chroma` in `backend/app/services/rag/vector_store.py`.

**File Storage:**
- Alibaba OSS for durable object storage in `backend/app/services/oss_service.py` and `backend/app/generators/ppt/file_service.py`.
- Local filesystem also stores generated artifacts under `backend/media` mounted by `backend/app/main.py` and persisted as `media_files` in `backend/docker-compose.yml`.

**Caching:**
- Redis for Celery broker/result backend, verification-code TTL storage, and ad hoc cache helpers in `backend/app/celery.py`, `backend/app/services/email.py`, `backend/app/services/sms.py`, and `backend/app/services/redis_service.py`.
- In-process LRU caching exists for LightRAG instances in `backend/app/services/rag/graph_store.py`.

## Authentication & Identity

**Auth Provider:**
- Custom JWT auth
  - Implementation: bearer-token auth in `backend/app/core/auth.py` and JWT helpers in `backend/app/core/jwt.py`; frontend stores the access token in `localStorage` via `teacher-platform/src/api/http.js`.

**Identity verification add-ons:**
- Email verification through QQ SMTP in `backend/app/services/email.py`.
- SMS verification through Aliyun Market SMS in `backend/app/services/sms.py`.

## Monitoring & Observability

**Error Tracking:**
- None detected. No Sentry, Datadog, OpenTelemetry, or similar integration is referenced in `backend/app/` or `teacher-platform/src/`.

**Logs:**
- Backend uses Python stdlib logging with a stdout `StreamHandler` in `backend/app/core/logging_setup.py`.
- Service modules log operational events directly via `logging.getLogger(__name__)`, e.g. `backend/app/services/ai/dashscope_service.py`, `backend/app/tasks.py`, and `backend/app/services/rag/graph_store.py`.

## CI/CD & Deployment

**Hosting:**
- Self-managed container stack defined in `backend/docker-compose.yml` with services for frontend, backend app, Celery worker, PostgreSQL, and Redis.
- Backend image is built from `backend/Dockerfile`; frontend image is built from `teacher-platform/Dockerfile`.

**CI Pipeline:**
- None detected. No repo-level `.github/workflows/` or other CI manifest is present outside dependency `node_modules`.

## Environment Configuration

**Required env vars:**
- Core runtime: `DATABASE_URL`, `DATABASE_URL_SYNC`, `REDIS_URL`, `JWT_SECRET_KEY` from `backend/app/core/config.py`.
- DashScope stack: `DASHSCOPE_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `RERANK_MODEL`, `TTS_MODEL`, `TTS_VOICE`, `ASR_MODEL`, `VISION_MODEL`, `REHEARSAL_IMAGE_MODEL`, `REHEARSAL_IMAGE_BASE_URL`.
- Storage and graph: `OSS_ENDPOINT`, `OSS_BUCKET`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`, `CHROMA_PERSIST_DIR`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `LIGHTRAG_WORKING_DIR`.
- External workflows/providers: `DIFY_API_BASE_URL`, `DIFY_RESOURCE_WORKFLOW_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_API_BASE`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HTML_LLM_API_KEY`, `HTML_LLM_BASE_URL`, `HTML_LLM_MODEL`, `MINERU_TOKEN`, `MINERU_API_BASE`, `TAVILY_API_KEY`.
- Digital human: `IFLYTEK_VMS_APP_ID`, `IFLYTEK_VMS_API_KEY`, `IFLYTEK_VMS_API_SECRET`, `IFLYTEK_VMS_SERVICE_ID`, `IFLYTEK_VMS_DEFAULT_AVATAR_ID`, `IFLYTEK_AVATAR_SERVER_URL`, `IFLYTEK_AVATAR_SCENE_ID`, `IFLYTEK_AVATAR_TTS_VCN`.
- Communications: `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASSWORD`, `SMS_APPCODE`.
- Frontend: `VITE_API_BASE` consumed by `teacher-platform/src/api/http.js`.

**Secrets location:**
- `backend/.env` file is present and is the backend settings source referenced by `backend/app/core/config.py`.
- `backend/.env.example` is present as the non-secret template.
- `teacher-platform/.env.development` is present for frontend dev-time variables.
- `backend/docker-compose.yml` also injects several dev-time environment values directly for local containers.

## Webhooks & Callbacks

**Incoming:**
- None detected. The code exposes REST endpoints and streaming responses (for example in `backend/app/api/rehearsal.py` and `backend/app/api/html_chat.py`), but no inbound webhook receiver is evident.

**Outgoing:**
- Direct HTTP API calls to DashScope, Dify, MinerU, iFlytek VMS, and Aliyun SMS from the service modules listed above.
- No webhook registration or callback subscription flow is detected.

---

*Integration audit: 2026-04-12*
