"""
自动配图服务

从大纲中提取页面标题，通过LLM翻译为英文关键词，调用Unsplash搜索横版图片。
配图失败不阻塞后续流程。
"""
import logging
import re

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_API = "https://api.unsplash.com"


def extract_page_titles(markdown: str) -> list[str]:
    """从Markdown大纲中提取页面标题（一级和二级标题）"""
    titles = []
    for line in markdown.split("\n"):
        line = line.strip()
        match = re.match(r"^#{1,2}\s+(.+)", line)
        if match:
            title = match.group(1).strip()
            if title:
                titles.append(title)
    return titles


async def translate_to_search_keywords(titles: list[str]) -> list[str]:
    """使用LLM将中文标题翻译为英文图片搜索关键词"""
    if not titles:
        return []
    try:
        client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        prompt = (
            "将以下PPT页面标题翻译为简短的英文图片搜索关键词（每个标题一行，只输出关键词）：\n"
            + "\n".join(f"- {t}" for t in titles)
        )
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        keywords = [line.strip().lstrip("- ").strip() for line in text.split("\n") if line.strip()]
        return keywords
    except Exception as e:
        logger.warning(f"Failed to translate titles to keywords: {e}")
        return titles


async def search_unsplash(keyword: str) -> str | None:
    """搜索Unsplash横版图片，返回图片URL"""
    if not settings.UNSPLASH_ACCESS_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{UNSPLASH_API}/search/photos",
                params={
                    "query": keyword,
                    "orientation": "landscape",
                    "per_page": 1,
                },
                headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
            )
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results[0].get("urls", {}).get("regular", "")
    except Exception as e:
        logger.warning(f"Unsplash search failed for '{keyword}': {e}")
    return None


async def auto_assign_images(markdown: str) -> dict:
    """
    自动配图主入口

    返回: {page_index: image_url} 映射
    配图失败返回空字典，不抛异常
    """
    try:
        titles = extract_page_titles(markdown)
        if not titles:
            return {}

        keywords = await translate_to_search_keywords(titles)
        image_urls = {}

        for i, kw in enumerate(keywords):
            url = await search_unsplash(kw)
            if url:
                image_urls[str(i)] = url

        logger.info(f"Auto image assignment: {len(image_urls)}/{len(titles)} pages got images")
        return image_urls
    except Exception as e:
        logger.error(f"Auto image assignment failed: {e}")
        return {}
