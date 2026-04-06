"""Shared async Redis singleton."""

import redis.asyncio as aioredis
from app.core.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def get_ppt_cover(project_id: int) -> str | None:
    """Get cached PPT cover URL. Returns None on cache miss."""
    r = await get_redis()
    return await r.get(f"ppt:cover:{project_id}")


async def set_ppt_cover(project_id: int, cover_url: str, ttl: int = 86400):
    """Cache PPT cover URL with TTL (default 24h)."""
    r = await get_redis()
    await r.set(f"ppt:cover:{project_id}", cover_url, ex=ttl)


async def invalidate_ppt_cover(project_id: int):
    """Delete cached PPT cover."""
    r = await get_redis()
    await r.delete(f"ppt:cover:{project_id}")
