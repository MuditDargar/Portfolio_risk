"""
Covariance-matrix / metric cache — Section 2 ("Redis caches the covariance
matrix per portfolio so it isn't recomputed on every keystroke").

Redis is optional: if REDIS_URL is unset (e.g. a free-tier deployment without
a Redis add-on), the cache transparently falls back to an in-process dict.
Both paths are keyed by "portfolio_id:holdings_hash" so a stale entry is
naturally invalidated whenever holdings change.
"""
from __future__ import annotations

import json
from typing import Any

from .config import get_settings

settings = get_settings()

_memory_cache: dict[str, str] = {}
_redis_client = None

if settings.redis_url:
    import redis

    _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def cache_get(key: str) -> Any | None:
    raw = _redis_client.get(key) if _redis_client else _memory_cache.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    raw = json.dumps(value)
    if _redis_client:
        _redis_client.set(key, raw, ex=ttl_seconds)
    else:
        _memory_cache[key] = raw
