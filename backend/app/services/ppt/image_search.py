"""
Automatic image matching for PPT outlines.
"""
import logging
import re

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_API = "https://api.unsplash.com"


def extract_page_titles(markdown: str) -> list[str]:
    """Extract per-page titles from markdown outline content."""
    lines = [line.strip() for line in markdown.split("\n") if line.strip()]
    level3_titles: list[str] = []
    level2_titles: list[str] = []

    for line in lines:
        match = re.match(r"^###\s+(.+)", line)
        if match:
            title = match.group(1).strip()
            if title:
                level3_titles.append(title)
            continue

        match = re.match(r"^##\s+(.+)", line)
        if match:
            title = match.group(1).strip()
            if title:
                level2_titles.append(title)

    return level3_titles or level2_titles


async def translate_to_search_keywords(titles: list[str]) -> list[str]:
    """Translate page titles into concise English search keywords."""
    if not titles:
        return []
    try:
        client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        prompt = (
            "将以下 PPT 页面标题翻译为简短的英文图片搜索关键词（每个标题一行，只输出关键词）：\n"
            + "\n".join(f"- {title}" for title in titles)
        )
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        return [line.strip().lstrip("- ").strip() for line in text.split("\n") if line.strip()]
    except Exception as exc:
        logger.warning(f"Failed to translate titles to keywords: {exc}")
        return titles


async def search_unsplash(keyword: str) -> list[str]:
    """Search Unsplash landscape images and return up to 2 URLs."""
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{UNSPLASH_API}/search/photos",
                params={"query": keyword, "orientation": "landscape", "per_page": 2},
                headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
            )
            data = response.json()
            urls = []
            for item in data.get("results", [])[:2]:
                url = item.get("urls", {}).get("regular", "")
                if url:
                    urls.append(url)
            return urls
    except Exception as exc:
        logger.warning(f"Unsplash search failed for '{keyword}': {exc}")
        return []


async def auto_assign_images(markdown: str) -> dict[str, list[str]]:
    """
    Match outline pages with image candidates.

    Returns: {"0": [url1, url2], "1": [url1, url2], ...}
    """
    try:
        titles = extract_page_titles(markdown)
        if not titles:
            return {}

        keywords = await translate_to_search_keywords(titles)
        image_urls: dict[str, list[str]] = {}

        for index, keyword in enumerate(keywords):
            urls = await search_unsplash(keyword)
            if urls:
                image_urls[str(index)] = urls

        logger.info("Auto image assignment: %s/%s pages got images", len(image_urls), len(titles))
        return image_urls
    except Exception as exc:
        logger.error(f"Auto image assignment failed: {exc}")
        return {}
