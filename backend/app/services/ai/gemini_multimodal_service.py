from __future__ import annotations

import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiMultimodalService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.GOOGLE_API_KEY
        self.api_base = (settings.GOOGLE_API_BASE or "https://generativelanguage.googleapis.com").rstrip("/")
        self.image_model = settings.IMAGE_CAPTION_MODEL or settings.TEXT_MODEL or "gemini-2.0-flash"
        self.text_model = settings.TEXT_MODEL or "gemini-2.0-flash"
        self.timeout = settings.GENAI_TIMEOUT

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    async def analyze_image(self, image_path: str, *, prompt: str | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("missing_google_api_key")

        path = Path(image_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        prompt = prompt or (
            "请分析这份教学参考图片，提取其中可用于课件生成的关键信息。"
            "以 JSON 返回，字段包含 summary、knowledge_points、style_cues、searchable_text。"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": encoded}},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        text = await self._generate(self.image_model, payload)
        parsed = self._parse_json_text(text)
        return {
            "summary": parsed.get("summary") or "",
            "knowledge_points": parsed.get("knowledge_points") or [],
            "style_cues": parsed.get("style_cues") or [],
            "searchable_text": parsed.get("searchable_text") or parsed.get("summary") or text,
            "raw_text": text,
        }

    async def summarize_video(
        self,
        *,
        file_name: str,
        transcript_text: str,
        frame_summaries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("missing_google_api_key")

        prompt = (
            "你是一名教学资源解析助手。请根据视频转写和关键帧摘要，"
            "提取适合课件生成的知识点、案例、实验步骤和检索文本。"
            "以 JSON 返回，字段包含 summary、knowledge_points、teaching_cases、time_segments、searchable_text。"
        )
        frame_text = "\n".join(
            f"- {item.get('timestamp_label') or item.get('timestamp')}: {item.get('description')}"
            for item in frame_summaries
            if str(item.get("description") or "").strip()
        )
        input_text = (
            f"文件名：{file_name}\n\n"
            f"视频转写：\n{transcript_text or '暂无转写'}\n\n"
            f"关键帧摘要：\n{frame_text or '暂无关键帧摘要'}"
        )
        payload = {
            "contents": [{"parts": [{"text": f"{prompt}\n\n{input_text}"}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        text = await self._generate(self.text_model, payload)
        parsed = self._parse_json_text(text)
        return {
            "summary": parsed.get("summary") or "",
            "knowledge_points": parsed.get("knowledge_points") or [],
            "teaching_cases": parsed.get("teaching_cases") or [],
            "time_segments": parsed.get("time_segments") or [],
            "searchable_text": parsed.get("searchable_text") or parsed.get("summary") or text,
            "raw_text": text,
        }

    async def _generate(self, model: str, payload: dict[str, Any]) -> str:
        url = f"{self.api_base}/v1beta/models/{model}:generateContent"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        return self._extract_text(data)

    def _extract_text(self, data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        for candidate in candidates:
            content = candidate.get("content") or {}
            for part in content.get("parts") or []:
                text = str(part.get("text") or "").strip()
                if text:
                    return text
        raise RuntimeError("empty_gemini_response")

    def _parse_json_text(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {"summary": cleaned}
        except Exception:
            logger.warning("Failed to parse Gemini multimodal JSON response")
            return {"summary": cleaned}
