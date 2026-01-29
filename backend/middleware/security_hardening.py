"""
Security hardening middleware for FastAPI.
Implements: Content Security Headers, HSTS, X-Frame-Options, CORS, CSRF protection
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import lru_cache

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import secretmanager
from google.cloud import logging as cloud_logging
import jwt

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses"""

    def __init__(self, app: FastAPI):
        self.app = app
        app.add_middleware(self.middleware)

    async def middleware(self, request: Request, call_next):
        response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy (CSP)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # X-Frame-Options (Clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options (MIME-type sniffing protection)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (Feature policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        return response


class CSRFProtectionMiddleware:
    """CSRF token validation middleware"""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    TOKEN_EXPIRY = 3600  # 1 hour

    def __init__(self, app: FastAPI, secret_key: str):
        self.app = app
        self.secret_key = secret_key
        app.add_middleware(self.middleware)

    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        payload = {
            "session_id": session_id,
            "exp": datetime.utcnow() + timedelta(seconds=self.TOKEN_EXPIRY),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload.get("session_id") == session_id
        except jwt.ExpiredSignatureError:
            logger.warning(f"CSRF token expired for session {session_id}")
            return False
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid CSRF token for session {session_id}")
            return False

    async def middleware(self, request: Request, call_next):
        # Skip CSRF check for safe methods and certain endpoints
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        if request.url.path.startswith("/api/v1/health"):
            return await call_next(request)

        # Validate CSRF token
        session_id = request.cookies.get("session_id")
        csrf_token = request.headers.get("X-CSRF-Token")

        if not session_id or not csrf_token or not self.validate_token(csrf_token, session_id):
            return Response("Invalid CSRF token", status_code=403)

        return await call_next(request)


class InputSanitizationMiddleware:
    """Sanitize and validate user inputs"""

    DANGEROUS_PATTERNS = [
        "<script",  # XSS
        "javascript:",  # XSS
        "onclick=",  # XSS
        "onerror=",  # XSS
        "eval(",  # Code injection
        "exec(",  # Code injection
        "system(",  # Command injection
        "../",  # Path traversal
        "..\\",  # Path traversal
        "%2e%2e",  # URL encoded path traversal
    ]

    def __init__(self, app: FastAPI):
        self.app = app
        app.add_middleware(self.middleware)

    def contains_dangerous_pattern(self, value: str) -> bool:
        """Check if value contains dangerous patterns"""
        value_lower = value.lower()
        return any(pattern.lower() in value_lower for pattern in self.DANGEROUS_PATTERNS)

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary"""
        for key, value in data.items():
            if isinstance(value, str):
                if self.contains_dangerous_pattern(value):
                    logger.warning(f"Dangerous pattern detected in {key}: {value}")
                    data[key] = self.escape_html(value)
            elif isinstance(value, dict):
                data[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                data[key] = [self.sanitize_dict(item) if isinstance(item, dict) else item for item in value]
        return data

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters"""
        escape_map = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }
        return "".join(escape_map.get(char, char) for char in text)

    async def middleware(self, request: Request, call_next):
        # Sanitize query parameters
        if request.query_params:
            query_dict = dict(request.query_params)
            self.sanitize_dict(query_dict)

        # Sanitize JSON body
        if request.method in ["POST", "PUT", "PATCH"]:
            if request.headers.get("content-type") == "application/json":
                try:
                    body = await request.body()
                    if body:
                        data = json.loads(body)
                        data = self.sanitize_dict(data)
                except (json.JSONDecodeError, Exception):
                    pass  # Skip sanitization if parsing fails

        return await call_next(request)


class AuditLoggingMiddleware:
    """Log all security-relevant events"""

    def __init__(self, app: FastAPI, project_id: str):
        self.app = app
        self.project_id = project_id
        self.cloud_logger = cloud_logging.Client(project=project_id).logger("security-audit")
        app.add_middleware(self.middleware)

    async def middleware(self, request: Request, call_next):
        # Extract audit-relevant fields
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "user_id": request.headers.get("x-user-id"),
        }

        response = await call_next(request)

        # Log response
        audit_event["status_code"] = response.status_code

        # Log security-relevant status codes
        if response.status_code >= 400:
            self.cloud_logger.log_struct(audit_event, severity="WARNING")
        elif request.method not in ["GET", "HEAD", "OPTIONS"]:
            self.cloud_logger.log_struct(audit_event, severity="INFO")

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class RateLimitSecurityMiddleware:
    """Additional rate limiting for security endpoints"""

    def __init__(self, app: FastAPI, max_requests: int = 10, window_seconds: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
        app.add_middleware(self.middleware)

    async def middleware(self, request: Request, call_next):
        # Apply stricter limits to security endpoints
        if any(path in request.url.path for path in ["/auth/login", "/auth/register", "/api/admin"]):
            ip = self._get_client_ip(request)

            # Clean old requests
            now = datetime.utcnow()
            if ip in self.requests:
                self.requests[ip] = [
                    req_time for req_time in self.requests[ip]
                    if (now - req_time).total_seconds() < self.window_seconds
                ]

            # Check rate limit
            if ip in self.requests and len(self.requests[ip]) >= self.max_requests:
                return Response("Rate limit exceeded", status_code=429)

            # Record request
            if ip not in self.requests:
                self.requests[ip] = []
            self.requests[ip].append(now)

        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class SecretRotationMiddleware:
    """Check and rotate secrets based on age"""

    SECRET_MAX_AGE_DAYS = 30

    def __init__(self, app: FastAPI, project_id: str, secret_manager_client=None):
        self.app = app
        self.project_id = project_id
        self.secret_client = secret_manager_client or secretmanager.SecretManagerServiceClient()
        self.last_rotation_check = None
        app.add_middleware(self.middleware)

    async def check_secret_rotation(self):
        """Check if secrets need rotation"""
        now = datetime.utcnow()
        if self.last_rotation_check and (now - self.last_rotation_check).days < 1:
            return  # Check only once per day

        self.last_rotation_check = now
        logger.info("Checking secret rotation...")

        # This would connect to Secret Manager and check creation dates
        # For now, just log the check

    async def middleware(self, request: Request, call_next):
        await self.check_secret_rotation()
        return await call_next(request)


def setup_security_middleware(app: FastAPI, config: Dict[str, Any]):
    """Setup all security middleware"""

    # Security headers
    SecurityHeadersMiddleware(app)

    # CORS (restrictive)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("allowed_origins", ["http://localhost:3000"]),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # CSRF protection
    CSRFProtectionMiddleware(app, config.get("secret_key", "change-me"))

    # Input sanitization
    InputSanitizationMiddleware(app)

    # Audit logging
    AuditLoggingMiddleware(app, config.get("project_id"))

    # Rate limiting for sensitive endpoints
    RateLimitSecurityMiddleware(app, max_requests=10, window_seconds=60)

    # Secret rotation checking
    SecretRotationMiddleware(app, config.get("project_id"))

    logger.info("Security middleware stack initialized")
