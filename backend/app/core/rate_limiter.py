"""
Distributed rate limiter for login endpoints.

Uses Redis so limits are enforced across all workers and processes.
Falls back to an in-process dict automatically when Redis is unavailable
(e.g. local development without Docker), so the app never crashes.

IP extraction is proxy-aware but safe:
  - X-Real-IP and X-Forwarded-For are only trusted when the TCP connection
    itself came from a configured TRUSTED_PROXY_IPS address (default: 127.0.0.1).
  - A client connecting from any other IP cannot forge these headers to
    bypass rate-limiting or misrepresent its identity in audit logs.
  - Both headers are validated as proper IP literals before use.
"""

import ipaddress
import logging
import time
from typing import Optional

import redis
from fastapi import HTTPException, Request, status

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_ATTEMPTS  = 5
BLOCK_SECONDS = 900   # 15 minutes

_FAIL_PREFIX  = "ratelimit:fail:"
_BLOCK_PREFIX = "ratelimit:block:"


# ── In-process fallback (single-worker / dev only) ───────────────────────────
_fallback_attempts: dict = {}
_fallback_blocked: dict  = {}   # ip → blocked_at timestamp


# ── Public helpers ────────────────────────────────────────────────────────────

def get_real_ip(request: Request) -> str:
    """
    Return the genuine client IP.

    Proxy headers (X-Real-IP, X-Forwarded-For) are ONLY trusted when the
    actual TCP connection came from a known trusted proxy IP.  If the request
    arrives from any other address, those headers are ignored — returning the
    raw TCP peer instead — so an attacker cannot forge them to spoof their IP.

    Priority (when connection is from a trusted proxy):
      1. X-Real-IP          — nginx sets this to $remote_addr; most precise
      2. X-Forwarded-For    — leftmost address; correct behind a single proxy
      3. TCP peer           — fallback (direct connection or unknown proxy)
    """
    from app.core.config import settings

    def _valid_ip(value: str) -> Optional[str]:
        """Return the stripped value if it is a valid IP literal, else None."""
        value = value.strip()
        try:
            ipaddress.ip_address(value)
            return value
        except ValueError:
            return None

    # Actual TCP peer — always available, cannot be forged at the network layer
    tcp_peer = request.client.host if request.client else "unknown"

    # Only trust proxy-injected headers when the TCP connection itself came
    # from a configured trusted proxy.  An untrusted source could inject
    # arbitrary X-Forwarded-For values to bypass per-IP rate limiting.
    if tcp_peer in settings.TRUSTED_PROXY_IPS:
        # X-Real-IP — nginx sets this to $remote_addr (most trustworthy source)
        ip = _valid_ip(request.headers.get("X-Real-IP", ""))
        if ip:
            return ip

        # X-Forwarded-For: client, proxy1, proxy2  →  take leftmost entry
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            ip = _valid_ip(forwarded_for.split(",")[0])
            if ip:
                return ip

    # Direct connection or untrusted proxy — use the raw TCP peer
    return tcp_peer


def check_ip_blocked(ip: str) -> None:
    """Raise HTTP 429 if this IP is currently blocked.

    If Redis is reachable, uses the distributed store.
    On any Redis error, falls back to the in-process store so blocked IPs
    are never silently let through.
    """
    r = get_redis()
    if r is not None:
        try:
            _redis_check_blocked(r, ip)
            return
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Redis check_blocked failed for %s, using fallback: %s", ip, exc)
    _fallback_check_blocked(ip)


def record_failed(ip: str) -> None:
    """Increment failure counter; block the IP when the threshold is reached."""
    r = get_redis()
    if r is not None:
        try:
            _redis_record_failed(r, ip)
            return
        except Exception as exc:
            logger.warning("Redis record_failed failed for %s, using fallback: %s", ip, exc)
    _fallback_record_failed(ip)


def record_success(ip: str) -> None:
    """Clear all rate-limit state for this IP on a successful login."""
    r = get_redis()
    if r is not None:
        try:
            _redis_record_success(r, ip)
            return
        except Exception as exc:
            logger.warning("Redis record_success failed for %s, using fallback: %s", ip, exc)
    _fallback_record_success(ip)


# ── Redis implementation ──────────────────────────────────────────────────────

def _redis_check_blocked(r: redis.Redis, ip: str) -> None:
    ttl = r.ttl(f"{_BLOCK_PREFIX}{ip}")
    if ttl > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {ttl} seconds.",
        )


def _redis_record_failed(r: redis.Redis, ip: str) -> None:
    fail_key  = f"{_FAIL_PREFIX}{ip}"
    block_key = f"{_BLOCK_PREFIX}{ip}"

    pipe = r.pipeline()
    pipe.incr(fail_key)
    pipe.ttl(fail_key)
    count, current_ttl = pipe.execute()

    # Set expiry on first failure so stale counters self-clean
    if current_ttl < 0:
        r.expire(fail_key, BLOCK_SECONDS)

    if count >= MAX_ATTEMPTS:
        r.setex(block_key, BLOCK_SECONDS, "1")
        r.delete(fail_key)
        logger.warning("IP blocked (Redis) after %d failed logins: %s", count, ip)


def _redis_record_success(r: redis.Redis, ip: str) -> None:
    r.delete(f"{_FAIL_PREFIX}{ip}", f"{_BLOCK_PREFIX}{ip}")


# ── In-process fallback implementation ───────────────────────────────────────

def _fallback_check_blocked(ip: str) -> None:
    if ip in _fallback_blocked:
        blocked_at = _fallback_blocked[ip]
        remaining  = int(BLOCK_SECONDS - (time.time() - blocked_at))
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed attempts. Try again in {remaining} seconds.",
            )
        else:
            _fallback_blocked.pop(ip, None)
            _fallback_attempts.pop(ip, None)


def _fallback_record_failed(ip: str) -> None:
    _fallback_attempts[ip] = _fallback_attempts.get(ip, 0) + 1
    if _fallback_attempts[ip] >= MAX_ATTEMPTS:
        _fallback_blocked[ip] = time.time()
        _fallback_attempts.pop(ip, None)
        logger.warning("IP blocked (in-process fallback) after failed logins: %s", ip)


def _fallback_record_success(ip: str) -> None:
    _fallback_attempts.pop(ip, None)
    _fallback_blocked.pop(ip, None)
