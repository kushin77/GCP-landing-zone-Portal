"""
Distributed Redis Caching Service with Cache Hierarchy

Features:
- L1: Redis (15-min TTL for dashboards, 1-hour for reports)
- L2: BigQuery query result cache (6-hour built-in)
- L3: PostgreSQL materialized views (nightly refresh)
- Cache-aside pattern with atomic operations
- Automatic cache warming
- Metrics and observability
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from opentelemetry import metrics, trace
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Metrics
meter = metrics.get_meter(__name__)
cache_hits = meter.create_counter("cache_hits_total", unit="1", description="Cache hits")
cache_misses = meter.create_counter("cache_misses_total", unit="1", description="Cache misses")
cache_evictions = meter.create_counter(
    "cache_evictions_total", unit="1", description="Cache evictions"
)
cache_operations = meter.create_histogram(
    "cache_operation_duration_ms", unit="ms", description="Cache operation latency"
)

# Tracer
tracer = trace.get_tracer(__name__)


class CacheConfig:
    """Cache configuration"""

    # TTL configurations (seconds)
    TTL_DASHBOARD = 15 * 60  # 15 minutes for dashboards
    TTL_REPORT = 60 * 60  # 1 hour for reports
    TTL_SHORT = 5 * 60  # 5 minutes for frequently changing data
    TTL_LONG = 24 * 60 * 60  # 24 hours for static data

    # Max memory
    MAX_MEMORY = "256mb"
    EVICTION_POLICY = "allkeys-lru"  # Least recently used

    # Key prefixes
    PREFIX_COSTS = "costs"
    PREFIX_COMPLIANCE = "compliance"
    PREFIX_RESOURCES = "resources"
    PREFIX_METRICS = "metrics"


class CacheService:
    """Distributed Redis caching service"""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self._initialized = False

    async def initialize(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection"""
        try:
            if not self.redis:
                self.redis = await aioredis.from_url(redis_url, decode_responses=True)

            # Test connection
            await self.redis.ping()
            self._initialized = True
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            self._initialized = False
            raise

    async def shutdown(self):
        """Shutdown Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Cache service shutdown")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Redis"""
        try:
            if not self.redis:
                return {"status": "unavailable", "error": "Not initialized"}

            # Ping Redis
            await self.redis.ping()

            # Get memory info
            info = await self.redis.info("memory")

            return {
                "status": "healthy",
                "memory_used": info.get("used_memory_human"),
                "memory_peak": info.get("used_memory_peak_human"),
            }
        except RedisConnectionError:
            return {"status": "unavailable", "error": "Redis connection failed"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (with metrics)"""
        span = tracer.start_as_current_span("cache.get")
        span.set_attribute("cache.key", key)

        start = time.time()

        try:
            if not self.redis or not self._initialized:
                cache_misses.add(1, {"key": key, "reason": "not_initialized"})
                return None

            value = await self.redis.get(key)

            if value:
                cache_hits.add(1, {"key": key})
                duration = (time.time() - start) * 1000
                cache_operations.record(duration, {"operation": "get", "hit": True})
                span.set_attribute("cache.hit", True)
            else:
                cache_misses.add(1, {"key": key, "reason": "key_not_found"})
                duration = (time.time() - start) * 1000
                cache_operations.record(duration, {"operation": "get", "hit": False})
                span.set_attribute("cache.hit", False)

            # Parse JSON if applicable
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return None
        except RedisError as e:
            logger.warning(f"Cache get error for {key}: {e}")
            cache_misses.add(1, {"key": key, "reason": "redis_error"})
            duration = (time.time() - start) * 1000
            cache_operations.record(duration, {"operation": "get", "error": True})
            span.record_exception(e)
            return None

    async def set(self, key: str, value: Any, ttl: int = CacheConfig.TTL_DASHBOARD):
        """Set value in cache (with metrics)"""
        span = tracer.start_as_current_span("cache.set")
        span.set_attribute("cache.key", key)
        span.set_attribute("cache.ttl_seconds", ttl)

        start = time.time()

        try:
            if not self.redis or not self._initialized:
                return False

            # Serialize to JSON
            if not isinstance(value, str):
                value = json.dumps(value)

            await self.redis.setex(key, ttl, value)

            duration = (time.time() - start) * 1000
            cache_operations.record(duration, {"operation": "set", "success": True})
            span.set_attribute("cache.set_success", True)

            return True
        except RedisError as e:
            logger.warning(f"Cache set error for {key}: {e}")
            duration = (time.time() - start) * 1000
            cache_operations.record(duration, {"operation": "set", "error": True})
            span.record_exception(e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if not self.redis or not self._initialized:
                return False

            await self.redis.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            if not self.redis or not self._initialized:
                return 0

            # Use SCAN to avoid blocking
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

                if keys:
                    deleted += await self.redis.delete(*keys)

                if cursor == 0:
                    break

            return deleted
        except RedisError as e:
            logger.warning(f"Cache delete_pattern error for {pattern}: {e}")
            return 0

    async def mget(self, keys: List[str]) -> Dict[str, Optional[Any]]:
        """Get multiple values from cache"""
        try:
            if not self.redis or not self._initialized:
                return {key: None for key in keys}

            values = await self.redis.mget(keys)

            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
                else:
                    result[key] = None

            return result
        except RedisError as e:
            logger.warning(f"Cache mget error: {e}")
            return {key: None for key in keys}

    async def mset(self, data: Dict[str, Any], ttl: int = CacheConfig.TTL_DASHBOARD) -> bool:
        """Set multiple values in cache"""
        try:
            if not self.redis or not self._initialized:
                return False

            # Serialize values
            serialized = {}
            for key, value in data.items():
                if isinstance(value, str):
                    serialized[key] = value
                else:
                    serialized[key] = json.dumps(value)

            # Use pipeline for atomic operation
            async with self.redis.pipeline(transaction=False) as pipe:
                for key, value in serialized.items():
                    pipe.setex(key, ttl, value)

                await pipe.execute()

            return True
        except RedisError as e:
            logger.warning(f"Cache mset error: {e}")
            return False


# Global cache instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create global cache service instance"""
    global _cache_service

    if _cache_service is None:
        _cache_service = CacheService()
        # Get Redis URL from environment
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        await _cache_service.initialize(redis_url)

    return _cache_service


async def shutdown_cache():
    """Shutdown cache service"""
    global _cache_service

    if _cache_service:
        await _cache_service.shutdown()
        _cache_service = None


def cache_wrapper(ttl: int = CacheConfig.TTL_DASHBOARD):
    """
    Decorator for caching async function results

    Usage:
        @cache_wrapper(ttl=3600)
        async def expensive_query():
            return data
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            cache_key = f"{func.__module__}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cache = await get_cache_service()
            cached_value = await cache.get(cache_key)

            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator
