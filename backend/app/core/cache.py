"""
Thin Redis cache wrapper.

Usage:
    from app.core.cache import cache_get, cache_set, cache_delete_pattern

    val = cache_get("key")
    if val is None:
        val = expensive_query()
        cache_set("key", val, ttl=30)
"""

import json
from typing import Any, Optional

import redis

from app.core.config import settings

_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1,
                socket_connect_timeout=1,
            )
            _client.ping()
        except Exception:
            _client = None
    return _client


def cache_get(key: str) -> Optional[Any]:
    try:
        c = _get_client()
        if c is None:
            return None
        val = c.get(key)
        return json.loads(val) if val is not None else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    try:
        c = _get_client()
        if c is None:
            return
        c.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    try:
        c = _get_client()
        if c:
            c.delete(key)
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    try:
        c = _get_client()
        if c is None:
            return
        keys = c.keys(pattern)
        if keys:
            c.delete(*keys)
    except Exception:
        pass
