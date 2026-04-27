from pathlib import Path
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_image_parser_falls_back_to_legacy_on_gemini_hard_failure(tmp_path):
    from app.services.parsers.base import ParseResult, ParsedChunk
    from app.services.parsers.image_parser import ImageParser

    image_path = tmp_path / "demo.png"
    image_path.write_bytes(b"fake-image")

    parser = ImageParser()
    parser._parse_with_gemini = AsyncMock(side_effect=RuntimeError("timeout"))
    parser._parse_with_legacy = AsyncMock(
        return_value=ParseResult(
            chunks=[
                ParsedChunk(
                    content="legacy image result",
                    metadata={"parser_provider": "legacy_fallback", "fallback_reason": "timeout"},
                )
            ],
            images=[str(image_path)],
        )
    )

    result = await parser.parse(image_path)

    assert result.chunks[0].metadata["parser_provider"] == "legacy_fallback"
    assert result.chunks[0].metadata["fallback_reason"] == "timeout"


@pytest.mark.asyncio
async def test_video_parser_falls_back_to_legacy_on_gemini_hard_failure(tmp_path):
    from app.services.parsers.base import ParseResult, ParsedChunk
    from app.services.parsers.video_parser import VideoParser

    video_path = tmp_path / "demo.mp4"
    video_path.write_bytes(b"fake-video")

    parser = VideoParser()
    parser._parse_with_gemini = AsyncMock(side_effect=RuntimeError("quota exceeded"))
    parser._parse_with_legacy = AsyncMock(
        return_value=ParseResult(
            chunks=[
                ParsedChunk(
                    content="legacy video result",
                    metadata={"parser_provider": "legacy_fallback", "fallback_reason": "quota exceeded"},
                )
            ],
            images=[],
        )
    )

    result = await parser.parse(video_path)

    assert result.chunks[0].metadata["parser_provider"] == "legacy_fallback"
    assert result.chunks[0].metadata["fallback_reason"] == "quota exceeded"
