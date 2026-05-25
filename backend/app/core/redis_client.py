"""
Shared Redis connection pool.

A single module-level client is created on first successful connection and
reused by all consumers (rate limiter, token blacklist, etc.).  Never caches
a failed attempt — retries on every call so the app automatically picks up
Redis after a startup delay or transient outage.
"""

import logging
from typing import Optional

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Return a live Redis client, or None if Redis is unreachable."""
    global _client
    if _client is not None:
        return _client
    try:
        r = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        r.ping()
        _client = r
        logger.info("Redis connected at %s", settings.REDIS_URL)
        return _client
    except Exception as exc:
        logger.warning("Redis unavailable (%s).", exc)
        return None   # Not cached — next call will retry
