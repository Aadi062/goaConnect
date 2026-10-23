"""
GoaConnect — Cache Service
Redis with automatic in-memory fallback for development.
Never blocks startup if Redis is unavailable.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional
from app.core.logging import get_logger

logger = get_logger("cache")

# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------
_memory: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry_ts or 0)
_redis_client: Any = None
_redis_available: Optional[bool] = None


def _mem_get(key: str) -> Optional[Any]:
    entry = _memory.get(key)
    if entry is None:
        return None
    value, expiry = entry
    if expiry and time.monotonic() > expiry:
        _memory.pop(key, None)
        return None
    return value


def _mem_set(key: str, value: Any, ttl: int = 0) -> None:
    expiry = (time.monotonic() + ttl) if ttl else 0
    _memory[key] = (value, expiry)


def _mem_delete(key: str) -> None:
    _memory.pop(key, None)


# ---------------------------------------------------------------------------
# Redis initialisation
# ---------------------------------------------------------------------------

async def _init_redis(url: str) -> bool:
    global _redis_client, _redis_available
    if _redis_available is not None:
        return _redis_available
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(url, socket_connect_timeout=2, decode_responses=True)
        await client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("redis_connected", url=url)
        return True
    except Exception as exc:
        _redis_available = False
        logger.info("redis_unavailable", reason=str(exc), fallback="in_memory")
        return False


# ---------------------------------------------------------------------------
# Public API — identical surface regardless of backend
# ---------------------------------------------------------------------------

async def get(key: str, redis_url: str = "redis://localhost:6379") -> Optional[Any]:
    """Get a cached value. Returns None on miss or error."""
    await _init_redis(redis_url)
    if _redis_available and _redis_client:
        try:
            raw = await _redis_client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            pass
    return _mem_get(key)


async def set(
    key: str,
    value: Any,
    ttl: int = 300,
    redis_url: str = "redis://localhost:6379",
) -> None:
    """Set a cached value with optional TTL (seconds)."""
    await _init_redis(redis_url)
    if _redis_available and _redis_client:
        try:
            await _redis_client.set(key, json.dumps(value), ex=ttl or None)
            return
        except Exception:
            pass
    _mem_set(key, value, ttl)


async def delete(key: str, redis_url: str = "redis://localhost:6379") -> None:
    """Delete a cached key."""
    if _redis_available and _redis_client:
        try:
            await _redis_client.delete(key)
            return
        except Exception:
            pass
    _mem_delete(key)


def cache_status() -> dict[str, Any]:
    """Return cache backend status for health checks."""
    return {
        "backend": "redis" if _redis_available else "in_memory",
        "redis_available": _redis_available,
        "in_memory_keys": len(_memory),
    }


def reset_cache_state() -> None:
    """Force re-check on next call (used in tests)."""
    global _redis_client, _redis_available
    _redis_client = None
    _redis_available = None
    _memory.clear()
