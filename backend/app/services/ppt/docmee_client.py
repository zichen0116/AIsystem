"""
Docmee API 代理客户端

所有Docmee请求均由后端代理，前端不直连Docmee。
业务主链路优先使用V2接口。
"""
import base64
import gzip
import json
import logging
from typing import AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DOCMEE_OPEN_URL = "https://open.docmee.cn"


class DocmeeClient:
    """Docmee API封装"""

    def __init__(self):
        self._token: str | None = None

    async def _ensure_token(self) -> str:
        """获取或刷新API Token"""
        if self._token:
            return self._token
        self._token = await self.create_api_token()
        return self._token

    async def create_api_token(self, uid: str = "system") -> str:
        """创建API Token"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{DOCMEE_OPEN_URL}/api/user/createApiToken",
                headers={
                    "Content-Type": "application/json",
                    "Api-Key": settings.DOCMEE_API_KEY,
                },
                json={"uid": uid, "timeOfHours": 2},
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Docmee createApiToken failed: {data.get('message')}")
            return data["data"]["token"]

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """通用请求封装，自动附加token"""
        token = await self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["token"] = token

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.request(method, f"{DOCMEE_OPEN_URL}{path}", headers=headers, **kwargs)
            data = resp.json()
            if data.get("code") != 0:
                # token过期时重试一次
                if "token" in str(data.get("message", "")).lower():
                    self._token = None
                    token = await self._ensure_token()
                    headers["token"] = token
                    resp = await client.request(method, f"{DOCMEE_OPEN_URL}{path}", headers=headers, **kwargs)
                    data = resp.json()
                    if data.get("code") != 0:
                        raise RuntimeError(f"Docmee API error: {data.get('message')}")
                else:
                    raise RuntimeError(f"Docmee API error: {data.get('message')}")
            return data

    # ========== 模板 ==========

    async def get_templates(self, page: int = 1, size: int = 20, category: str | None = None) -> dict:
        """获取模板列表"""
        filters = {"type": 1}
        if category:
            filters["category"] = category
        return await self._request(
            "POST", "/api/ppt/templates",
            json={"page": page, "size": size, "filters": filters},
        )

    # ========== V2 任务流程 ==========

    async def create_task(self, content: str, task_type: int = 1) -> str:
        """创建PPT任务，返回任务ID
        type: 1=智能生成, 7=Markdown大纲
        """
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{DOCMEE_OPEN_URL}/api/ppt/v2/createTask",
                headers={"token": token},
                data={"type": str(task_type), "content": content},
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Docmee createTask failed: {data.get('message')}")
            return data["data"]["id"]

    async def generate_content_stream(self, task_id: str, **kwargs) -> AsyncIterator[dict]:
        """流式生成大纲内容"""
        token = await self._ensure_token()
        body = {"id": task_id, "stream": True, **kwargs}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{DOCMEE_OPEN_URL}/api/ppt/v2/generateContent",
                headers={"Content-Type": "application/json", "token": token},
                json=body,
            ) as resp:
                async for line in resp.aiter_lines():
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
        """非流式生成大纲内容"""
        body = {"id": task_id, "stream": False, **kwargs}
        return await self._request("POST", "/api/ppt/v2/generateContent", json=body)

    async def update_content_stream(self, task_id: str, markdown: str, question: str = "") -> AsyncIterator[dict]:
        """流式更新大纲内容"""
        token = await self._ensure_token()
        body = {"id": task_id, "markdown": markdown, "stream": True}
        if question:
            body["question"] = question
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{DOCMEE_OPEN_URL}/api/ppt/v2/updateContent",
                headers={"Content-Type": "application/json", "token": token},
                json=body,
            ) as resp:
                async for line in resp.aiter_lines():
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
        """生成PPT，返回pptInfo"""
        data = await self._request(
            "POST", "/api/ppt/v2/generatePptx",
            json={"id": task_id, "templateId": template_id, "markdown": markdown},
        )
        return data.get("data", {}).get("pptInfo", {})

    async def load_pptx(self, ppt_id: str) -> dict:
        """加载PPT结果"""
        data = await self._request("GET", f"/api/ppt/loadPptx?id={ppt_id}")
        return data.get("data", {}).get("pptInfo", {})

    async def download_pptx(self, ppt_id: str, refresh: bool = False) -> str:
        """获取PPT下载地址"""
        data = await self._request(
            "POST", "/api/ppt/downloadPptx",
            json={"id": ppt_id, "refresh": refresh},
        )
        return data.get("data", {}).get("fileUrl", "")

    async def save_pptx(self, ppt_id: str, pptx_property: dict | None = None) -> dict:
        """保存PPT编辑"""
        body = {"id": ppt_id, "drawPptx": True, "drawCover": True}
        if pptx_property:
            body["pptxProperty"] = pptx_property
        return await self._request("POST", "/api/ppt/savePptx", json=body)

    # ========== 工具方法 ==========

    @staticmethod
    def decompress_pptx_property(encoded: str) -> dict:
        """解压pptxProperty: base64 -> gzip -> json"""
        try:
            compressed = base64.b64decode(encoded)
            decompressed = gzip.decompress(compressed)
            return json.loads(decompressed)
        except Exception as e:
            logger.error(f"Failed to decompress pptxProperty: {e}")
            return {}

    @staticmethod
    def compress_pptx_property(obj: dict) -> str:
        """压缩pptxProperty: json -> gzip -> base64"""
        try:
            json_bytes = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            compressed = gzip.compress(json_bytes)
            return base64.b64encode(compressed).decode("ascii")
        except Exception as e:
            logger.error(f"Failed to compress pptxProperty: {e}")
            return ""


# 全局单例
docmee_client = DocmeeClient()
