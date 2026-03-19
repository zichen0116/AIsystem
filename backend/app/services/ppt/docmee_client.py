"""
Docmee API proxy client.
"""
import asyncio
import base64
import gzip
import json
import logging
from typing import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DOCMEE_OPEN_URL = "https://open.docmee.cn"


def describe_exception(exc: Exception) -> str:
    """Return a useful exception description even when `str(exc)` is empty."""
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


def build_docmee_client_kwargs(timeout_s: float) -> dict:
    timeout = httpx.Timeout(
        timeout_s,
        connect=min(30.0, timeout_s),
        read=timeout_s,
        write=min(60.0, timeout_s),
        pool=min(60.0, timeout_s),
    )
    return {
        "timeout": timeout,
        "trust_env": settings.DOCMEE_TRUST_ENV,
    }


class DocmeeClient:
    """Docmee API wrapper."""

    def __init__(self):
        self._token: str | None = None

    async def _ensure_token(self) -> str:
        """Get or refresh API token."""
        if self._token:
            return self._token
        self._token = await self.create_api_token()
        return self._token

    async def create_api_token(self, uid: str = "system") -> str:
        """Create API token."""
        async with httpx.AsyncClient(**build_docmee_client_kwargs(30)) as client:
            response = await client.post(
                f"{DOCMEE_OPEN_URL}/api/user/createApiToken",
                headers={
                    "Content-Type": "application/json",
                    "Api-Key": settings.DOCMEE_API_KEY,
                },
                json={"uid": uid, "timeOfHours": 2},
            )
            data = response.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Docmee createApiToken failed: {data.get('message')}")
            return data["data"]["token"]

    async def _request(self, method: str, path: str, timeout_s: float | None = None, **kwargs) -> dict:
        """Perform an authenticated Docmee request."""
        token = await self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["token"] = token
        timeout_s = timeout_s or settings.DOCMEE_REQUEST_TIMEOUT_SECONDS

        async with httpx.AsyncClient(**build_docmee_client_kwargs(timeout_s)) as client:
            response = await client.request(method, f"{DOCMEE_OPEN_URL}{path}", headers=headers, **kwargs)
            data = response.json()
            if data.get("code") != 0:
                if "token" in str(data.get("message", "")).lower():
                    self._token = None
                    token = await self._ensure_token()
                    headers["token"] = token
                    response = await client.request(method, f"{DOCMEE_OPEN_URL}{path}", headers=headers, **kwargs)
                    data = response.json()
                    if data.get("code") != 0:
                        raise RuntimeError(f"Docmee API error: {data.get('message')}")
                else:
                    raise RuntimeError(f"Docmee API error: {data.get('message')}")
            return data

    async def get_templates(self, page: int = 1, size: int = 20, category: str | None = None) -> dict:
        """Get template list."""
        filters = {"type": 1}
        if category:
            filters["category"] = category
        return await self._request(
            "POST",
            "/api/ppt/templates",
            json={"page": page, "size": size, "filters": filters},
        )

    async def create_task(self, content: str, task_type: int = 1) -> str:
        """
        Create a PPT task and return task ID.

        task_type: 1=topic generation, 7=markdown outline
        """
        token = await self._ensure_token()
        async with httpx.AsyncClient(**build_docmee_client_kwargs(30)) as client:
            response = await client.post(
                f"{DOCMEE_OPEN_URL}/api/ppt/v2/createTask",
                headers={"token": token},
                data={"type": str(task_type), "content": content},
            )
            data = response.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Docmee createTask failed: {data.get('message')}")
            return data["data"]["id"]

    async def generate_content_stream(self, task_id: str, **kwargs) -> AsyncIterator[dict]:
        """Stream outline generation content."""
        token = await self._ensure_token()
        body = {"id": task_id, "stream": True, **kwargs}
        async with httpx.AsyncClient(**build_docmee_client_kwargs(120)) as client:
            async with client.stream(
                "POST",
                f"{DOCMEE_OPEN_URL}/api/ppt/v2/generateContent",
                headers={"Content-Type": "application/json", "token": token},
                json=body,
            ) as response:
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    async def generate_content(self, task_id: str, **kwargs) -> dict:
        """Generate outline content in non-streaming mode."""
        body = {"id": task_id, "stream": False, **kwargs}
        return await self._request("POST", "/api/ppt/v2/generateContent", json=body)

    async def update_content_stream(self, task_id: str, markdown: str, question: str = "") -> AsyncIterator[dict]:
        """Stream outline update content."""
        token = await self._ensure_token()
        body = {"id": task_id, "markdown": markdown, "stream": True}
        if question:
            body["question"] = question
        async with httpx.AsyncClient(**build_docmee_client_kwargs(120)) as client:
            async with client.stream(
                "POST",
                f"{DOCMEE_OPEN_URL}/api/ppt/v2/updateContent",
                headers={"Content-Type": "application/json", "token": token},
                json=body,
            ) as response:
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    async def generate_pptx(self, task_id: str, template_id: str, markdown: str) -> dict:
        """Generate PPT and return `pptInfo`."""
        data = await self._request(
            "POST",
            "/api/ppt/v2/generatePptx",
            json={"id": task_id, "templateId": template_id, "markdown": markdown},
            timeout_s=settings.DOCMEE_GENERATE_PPTX_TIMEOUT_SECONDS,
        )
        return data.get("data", {}).get("pptInfo", {})

    async def finalize_ppt_info(
        self,
        ppt_info: dict,
        poll_attempts: int | None = None,
        poll_delay: float | None = None,
    ) -> dict:
        """Reload PPT info until `pptxProperty` is available or retries are exhausted."""
        merged = dict(ppt_info or {})
        ppt_id = merged.get("id")
        if not ppt_id:
            return merged
        poll_attempts = poll_attempts if poll_attempts is not None else settings.DOCMEE_PPTX_POLL_ATTEMPTS
        poll_delay = poll_delay if poll_delay is not None else settings.DOCMEE_PPTX_POLL_DELAY_SECONDS

        upload_status = (merged.get("extInfo") or {}).get("uploadStatus")
        needs_reload = not merged.get("pptxProperty") or upload_status != "ready"
        if not needs_reload:
            return merged

        for attempt in range(max(poll_attempts, 1)):
            loaded = await self.load_pptx(ppt_id)
            for key, value in (loaded or {}).items():
                if value not in (None, "", [], {}):
                    merged[key] = value

            if merged.get("pptxProperty"):
                break

            if attempt < poll_attempts - 1 and poll_delay > 0:
                await asyncio.sleep(poll_delay)

        return merged

    async def load_pptx(self, ppt_id: str) -> dict:
        """Load generated PPT info."""
        data = await self._request("GET", f"/api/ppt/loadPptx?id={ppt_id}", timeout_s=60)
        return data.get("data", {}).get("pptInfo", {})

    async def download_pptx(self, ppt_id: str, refresh: bool = False) -> str:
        """Get PPT download URL."""
        data = await self._request(
            "POST",
            "/api/ppt/downloadPptx",
            json={"id": ppt_id, "refresh": refresh},
        )
        return data.get("data", {}).get("fileUrl", "")

    async def save_pptx(self, ppt_id: str, pptx_property: dict | None = None) -> dict:
        """Save edited PPT."""
        body = {"id": ppt_id, "drawPptx": True, "drawCover": True}
        if pptx_property:
            body["pptxProperty"] = pptx_property
        return await self._request("POST", "/api/ppt/savePptx", json=body)

    @staticmethod
    def decompress_pptx_property(encoded: str) -> dict:
        """Decode pptxProperty: base64 -> gzip -> json."""
        try:
            compressed = base64.b64decode(encoded)
            decompressed = gzip.decompress(compressed)
            return json.loads(decompressed)
        except Exception as exc:
            logger.error("Failed to decompress pptxProperty: %s", exc)
            return {}

    @staticmethod
    def compress_pptx_property(obj: dict) -> str:
        """Encode pptxProperty: json -> gzip -> base64."""
        try:
            json_bytes = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            compressed = gzip.compress(json_bytes)
            return base64.b64encode(compressed).decode("ascii")
        except Exception as exc:
            logger.error("Failed to compress pptxProperty: %s", exc)
            return ""

    @classmethod
    def get_page_count(cls, encoded: str) -> int:
        """Support both `pages` and `slides` structures from Docmee."""
        if not encoded:
            return 0

        obj = cls.decompress_pptx_property(encoded)
        pages = obj.get("pages")
        if isinstance(pages, list):
            return len(pages)

        slides = obj.get("slides")
        if isinstance(slides, list):
            return len(slides)

        return 0


docmee_client = DocmeeClient()
