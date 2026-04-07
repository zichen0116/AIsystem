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
