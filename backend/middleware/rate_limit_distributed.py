"""
Distributed rate limiting and input validation.
Fixes issue #46: No Input Validation or DDoS Protection.

Provides:
- Distributed rate limiting (Redis-backed)
- Per-user and per-IP rate limits
- Input parameter validation
- Request size limits
- OWASP controls
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time

import aioredis
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimitConfig:
    """Rate limit configuration."""

    # Per-user limits
    USER_LIMIT_REQUESTS = 1000  # requests
    USER_LIMIT_WINDOW = 3600    # seconds (1 hour)

    # Per-IP limits
    IP_LIMIT_REQUESTS = 10000   # requests
    IP_LIMIT_WINDOW = 3600      # seconds (1 hour)

    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        "/api/v1/health": {"requests": 1000, "window": 60},  # 1000 req/min
        "/api/v1/auth/login": {"requests": 10, "window": 300},  # 10 req/5min
        "/api/v1/projects": {"requests": 100, "window": 60},  # 100 req/min
        "/api/v1/compliance/scan": {"requests": 5, "window": 300},  # 5 req/5min
    }


class DistributedRateLimiter:
    """Rate limiter backed by Redis for distributed systems."""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def check_limit(
        self, key: str, limit: int, window: int
    ) -> bool:
        """
        Check if request is within rate limit.

        Uses sliding window algorithm:
        - Maintains sorted set of request timestamps
        - Removes old entries outside window
        - Counts requests in current window

        Args:
            key: Rate limit key (e.g., "user:123", "ip:192.168.1.1")
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        window_start = now - window

        # Remove requests outside window
        await self.redis.zremrangebyscore(key, 0, window_start)

        # Count requests in window
        count = await self.redis.zcard(key)

        if count >= limit:
            return False

        # Add this request
        await self.redis.zadd(key, {str(now): now})

        # Set expiration (window + 1 second)
        await self.redis.expire(key, window + 1)

        return True

    async def get_remaining(
        self, key: str, limit: int, window: int
    ) -> tuple[int, int]:
        """
        Get remaining requests and reset time.

        Returns:
            (remaining_requests, seconds_until_reset)
        """
        now = time.time()
        window_start = now - window

        # Count requests in current window
        count = await self.redis.zcard(key)
        remaining = max(0, limit - count)

        # Get oldest request timestamp
        oldest = await self.redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            reset_time = int(oldest[0][1]) + window
            seconds_until_reset = max(0, reset_time - int(now))
        else:
            seconds_until_reset = 0

        return remaining, seconds_until_reset

    async def block_ip(self, ip_address: str, duration: int = 3600):
        """Block an IP address."""
        key = f"blocked_ip:{ip_address}"
        await self.redis.setex(key, duration, "1")
        logger.warning(f"Blocked IP: {ip_address} for {duration}s")

    async def is_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked."""
        key = f"blocked_ip:{ip_address}"
        return await self.redis.exists(key) > 0


# ============================================================================
# Input Validation
# ============================================================================

class PaginationParams(BaseModel):
    """Paginated query parameters with validation."""

    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number"
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100,  # Max 100 items per page
        description="Items per page (1-100)"
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Offset (calculated from page/limit)"
    )

    @validator("offset", pre=True, always=True)
    def calculate_offset(cls, v, values):
        if "page" in values and "limit" in values:
            return (values["page"] - 1) * values["limit"]
        return v


class ProjectQueryParams(BaseModel):
    """Project query parameters with validation."""

    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to query (1-365)"
    )

    project_id: Optional[str] = Field(
        default=None,
        regex=r"^[a-z0-9\-]{1,30}$",  # GCP project ID format
        description="Project ID to filter by"
    )

    status: Optional[str] = Field(
        default=None,
        regex=r"^[a-z\-]+$",
        description="Project status"
    )

    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number"
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Items per page"
    )


class CostQueryParams(BaseModel):
    """Cost query parameters with validation."""

    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to query"
    )

    project_id: Optional[str] = Field(
        default=None,
        regex=r"^[a-z0-9\-]{1,30}$",
        description="Project ID"
    )

    min_cost: float = Field(
        default=0,
        ge=0,
        le=1000000,
        description="Minimum cost filter"
    )

    max_cost: float = Field(
        default=1000000,
        ge=0,
        le=1000000,
        description="Maximum cost filter"
    )

    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number"
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Items per page"
    )


class ComplianceScanParams(BaseModel):
    """Compliance scan parameters with validation."""

    frameworks: list[str] = Field(
        default=[],
        max_items=10,
        description="Compliance frameworks to scan"
    )

    severity: Optional[str] = Field(
        default=None,
        regex=r"^(critical|high|medium|low)$",
        description="Minimum severity level"
    )

    project_ids: list[str] = Field(
        default=[],
        max_items=100,
        description="Project IDs to scan"
    )


# ============================================================================
# Request Validation Middleware
# ============================================================================

class RequestValidator:
    """Validates HTTP requests."""

    # Global limits
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1MB max request size
    MAX_QUERY_STRING_LENGTH = 10 * 1024  # 10KB max query string

    # Header limits
    MAX_HEADER_SIZE = 8 * 1024  # 8KB per header
    MAX_HEADERS = 100

    @staticmethod
    def validate_content_length(request: Request) -> bool:
        """Validate Content-Length header."""
        content_length = request.headers.get("content-length", "0")

        try:
            length = int(content_length)
            if length > RequestValidator.MAX_CONTENT_LENGTH:
                logger.warning(
                    f"Content-Length exceeded: {length} > "
                    f"{RequestValidator.MAX_CONTENT_LENGTH}"
                )
                return False
        except ValueError:
            logger.warning(f"Invalid Content-Length: {content_length}")
            return False

        return True

    @staticmethod
    def validate_query_string(request: Request) -> bool:
        """Validate query string length."""
        query = request.url.query or ""
        if len(query) > RequestValidator.MAX_QUERY_STRING_LENGTH:
            logger.warning(
                f"Query string too long: {len(query)} > "
                f"{RequestValidator.MAX_QUERY_STRING_LENGTH}"
            )
            return False
        return True

    @staticmethod
    def validate_headers(request: Request) -> bool:
        """Validate headers."""
        # Check header count
        if len(request.headers) > RequestValidator.MAX_HEADERS:
            logger.warning(
                f"Too many headers: {len(request.headers)} > "
                f"{RequestValidator.MAX_HEADERS}"
            )
            return False

        # Check header sizes
        for name, value in request.headers.items():
            if len(value) > RequestValidator.MAX_HEADER_SIZE:
                logger.warning(
                    f"Header too large: {name} ({len(value)} > "
                    f"{RequestValidator.MAX_HEADER_SIZE})"
                )
                return False

        return True

    @staticmethod
    def validate_request(request: Request) -> bool:
        """Validate all request properties."""
        return (
            RequestValidator.validate_content_length(request)
            and RequestValidator.validate_query_string(request)
            and RequestValidator.validate_headers(request)
        )
