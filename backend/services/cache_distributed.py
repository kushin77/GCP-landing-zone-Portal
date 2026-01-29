"""
Distributed caching strategy with multi-tier architecture.
Fixes issue #45: Missing Distributed Caching Strategy.

Provides:
- Multi-tier caching (request → Redis → database)
- Cache invalidation strategy
- Thundering herd protection
- Metrics and monitoring
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypeVar

import aioredis

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Cache Configuration
# ============================================================================

CACHE_TTL_CONFIG = {
    "projects:list": 300,  # 5 minutes
    "project:details": 600,  # 10 minutes
    "compliance:scores": 3600,  # 1 hour
    "compliance:details": 1800,  # 30 minutes
    "costs:daily": 86400,  # 1 day
    "costs:summary": 3600,  # 1 hour
    "user:permissions": 600,  # 10 minutes
    "resource:list": 1800,  # 30 minutes
    "audit:summary": 3600,  # 1 hour
}


# ============================================================================
# Cache Locks (Thundering Herd Prevention)
# ============================================================================


class CacheLock:
    """Distributed lock for cache updates."""

    def __init__(self, redis_client: aioredis.Redis, key: str, ttl: int = 10):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.lock_value = str(datetime.utcnow().timestamp())

    async def __aenter__(self):
        """Acquire lock."""
        max_retries = 10
        retry_delay = 0.1

        for attempt in range(max_retries):
            # Try to set lock (only if not exists)
            acquired = await self.redis.set(self.key, self.lock_value, ex=self.ttl, nx=True)

            if acquired:
                logger.debug(f"Lock acquired: {self.key}")
                return self

            # Wait before retry
            await asyncio.sleep(retry_delay * (2**attempt))  # Exponential backoff

        raise TimeoutError(f"Could not acquire lock: {self.key}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        # Only delete if we still own it
        current_value = await self.redis.get(self.key)
        if current_value == self.lock_value.encode():
            await self.redis.delete(self.key)
            logger.debug(f"Lock released: {self.key}")


# ============================================================================
# Multi-Tier Cache
# ============================================================================


class CacheService:
    """Multi-tier caching: request scope → Redis → database."""

    def __init__(self, redis_url: str):
        self.redis: Optional[aioredis.Redis] = None
        self.redis_url = redis_url
        self.request_cache: Dict[str, Any] = {}  # In-process cache

    async def connect(self):
        """Connect to Redis."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("Cache service connected to Redis")

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Cache service disconnected from Redis")

    async def get(self, key: str, fetch_fn: Callable, ttl: Optional[int] = None) -> Any:
        """
        Get value with multi-tier fallback.

        Strategy:
        1. Check request-scoped cache (fastest)
        2. Check Redis cache (fast)
        3. Fetch from database with lock to prevent thundering herd
        4. Store in both caches
        """
        # Level 1: Request cache
        if key in self.request_cache:
            logger.debug(f"Cache hit (request): {key}")
            return self.request_cache[key]

        # Level 2: Redis cache
        if self.redis:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache hit (redis): {key}")
                try:
                    result = json.loads(value)
                    self.request_cache[key] = result
                    return result
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode cached value: {key}")
                    await self.redis.delete(key)

        # Level 3: Database fetch with lock
        logger.debug(f"Cache miss: {key}")

        if not self.redis:
            # Redis not available, fetch directly
            value = await fetch_fn()
            self.request_cache[key] = value
            return value

        # Use lock to prevent thundering herd (only one request fetches from DB)
        lock = CacheLock(self.redis, key)

        try:
            async with lock:
                # Double-check after lock (another request may have fetched)
                redis_value = await self.redis.get(key)
                if redis_value:
                    result = json.loads(redis_value)
                    self.request_cache[key] = result
                    return result

                # Fetch from database
                value = await fetch_fn()

                # Store in both caches
                self.request_cache[key] = value

                # Determine TTL
                cache_ttl = ttl
                if not cache_ttl:
                    # Infer from key pattern
                    for pattern, default_ttl in CACHE_TTL_CONFIG.items():
                        if pattern in key:
                            cache_ttl = default_ttl
                            break
                    cache_ttl = cache_ttl or 300  # Default 5 minutes

                # Store in Redis
                await self.redis.setex(key, cache_ttl, json.dumps(value, default=str))
                logger.debug(f"Cached: {key} (ttl={cache_ttl}s)")

                return value

        except TimeoutError:
            # Could not acquire lock, wait and retry reading from cache
            logger.warning(f"Could not acquire cache lock: {key}, waiting...")
            for _ in range(10):
                await asyncio.sleep(0.1)
                redis_value = await self.redis.get(key)
                if redis_value:
                    return json.loads(redis_value)

            # Still no cache, fetch directly
            return await fetch_fn()

    async def invalidate(self, pattern: str):
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Pattern like "projects:list:*" or exact key
        """
        if not self.redis:
            logger.warning("Redis not available, cannot invalidate")
            return

        # Invalidate from request cache
        matching_keys = [k for k in self.request_cache.keys() if pattern in k]
        for key in matching_keys:
            del self.request_cache[key]

        # Invalidate from Redis
        if "*" in pattern:
            # Pattern match
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries: {pattern}")
        else:
            # Exact match
            await self.redis.delete(pattern)
            logger.info(f"Invalidated cache: {pattern}")

    async def invalidate_by_resource(self, resource_type: str, resource_id: str):
        """
        Invalidate all cache entries related to a resource.
        Called when resource is modified.
        """
        patterns = [
            f"{resource_type}:*",
            f"*:{resource_type}:*",
            f"{resource_type}:{resource_id}:*",
        ]

        for pattern in patterns:
            await self.invalidate(pattern)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Explicitly set a cache value."""
        # Store in request cache
        self.request_cache[key] = value

        # Store in Redis
        if self.redis:
            cache_ttl = ttl or CACHE_TTL_CONFIG.get(key.split(":")[0], 300)
            await self.redis.setex(key, cache_ttl, json.dumps(value, default=str))

    async def delete(self, key: str):
        """Delete a cache entry."""
        # Delete from request cache
        self.request_cache.pop(key, None)

        # Delete from Redis
        if self.redis:
            await self.redis.delete(key)

    async def clear_request_cache(self):
        """Clear request-scoped cache (called at end of request)."""
        self.request_cache.clear()

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health."""
        if not self.redis:
            return {"status": "unavailable", "error": "Redis not configured"}

        try:
            pong = await self.redis.ping()
            info = await self.redis.info()
            return {
                "status": "healthy" if pong else "unhealthy",
                "memory_usage": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


# ============================================================================
# Cache Warmer (Background Job)
# ============================================================================


class CacheWarmer:
    """Pre-populate cache on startup."""

    def __init__(self, cache: CacheService):
        self.cache = cache

    async def warm_all(self, data_loader: Callable):
        """
        Warm cache with critical data.

        Args:
            data_loader: Callable that returns dict of {key: value} to cache
        """
        logger.info("Warming cache...")
        try:
            data = await data_loader()
            for key, value in data.items():
                await self.cache.set(key, value)
            logger.info(f"Cache warmed with {len(data)} entries")
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            # Don't fail startup if warming fails


# ============================================================================
# Cache Factory
# ============================================================================

_cache_instance: Optional[CacheService] = None


async def init_cache(redis_url: str) -> CacheService:
    """Initialize cache service."""
    global _cache_instance
    _cache_instance = CacheService(redis_url)
    await _cache_instance.connect()
    return _cache_instance


async def get_cache() -> CacheService:
    """Get cache instance."""
    if _cache_instance is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _cache_instance


async def shutdown_cache():
    """Shutdown cache service."""
    if _cache_instance:
        await _cache_instance.disconnect()
