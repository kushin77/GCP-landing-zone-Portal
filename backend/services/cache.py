"""
FAANG-Grade Redis Caching Layer
Enterprise-grade caching with:
- Connection pooling
- Automatic reconnection
- Cache invalidation patterns
- Compression for large payloads
- Structured key namespacing
- TTL management
- Circuit breaker for resilience
"""

import asyncio
import gzip
import hashlib
import logging
import pickle
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, ParamSpec, TypeVar

try:
    import redis.asyncio as aioredis
    from redis.asyncio.connection import ConnectionPool

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variables for generic functions
P = ParamSpec("P")
R = TypeVar("R")


class CacheNamespace(str, Enum):
    """Cache key namespaces for organization"""

    COSTS = "costs"
    COMPLIANCE = "compliance"
    PROJECTS = "projects"
    USERS = "users"
    SESSIONS = "sessions"
    RATE_LIMIT = "rate_limit"
    AI = "ai"
    METRICS = "metrics"


class CacheConfig(BaseModel):
    """Cache configuration"""

    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 300  # 5 minutes
    max_connections: int = 50
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    compression_threshold: int = 1024  # Compress if > 1KB
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0
    key_prefix: str = "lz_portal"


class CircuitBreaker:
    """
    Circuit breaker for cache resilience.
    Prevents cascade failures when Redis is unavailable.
    """

    def __init__(self, threshold: int = 5, timeout: float = 30.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.is_open = False
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.is_open:
                if self.last_failure_time:
                    import time

                    elapsed = time.time() - self.last_failure_time
                    if elapsed >= self.timeout:
                        # Try to close circuit
                        self.is_open = False
                        self.failures = 0
                        logger.info("Circuit breaker: attempting to close")
                    else:
                        raise CacheUnavailableError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self.failures = 0
            return result
        except Exception:
            async with self._lock:
                self.failures += 1
                import time

                self.last_failure_time = time.time()
                if self.failures >= self.threshold:
                    self.is_open = True
                    logger.warning(f"Circuit breaker opened after {self.failures} failures")
            raise


class CacheUnavailableError(Exception):
    """Raised when cache is unavailable"""

    pass


class CacheService:
    """
    Enterprise-grade caching service with Redis.

    Features:
    - Async operations
    - Automatic serialization/deserialization
    - Compression for large values
    - Structured key namespacing
    - Circuit breaker for resilience
    - Graceful degradation when Redis unavailable
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Any] = None
        self._circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout,
        )
        self._connected = False

    async def connect(self) -> bool:
        """Initialize Redis connection pool"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, caching disabled")
            return False

        try:
            self._pool = ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close Redis connection pool"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False
        logger.info("Redis connection closed")

    def _make_key(self, namespace: CacheNamespace, key: str) -> str:
        """Create namespaced cache key"""
        return f"{self.config.key_prefix}:{namespace.value}:{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value with optional compression"""
        data = pickle.dumps(value)

        if len(data) > self.config.compression_threshold:
            compressed = gzip.compress(data)
            # Only use compression if it actually reduces size
            if len(compressed) < len(data):
                return b"\x01" + compressed

        return b"\x00" + data

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value with optional decompression"""
        if not data:
            return None

        is_compressed = data[0] == 1
        payload = data[1:]

        if is_compressed:
            payload = gzip.decompress(payload)

        return pickle.loads(payload)

    async def get(self, namespace: CacheNamespace, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self._connected:
            return default

        try:

            async def _get():
                cache_key = self._make_key(namespace, key)
                data = await self._client.get(cache_key)
                if data is None:
                    return default
                return self._deserialize(data)

            return await self._circuit_breaker.call(_get)

        except CacheUnavailableError:
            return default
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return default

    async def set(
        self, namespace: CacheNamespace, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        if not self._connected:
            return False

        try:

            async def _set():
                cache_key = self._make_key(namespace, key)
                data = self._serialize(value)
                ttl_seconds = ttl or self.config.default_ttl
                await self._client.setex(cache_key, ttl_seconds, data)
                return True

            return await self._circuit_breaker.call(_set)

        except CacheUnavailableError:
            return False
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, namespace: CacheNamespace, key: str) -> bool:
        """Delete value from cache"""
        if not self._connected:
            return False

        try:

            async def _delete():
                cache_key = self._make_key(namespace, key)
                await self._client.delete(cache_key)
                return True

            return await self._circuit_breaker.call(_delete)

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, namespace: CacheNamespace, pattern: str) -> int:
        """Delete all keys matching pattern in namespace"""
        if not self._connected:
            return 0

        try:

            async def _delete_pattern():
                full_pattern = self._make_key(namespace, pattern)
                cursor = 0
                deleted = 0

                while True:
                    cursor, keys = await self._client.scan(
                        cursor=cursor, match=full_pattern, count=100
                    )
                    if keys:
                        deleted += await self._client.delete(*keys)
                    if cursor == 0:
                        break

                return deleted

            return await self._circuit_breaker.call(_delete_pattern)

        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0

    async def exists(self, namespace: CacheNamespace, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._connected:
            return False

        try:

            async def _exists():
                cache_key = self._make_key(namespace, key)
                return await self._client.exists(cache_key) > 0

            return await self._circuit_breaker.call(_exists)

        except Exception:
            return False

    async def get_or_set(
        self,
        namespace: CacheNamespace,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """Get from cache, or compute and cache if missing"""
        value = await self.get(namespace, key)

        if value is not None:
            return value

        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        # Cache it
        await self.set(namespace, key, value, ttl)

        return value

    async def health_check(self) -> dict:
        """Check cache health"""
        if not self._connected:
            return {
                "status": "disconnected",
                "available": False,
                "circuit_breaker_open": self._circuit_breaker.is_open,
            }

        try:
            start = asyncio.get_event_loop().time()
            await self._client.ping()
            latency_ms = (asyncio.get_event_loop().time() - start) * 1000

            info = await self._client.info("memory")

            return {
                "status": "healthy",
                "available": True,
                "latency_ms": round(latency_ms, 2),
                "circuit_breaker_open": self._circuit_breaker.is_open,
                "memory_used": info.get("used_memory_human", "unknown"),
                "memory_peak": info.get("used_memory_peak_human", "unknown"),
            }
        except Exception as e:
            return {
                "status": "error",
                "available": False,
                "error": str(e),
                "circuit_breaker_open": self._circuit_breaker.is_open,
            }


def cached(
    namespace: CacheNamespace,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator for caching function results.

    Usage:
        @cached(CacheNamespace.COSTS, ttl=300)
        async def get_project_costs(project_id: str, days: int):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> R:
            # Get cache service from first arg if it has one
            cache = None
            if args and hasattr(args[0], "cache"):
                cache = getattr(args[0], "cache")

            if cache is None or not isinstance(cache, CacheService):
                # No cache available, just call function
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                # Default key builder
                key_parts = [func.__name__]
                key_parts.extend(str(a) for a in args[1:])  # Skip self
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key = ":".join(key_parts)

            # Hash long keys
            if len(key) > 200:
                key = hashlib.sha256(key.encode()).hexdigest()

            # Try to get from cache
            cached_value = await cache.get(namespace, key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {namespace.value}:{key}")
                return cached_value

            # Compute and cache
            logger.debug(f"Cache miss: {namespace.value}:{key}")
            result = await func(*args, **kwargs)
            await cache.set(namespace, key, result, ttl)

            return result

        return wrapper

    return decorator


# Singleton instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create the cache service singleton"""
    global _cache_service

    if _cache_service is None:
        import os

        config = CacheConfig(
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            default_ttl=int(os.environ.get("CACHE_DEFAULT_TTL", "300")),
        )
        _cache_service = CacheService(config)
        await _cache_service.connect()

    return _cache_service


async def shutdown_cache() -> None:
    """Shutdown the cache service"""
    global _cache_service

    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None
