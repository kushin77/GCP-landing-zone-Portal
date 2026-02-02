"""
FAANG-Grade Security Middleware for Landing Zone Portal.

Implements:
- Security headers
- Request ID tracking
- Request validation
- CORS hardening
- Input sanitization
"""
import logging
import os
import re
import time
import uuid
from typing import Set

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class SecurityConfig:
    """Security configuration from environment."""

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

    # CORS
    ALLOWED_ORIGINS: Set[str] = (
        set(os.getenv("ALLOWED_ORIGINS", "").split(",")) if os.getenv("ALLOWED_ORIGINS") else set()
    )

    # Request limits
    MAX_REQUEST_SIZE_MB = int(os.getenv("MAX_REQUEST_SIZE_MB", "10"))
    MAX_REQUEST_SIZE_BYTES = MAX_REQUEST_SIZE_MB * 1024 * 1024

    # Headers
    HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year

    # CSP directives
    CSP_DIRECTIVES = {
        "default-src": "'self'",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",  # Inline styles for components
        "img-src": "'self' data: https:",
        "font-src": "'self'",
        "connect-src": "'self' https://*.googleapis.com",
        "frame-ancestors": "'self'",
        "base-uri": "'self'",
        "form-action": "'self'",
    }


# ============================================================================
# Security Headers
# ============================================================================


def get_security_headers(request: Request) -> dict:
    """Generate security headers for response."""
    headers = {
        # Prevent XSS
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        # Prevent clickjacking
        "X-Frame-Options": "SAMEORIGIN",
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        # Permissions policy (formerly Feature-Policy)
        "Permissions-Policy": ("camera=(), " "microphone=(), " "geolocation=(), " "payment=()"),
        # Cache control for API responses
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
    }

    # HSTS (only in production with HTTPS or testing)
    if SecurityConfig.IS_PRODUCTION or os.getenv("TESTING") == "true":
        headers[
            "Strict-Transport-Security"
        ] = f"max-age={SecurityConfig.HSTS_MAX_AGE}; includeSubDomains; preload"

    # CSP (for HTML responses, though API typically returns JSON)
    if not request.url.path.startswith("/api/"):
        csp = "; ".join(
            f"{directive} {value}" for directive, value in SecurityConfig.CSP_DIRECTIVES.items()
        )
        headers["Content-Security-Policy"] = csp

    return headers


# ============================================================================
# Input Validation
# ============================================================================


class InputValidator:
    """Validate and sanitize input data."""

    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        r"<script[^>]*>",  # Script tags
        r"javascript:",  # JavaScript URLs
        r"data:text/html",  # Data URLs with HTML
        r"on\w+\s*=",  # Event handlers
        r"\{\{.*\}\}",  # Template injection
        r"\$\{.*\}",  # Template literals
    ]

    # SQL injection patterns (for logging, actual protection via parameterized queries)
    SQL_PATTERNS = [
        r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER)\s+",
        r"UNION\s+SELECT",
        r"--\s*$",
        r"\/\*.*\*\/",
    ]

    def __init__(self):
        self.blocked_regex = [re.compile(p, re.IGNORECASE) for p in self.BLOCKED_PATTERNS]
        self.sql_regex = [re.compile(p, re.IGNORECASE) for p in self.SQL_PATTERNS]

    def is_safe(self, value: str) -> bool:
        """Check if string value is safe."""
        if not isinstance(value, str):
            return True

        for pattern in self.blocked_regex:
            if pattern.search(value):
                return False

        return True

    def check_sql_injection(self, value: str) -> bool:
        """Check for potential SQL injection (for logging)."""
        if not isinstance(value, str):
            return False

        for pattern in self.sql_regex:
            if pattern.search(value):
                return True

        return False

    def sanitize(self, value: str) -> str:
        """Sanitize string value by escaping dangerous characters."""
        if not isinstance(value, str):
            return value

        # HTML entity encoding for special characters
        value = value.replace("&", "&amp;")
        value = value.replace("<", "&lt;")
        value = value.replace(">", "&gt;")
        value = value.replace('"', "&quot;")
        value = value.replace("'", "&#x27;")

        return value


# ============================================================================
# Request Context
# ============================================================================


class RequestContext:
    """Request context for tracking and logging."""

    def __init__(self, request: Request):
        self.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        self.start_time = time.time()
        self.client_ip = self._get_client_ip(request)
        self.user_agent = request.headers.get("User-Agent", "")
        self.path = request.url.path
        self.method = request.method

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For header (set by load balancers)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    @property
    def duration_ms(self) -> float:
        """Get request duration in milliseconds."""
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "correlation_id": self.request_id,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "path": self.path,
            "method": self.method,
            "duration_ms": self.duration_ms,
        }


# ============================================================================
# Security Middleware
# ============================================================================


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware.

    Features:
    - Adds security headers to all responses
    - Adds request ID tracking
    - Validates request size
    - Logs request context
    """

    def __init__(self, app, validator: InputValidator = None):
        super().__init__(app)
        self.validator = validator or InputValidator()

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with security checks."""

        # Create request context
        ctx = RequestContext(request)
        request.state.request_id = ctx.request_id
        request.state.client_ip = ctx.client_ip

        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > SecurityConfig.MAX_REQUEST_SIZE_BYTES:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=413,
                content={
                    "error": True,
                    "error_code": "REQUEST_TOO_LARGE",
                    "message": f"Request body exceeds maximum size of {SecurityConfig.MAX_REQUEST_SIZE_MB}MB",
                },
            )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request failed: {e}", extra=ctx.to_dict())
            raise

        # Add security headers
        security_headers = get_security_headers(request)
        for header, value in security_headers.items():
            response.headers[header] = value

        # Add request ID to response
        response.headers["X-Request-ID"] = ctx.request_id

        # Log request completion
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} "
            f"({ctx.duration_ms:.2f}ms)",
            extra=ctx.to_dict(),
        )

        return response


# ============================================================================
# CORS Configuration Helper
# ============================================================================


def get_cors_config() -> dict:
    """Get CORS configuration for FastAPI."""

    if SecurityConfig.IS_PRODUCTION:
        # Production: Only allow specific origins
        allowed_origins = list(SecurityConfig.ALLOWED_ORIGINS) or ["https://portal.landing-zone.io"]
    else:
        # Development: Allow localhost
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Requested-With",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 600,  # 10 minutes
    }
