"""
图片解析器
优先使用 Gemini 生成教学语义，硬失败时回退到旧链路。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from app.services.ai.gemini_multimodal_service import GeminiMultimodalService
from app.services.ai.vision_service import VisionService
from app.services.parsers.base import BaseParser, ParseResult, ParsedChunk

logger = logging.getLogger(__name__)


class ImageParser(BaseParser):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.vision_service = VisionService(api_key=self.api_key) if self.api_key else None
        self.gemini_service = GeminiMultimodalService()

    @property
    def supported_extensions(self) -> list[str]:
        return [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

    async def parse(self, file_path: Path) -> ParseResult:
        file_name = file_path.name
        if not file_path.exists():
            logger.error("图片文件不存在: %s", file_path)
            return ParseResult(chunks=[], images=[])

        if self.gemini_service.is_enabled():
            try:
                return await self._parse_with_gemini(file_path)
            except Exception as exc:
                logger.warning("Gemini image parse failed, fallback to legacy: %s", exc)
                return await self._parse_with_legacy(file_path, fallback_reason=str(exc))

        return await self._parse_with_legacy(file_path, fallback_reason="missing_google_api_key")

    async def _parse_with_gemini(self, file_path: Path) -> ParseResult:
        file_name = file_path.name
        result = await self.gemini_service.analyze_image(str(file_path))
        summary = str(result.get("summary") or "").strip()
        searchable_text = str(result.get("searchable_text") or summary).strip()
        if not searchable_text:
            raise RuntimeError("empty_gemini_image_result")

        metadata = {
            "source": file_name,
            "type": "image_upload",
            "parser_provider": "gemini",
            "image_count": 1,
            "image_descriptions": [{"filename": file_name, "description": summary or searchable_text}],
            "knowledge_points": list(result.get("knowledge_points") or []),
            "style_cues": list(result.get("style_cues") or []),
            "searchable_text": searchable_text,
            "is_partial": False,
        }
        return ParseResult(
            chunks=[ParsedChunk(content=searchable_text, metadata=metadata)],
            images=[str(file_path)],
        )

    async def _parse_with_legacy(self, file_path: Path, fallback_reason: str | None = None) -> ParseResult:
        chunks = []
        images = []
        file_name = file_path.name

        if not self.vision_service:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过图片解析")
            chunks.append(
                ParsedChunk(
                    content=f"[图片文件] {file_name}",
                    metadata={
                        "source": file_name,
                        "type": "image_upload",
                        "status": "no_api_key",
                        "image_count": 0,
                        "image_descriptions": [],
                        "parser_provider": "legacy_fallback",
                        "fallback_reason": fallback_reason or "missing_legacy_api_key",
                        "is_partial": True,
                    },
                )
            )
            return ParseResult(chunks=chunks, images=[])

        try:
            description = await self.vision_service.describe_image(image_path=str(file_path))
            if description and not description.startswith("错误:") and not description.startswith("API "):
                chunk = ParsedChunk(
                    content=description,
                    metadata={
                        "source": file_name,
                        "type": "image_upload",
                        "image_count": 1,
                        "image_descriptions": [{"filename": file_name, "description": description}],
                        "parser_provider": "legacy_fallback" if fallback_reason else "legacy",
                        "fallback_reason": fallback_reason,
                        "searchable_text": description,
                        "is_partial": False,
                    },
                )
                chunks.append(chunk)
                images.append(str(file_path))
            else:
                chunk = ParsedChunk(
                    content=f"[图片文件] {file_name} (解析失败)",
                    metadata={
                        "source": file_name,
                        "type": "image_upload",
                        "status": "parse_failed",
                        "image_count": 0,
                        "image_descriptions": [],
                        "error": description,
                        "parser_provider": "legacy_fallback" if fallback_reason else "legacy",
                        "fallback_reason": fallback_reason or description,
                        "is_partial": True,
                    },
                )
                chunks.append(chunk)
        except Exception as exc:
            logger.error("图片解析异常: %s", exc)
            chunk = ParsedChunk(
                content=f"[图片文件] {file_name} (解析异常)",
                metadata={
                    "source": file_name,
                    "type": "image_upload",
                    "status": "error",
                    "image_count": 0,
                    "image_descriptions": [],
                    "error": str(exc),
                    "parser_provider": "legacy_fallback" if fallback_reason else "legacy",
                    "fallback_reason": fallback_reason or str(exc),
                    "is_partial": True,
                },
            )
            chunks.append(chunk)

        return ParseResult(chunks=chunks, images=images)
