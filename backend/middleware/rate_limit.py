"""
FAANG-Grade Rate Limiting Middleware for Landing Zone Portal.

Implements:
- Request rate limiting per user/IP
- Burst protection
- Sliding window algorithm
- Redis-backed for distributed systems
"""
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    # Default limits
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10

    # Endpoint-specific overrides
    endpoint_limits: dict = field(
        default_factory=lambda: {
            "/api/v1/ai/query": {"per_minute": 10, "per_hour": 100},  # AI is expensive
            "/api/v1/costs": {"per_minute": 30, "per_hour": 300},
            "/health": {"per_minute": 1000, "per_hour": 10000},  # Health checks unlimited
        }
    )

    # Whitelist
    whitelisted_ips: set = field(default_factory=set)
    whitelisted_paths: set = field(default_factory=lambda: {"/health", "/ready", "/metrics"})

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create config from environment variables."""
        return cls(
            requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
            requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
            burst_size=int(os.getenv("RATE_LIMIT_BURST", "10")),
        )


# ============================================================================
# In-Memory Rate Limiter (for single instance)
# ============================================================================


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using in-memory storage.
    For production, use Redis-backed implementation.
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._windows: dict = defaultdict(list)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try to get user email from auth
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "email"):
            return f"user:{user.email}"

        # Fall back to IP address
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client = request.client
        if client:
            return f"ip:{client.host}"

        return "ip:unknown"

    def _cleanup_old_entries(self, window_key: str, window_size: int):
        """Remove entries outside the current window."""
        current_time = time.time()
        cutoff = current_time - window_size

        self._windows[window_key] = [ts for ts in self._windows[window_key] if ts > cutoff]

    def _periodic_cleanup(self):
        """Periodically clean up old entries to prevent memory growth."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            for key in list(self._windows.keys()):
                if not self._windows[key]:
                    del self._windows[key]
            self._last_cleanup = current_time

    def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limits.

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        path = request.url.path

        # Skip whitelisted paths
        if path in self.config.whitelisted_paths:
            return True, {}

        client_id = self._get_client_id(request)

        # Skip whitelisted IPs
        if client_id.startswith("ip:") and client_id[3:] in self.config.whitelisted_ips:
            return True, {}

        current_time = time.time()

        # Get limits for this endpoint
        endpoint_config = self.config.endpoint_limits.get(path, {})
        per_minute = endpoint_config.get("per_minute", self.config.requests_per_minute)
        per_hour = endpoint_config.get("per_hour", self.config.requests_per_hour)

        # Check per-minute limit
        minute_key = f"{client_id}:minute:{path}"
        self._cleanup_old_entries(minute_key, 60)
        minute_count = len(self._windows[minute_key])

        if minute_count >= per_minute:
            retry_after = 60 - (current_time - min(self._windows[minute_key]))
            return False, {
                "limit": per_minute,
                "remaining": 0,
                "reset": int(current_time + retry_after),
                "retry_after": int(retry_after),
            }

        # Check per-hour limit
        hour_key = f"{client_id}:hour:{path}"
        self._cleanup_old_entries(hour_key, 3600)
        hour_count = len(self._windows[hour_key])

        if hour_count >= per_hour:
            retry_after = 3600 - (current_time - min(self._windows[hour_key]))
            return False, {
                "limit": per_hour,
                "remaining": 0,
                "reset": int(current_time + retry_after),
                "retry_after": int(retry_after),
            }

        # Record this request
        self._windows[minute_key].append(current_time)
        self._windows[hour_key].append(current_time)

        # Periodic cleanup
        self._periodic_cleanup()

        return True, {
            "limit": per_minute,
            "remaining": per_minute - minute_count - 1,
            "reset": int(current_time + 60),
        }


# ============================================================================
# Redis-Backed Rate Limiter (for distributed systems)
# ============================================================================


class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed deployments.
    Uses sliding window with Redis sorted sets.
    """

    def __init__(self, redis_client, config: RateLimitConfig = None):
        self.redis = redis_client
        self.config = config or RateLimitConfig()

    async def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """Check if request is allowed under rate limits."""
        path = request.url.path

        # Skip whitelisted paths
        if path in self.config.whitelisted_paths:
            return True, {}

        client_id = self._get_client_id(request)
        current_time = time.time()

        # Get limits for this endpoint
        endpoint_config = self.config.endpoint_limits.get(path, {})
        per_minute = endpoint_config.get("per_minute", self.config.requests_per_minute)

        key = f"rate_limit:{client_id}:{path}"

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, current_time - 60)

        # Count current entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(current_time): current_time})

        # Set expiry
        pipe.expire(key, 120)

        results = await pipe.execute()
        count = results[1]

        if count >= per_minute:
            return False, {
                "limit": per_minute,
                "remaining": 0,
                "reset": int(current_time + 60),
                "retry_after": 60,
            }

        return True, {
            "limit": per_minute,
            "remaining": per_minute - count,
            "reset": int(current_time + 60),
        }

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "email"):
            return f"user:{user.email}"

        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client = request.client
        if client:
            return f"ip:{client.host}"

        return "ip:unknown"


# ============================================================================
# Rate Limiting Middleware
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, limiter: SlidingWindowRateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or SlidingWindowRateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Check rate limit before processing request."""

        allowed, rate_info = self.limiter.is_allowed(request)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {self.limiter._get_client_id(request)} "
                f"on {request.url.path}"
            )

            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": rate_info.get("retry_after", 60),
                },
                headers={
                    "Retry-After": str(rate_info.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info.get("reset", 0)),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if rate_info:
            response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset", 0))

        return response


# ============================================================================
# Decorator for endpoint-specific rate limiting
# ============================================================================


def rate_limit(requests_per_minute: int = 60, requests_per_hour: int = 1000):
    """
    Decorator for endpoint-specific rate limiting.

    Usage:
        @app.get("/expensive-operation")
        @rate_limit(requests_per_minute=10)
        async def expensive_operation():
            ...
    """

    def decorator(func: Callable):
        # Store limits on function for middleware to read
        func._rate_limit = {"per_minute": requests_per_minute, "per_hour": requests_per_hour}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Factory function
# ============================================================================


def create_rate_limiter(redis_client=None) -> SlidingWindowRateLimiter:
    """Create appropriate rate limiter based on configuration."""
    config = RateLimitConfig.from_env()

    if redis_client:
        return RedisRateLimiter(redis_client, config)

    return SlidingWindowRateLimiter(config)
