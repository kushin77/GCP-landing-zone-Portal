"""
Distributed Rate Limiting with Redis - Token Bucket Algorithm

Features:
- Token bucket algorithm with Lua script (atomic operations)
- Distributed state across instances
- Tiered rate limiting (public, authenticated, admin)
- Per-endpoint custom limits
- Adaptive rate limiting based on backend health
- Circuit breaker with graceful degradation
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import redis.asyncio as aioredis
from fastapi import Request
from opentelemetry import metrics
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Metrics
meter = metrics.get_meter(__name__)
rate_limit_requests = meter.create_counter(
    "rate_limit_requests_total",
    unit="1",
    description="Total requests evaluated by rate limiter",
)

rate_limit_violations = meter.create_counter(
    "rate_limit_violations_total",
    unit="1",
    description="Rate limit violations",
)


class ClientTier(str, Enum):
    """Client tier definitions"""

    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ADMIN = "admin"
    SERVICE_ACCOUNT = "service_account"


class RateLimitConfig:
    """Rate limiting configuration"""

    # Tiered limits (requests per minute)
    TIER_LIMITS = {
        ClientTier.PUBLIC: {"requests": 100, "window": 60},
        ClientTier.AUTHENTICATED: {"requests": 1000, "window": 60},
        ClientTier.ADMIN: {"requests": 5000, "window": 60},
        ClientTier.SERVICE_ACCOUNT: {"requests": 10000, "window": 60},
    }

    # Per-endpoint custom limits
    ENDPOINT_LIMITS = {
        ("POST", "/api/v2/projects"): {"requests": 10, "window": 60},
        ("GET", "/api/v2/costs"): {"requests": 100, "window": 60},
        ("GET", "/api/v2/compliance/reports"): {"requests": 50, "window": 60},
    }

    # Default endpoint limit
    DEFAULT_ENDPOINT_LIMIT = {"requests": 1000, "window": 60}


class DistributedRateLimiter:
    """Redis-backed distributed rate limiter using token bucket algorithm"""

    # Lua script for atomic token bucket operation
    LUA_SCRIPT = """
    local key = KEYS[1]
    local max_tokens = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])  -- tokens per second
    local now = tonumber(ARGV[3])

    local current = redis.call('GET', key)
    local state = {}

    if not current then
        state = {tokens = max_tokens, last_refill = now}
    else
        state = cjson.decode(current)
        -- Calculate tokens to add since last refill
        local seconds_elapsed = now - tonumber(state.last_refill)
        local tokens_to_add = seconds_elapsed * refill_rate
        state.tokens = math.min(max_tokens, state.tokens + tokens_to_add)
        state.last_refill = now
    end

    -- Try to consume 1 token
    if state.tokens >= 1 then
        state.tokens = state.tokens - 1
        redis.call('SET', key, cjson.encode(state), 'EX', 86400)
        return {1, math.floor(state.tokens)}  -- {allowed, remaining}
    else
        redis.call('SET', key, cjson.encode(state), 'EX', 86400)
        return {0, 0}  -- {not_allowed, 0_remaining}
    end
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client
        self._lua_script = None
        self._health_status = "healthy"
        self._last_health_check = 0
        self._health_check_interval = 10  # seconds

    async def initialize(self, redis_url: str = "redis://localhost:6379/1"):
        """Initialize Redis connection"""
        try:
            if not self.redis:
                self.redis = await aioredis.from_url(redis_url, decode_responses=True)

            # Register Lua script
            self._lua_script = await self.redis.script_load(self.LUA_SCRIPT)

            logger.info("Rate limiter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize rate limiter: {e}")
            raise

    async def shutdown(self):
        """Shutdown Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Rate limiter shutdown")

    async def is_allowed(
        self, client_id: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limit.

        Args:
            client_id: Unique identifier (user_id, API key, IP)
            max_requests: Max requests allowed
            window_seconds: Time window in seconds

        Returns:
            (is_allowed, metadata with remaining, limit, reset_in)
        """
        key = f"rate_limit:{client_id}"
        refill_rate = max_requests / window_seconds  # tokens per second
        now = datetime.now(timezone.utc).timestamp()

        try:
            # Execute Lua script atomically
            result = await self.redis.evalsha(
                self._lua_script, 1, key, max_requests, refill_rate, now
            )

            is_allowed, remaining = result

            metadata = {
                "remaining": int(remaining),
                "limit": max_requests,
                "reset_in": window_seconds,
                "window_seconds": window_seconds,
            }

            rate_limit_requests.add(
                1,
                {
                    "client_id": client_id,
                    "tier": "unknown",
                    "allowed": "true" if is_allowed else "false",
                },
            )

            return bool(is_allowed), metadata
        except RedisError as e:
            logger.warning(f"Rate limiter error for {client_id}: {e}")
            # Fail open (allow request) during Redis outage
            return True, {"remaining": max_requests, "limit": max_requests}

    async def get_dynamic_limit(
        self, client_tier: ClientTier, method: str, endpoint: str
    ) -> Dict[str, int]:
        """
        Get rate limit based on tier and endpoint.
        Adapts based on backend health.

        Args:
            client_tier: Client tier (public, authenticated, admin)
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path

        Returns:
            Dict with 'requests' and 'window' keys
        """
        # Check if there's an endpoint-specific limit
        endpoint_key = (method, endpoint)
        if endpoint_key in RateLimitConfig.ENDPOINT_LIMITS:
            base_limit = RateLimitConfig.ENDPOINT_LIMITS[endpoint_key]
        else:
            # Use tier-based limit
            base_limit = RateLimitConfig.TIER_LIMITS.get(
                client_tier, RateLimitConfig.DEFAULT_ENDPOINT_LIMIT
            )

        # Adapt based on backend health
        health = await self._check_backend_health()

        if health["status"] == "critical":
            # Reduce limit by 80%
            return {"requests": int(base_limit["requests"] * 0.2), "window": base_limit["window"]}
        elif health["status"] == "degraded":
            # Reduce limit by 50%
            return {"requests": int(base_limit["requests"] * 0.5), "window": base_limit["window"]}

        return base_limit

    async def _check_backend_health(self) -> Dict[str, str]:
        """Check if backend is healthy"""
        now = time.time()

        # Use cached result if recent
        if now - self._last_health_check < self._health_check_interval:
            return {"status": self._health_status}

        try:
            # Check queue depth (pseudo-metric for now)
            # In production, would check actual metrics from Cloud Monitoring
            queue_depth = await self._get_queue_depth()

            if queue_depth > 1000:
                self._health_status = "critical"
            elif queue_depth > 500:
                self._health_status = "degraded"
            else:
                self._health_status = "healthy"

            self._last_health_check = now
            return {"status": self._health_status}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            # Fail safe - reduce limits
            return {"status": "degraded"}

    async def _get_queue_depth(self) -> int:
        """Get current request queue depth (mock implementation)"""
        # In production, this would query Cloud Monitoring or a metrics endpoint
        return 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for distributed rate limiting"""

    def __init__(self, app, rate_limiter: DistributedRateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Determine client tier
        client_tier = self._get_client_tier(request)

        # Get rate limit for this endpoint
        limit = await self.rate_limiter.get_dynamic_limit(
            client_tier, request.method, request.url.path
        )

        # Check if allowed
        is_allowed, metadata = await self.rate_limiter.is_allowed(
            client_id, limit["requests"], limit["window"]
        )

        if not is_allowed:
            rate_limit_violations.add(
                1, {"client_id": client_id, "tier": client_tier.value, "endpoint": request.url.path}
            )

            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "retry_after": limit["window"],
                },
                headers={
                    "Retry-After": str(limit["window"]),
                    "X-RateLimit-Limit": str(limit["requests"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(
                        int(
                            (
                                datetime.now(timezone.utc) + timedelta(seconds=limit["window"])
                            ).timestamp()
                        )
                    ),
                },
            )

        # Allow request, add headers
        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(limit["requests"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        response.headers["X-RateLimit-Reset"] = str(
            int((datetime.now(timezone.utc) + timedelta(seconds=limit["window"])).timestamp())
        )

        return response

    def _get_client_id(self, request: Request) -> str:
        """Extract client ID from request"""
        # Check for user ID from auth
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user.id

        # Check for API key
        if "X-API-Key" in request.headers:
            return f"key:{request.headers['X-API-Key'][:16]}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    def _get_client_tier(self, request: Request) -> ClientTier:
        """Determine client tier from request"""
        # Check if authenticated
        if hasattr(request.state, "user") and request.state.user:
            if request.state.user.is_admin:
                return ClientTier.ADMIN
            return ClientTier.AUTHENTICATED

        # Check for service account
        if "X-Service-Account" in request.headers:
            return ClientTier.SERVICE_ACCOUNT

        # Default to public
        return ClientTier.PUBLIC


# Global rate limiter instance
_rate_limiter: Optional[DistributedRateLimiter] = None


async def get_rate_limiter() -> DistributedRateLimiter:
    """Get or create global rate limiter instance"""
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = DistributedRateLimiter()
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
        await _rate_limiter.initialize(redis_url)

    return _rate_limiter


async def shutdown_rate_limiter():
    """Shutdown rate limiter"""
    global _rate_limiter

    if _rate_limiter:
        await _rate_limiter.shutdown()
        _rate_limiter = None
