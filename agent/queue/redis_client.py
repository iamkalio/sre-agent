"""Shared async Redis client."""

from __future__ import annotations

import redis.asyncio as aioredis

from agent.config import settings

_pool: aioredis.Redis | None = None

STREAM_KEY = "sre:alerts"
CONSUMER_GROUP = "sre-investigators"
DEDUP_PREFIX = "sre:dedup:"


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=10,
        )
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
