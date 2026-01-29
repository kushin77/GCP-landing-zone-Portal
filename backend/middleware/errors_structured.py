"""
Structured error handling for production reliability.
Fixes issue #41: Zero Error Handling in Production.

Provides:
- Structured exception hierarchy
- Error code standardization
- Audit trail for errors
- Retry recommendations
- SLI metrics
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ============================================================================
# Error Codes
# ============================================================================

class ErrorCode(str, Enum):
    """Standardized error codes for monitoring and alerting."""

    # Authentication errors (1xx)
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"

    # Validation errors (2xx)
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_PARAMETER = "INVALID_PARAMETER"

    # Resource errors (3xx)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # Rate limiting (4xx)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # Service errors (5xx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_TIMEOUT = "SERVICE_TIMEOUT"
    SERVICE_DEGRADED = "SERVICE_DEGRADED"

    # Database errors (6xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    DATABASE_QUOTA_EXCEEDED = "DATABASE_QUOTA_EXCEEDED"

    # GCP errors (7xx)
    GCP_API_ERROR = "GCP_API_ERROR"
    GCP_QUOTA_EXCEEDED = "GCP_QUOTA_EXCEEDED"
    GCP_PERMISSION_DENIED = "GCP_PERMISSION_DENIED"
    GCP_INVALID_CREDENTIALS = "GCP_INVALID_CREDENTIALS"

    # Network errors (8xx)
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"

    # Internal errors (9xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# ============================================================================
# Exception Hierarchy
# ============================================================================

class LandingZoneException(Exception):
    """Base exception for Landing Zone Portal."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        http_status: int = 500,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

        super().__init__(f"[{code}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "error": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


# Authentication exceptions
class AuthenticationError(LandingZoneException):
    """Authentication failed."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.AUTH_REQUIRED,
            message=message,
            http_status=401,
            details=details,
        )


class InvalidTokenError(LandingZoneException):
    """Token is invalid or malformed."""

    def __init__(self, message: str = "Invalid token", details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message=message,
            http_status=401,
            details=details,
        )


class TokenExpiredError(LandingZoneException):
    """Token has expired."""

    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Token expired",
            http_status=401,
            retryable=False,  # Client must refresh token
            details=details,
        )


class PermissionDeniedError(LandingZoneException):
    """User lacks required permission."""

    def __init__(
        self, required_permission: str, details: Optional[Dict] = None
    ):
        super().__init__(
            code=ErrorCode.AUTH_PERMISSION_DENIED,
            message=f"Permission denied: {required_permission}",
            http_status=403,
            details=details or {"required_permission": required_permission},
        )


# Validation exceptions
class ValidationError(LandingZoneException):
    """Input validation failed."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_FAILED,
            message=message,
            http_status=400,
            details=details,
        )


class InvalidParameterError(LandingZoneException):
    """Invalid parameter value."""

    def __init__(self, param_name: str, reason: str):
        super().__init__(
            code=ErrorCode.INVALID_PARAMETER,
            message=f"Invalid parameter {param_name}: {reason}",
            http_status=400,
            details={"parameter": param_name, "reason": reason},
        )


# Resource exceptions
class ResourceNotFoundError(LandingZoneException):
    """Resource not found."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=f"{resource_type} not found: {resource_id}",
            http_status=404,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class ResourceAlreadyExistsError(LandingZoneException):
    """Resource already exists."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            code=ErrorCode.RESOURCE_ALREADY_EXISTS,
            message=f"{resource_type} already exists: {resource_id}",
            http_status=409,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


# Rate limiting exceptions
class RateLimitExceededError(LandingZoneException):
    """Rate limit exceeded."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        retry_after: int,
        details: Optional[Dict] = None,
    ):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            http_status=429,
            retryable=True,
            details=details
            or {
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after,
            },
        )
        self.retry_after = retry_after


class QuotaExceededError(LandingZoneException):
    """Quota limit exceeded."""

    def __init__(
        self,
        quota_name: str,
        used: int,
        limit: int,
        details: Optional[Dict] = None,
    ):
        super().__init__(
            code=ErrorCode.QUOTA_EXCEEDED,
            message=f"Quota exceeded: {quota_name} ({used}/{limit})",
            http_status=429,
            retryable=False,
            details=details
            or {"quota_name": quota_name, "used": used, "limit": limit},
        )


# Service exceptions
class ServiceUnavailableError(LandingZoneException):
    """Service temporarily unavailable."""

    def __init__(
        self, service_name: str, retry_after: Optional[int] = None, details: Optional[Dict] = None
    ):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=f"Service unavailable: {service_name}",
            http_status=503,
            retryable=True,
            details=details or {"service": service_name, "retry_after": retry_after},
        )
        self.retry_after = retry_after


class ServiceTimeoutError(LandingZoneException):
    """Service request timed out."""

    def __init__(
        self, service_name: str, timeout_seconds: float, details: Optional[Dict] = None
    ):
        super().__init__(
            code=ErrorCode.SERVICE_TIMEOUT,
            message=f"Service timeout: {service_name} ({timeout_seconds}s)",
            http_status=504,
            retryable=True,
            details=details
            or {"service": service_name, "timeout_seconds": timeout_seconds},
        )


# Database exceptions
class DatabaseError(LandingZoneException):
    """Database operation failed."""

    def __init__(
        self,
        operation: str,
        reason: str,
        retryable: bool = False,
        details: Optional[Dict] = None,
    ):
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=f"Database error: {operation} ({reason})",
            http_status=500,
            retryable=retryable,
            details=details
            or {"operation": operation, "reason": reason},
        )


class DatabaseQuotaExceededError(LandingZoneException):
    """Database quota exceeded."""

    def __init__(
        self, quota_type: str, used: int, limit: int, details: Optional[Dict] = None
    ):
        super().__init__(
            code=ErrorCode.DATABASE_QUOTA_EXCEEDED,
            message=f"Database quota exceeded: {quota_type}",
            http_status=429,
            retryable=False,
            details=details
            or {"quota_type": quota_type, "used": used, "limit": limit},
        )


# GCP exceptions
class GCPError(LandingZoneException):
    """GCP API error."""

    def __init__(
        self,
        api_name: str,
        status_code: int,
        reason: str,
        retryable: bool = False,
        details: Optional[Dict] = None,
    ):
        # Map GCP status codes to appropriate error codes
        if status_code == 429:
            code = ErrorCode.GCP_QUOTA_EXCEEDED
        elif status_code == 403:
            code = ErrorCode.GCP_PERMISSION_DENIED
        elif status_code == 401:
            code = ErrorCode.GCP_INVALID_CREDENTIALS
        else:
            code = ErrorCode.GCP_API_ERROR

        # GCP 5xx errors are generally retryable
        if 500 <= status_code < 600:
            retryable = True

        http_status = min(status_code, 503)  # Don't expose GCP status directly

        super().__init__(
            code=code,
            message=f"GCP API error: {api_name} ({status_code}): {reason}",
            http_status=http_status,
            retryable=retryable,
            details=details
            or {
                "api": api_name,
                "gcp_status_code": status_code,
                "reason": reason,
            },
        )


# ============================================================================
# Error Recovery Helpers
# ============================================================================

def classify_gcp_error(error: Exception) -> LandingZoneException:
    """Classify GCP error into appropriate exception type."""
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Quota exceeded
    if "quota" in error_str or "exceeded" in error_str:
        return GCPError(
            api_name="unknown",
            status_code=429,
            reason="Quota exceeded",
            retryable=False,
        )

    # Permission denied
    if "permission" in error_str or "forbidden" in error_str:
        return GCPError(
            api_name="unknown",
            status_code=403,
            reason="Permission denied",
            retryable=False,
        )

    # Invalid credentials
    if "credential" in error_str or "unauthorized" in error_str:
        return GCPError(
            api_name="unknown",
            status_code=401,
            reason="Invalid credentials",
            retryable=False,
        )

    # Network/timeout errors
    if "timeout" in error_str or "connection" in error_str:
        return ServiceTimeoutError(
            service_name="gcp_api",
            timeout_seconds=30,
        )

    # Default
    return GCPError(
        api_name="unknown",
        status_code=500,
        reason=str(error),
        retryable=True,
    )


def is_retryable_error(error: Exception) -> bool:
    """Check if error is retryable."""
    if isinstance(error, LandingZoneException):
        return error.retryable

    # Classify GCP errors
    if "googleapi" in type(error).__module__:
        classified = classify_gcp_error(error)
        return classified.retryable

    # Default: not retryable
    return False


def should_circuit_break(error: Exception) -> bool:
    """Check if error should trigger circuit breaker."""
    if isinstance(error, LandingZoneException):
        # Circuit break on unavailable/quota errors
        return error.code in (
            ErrorCode.SERVICE_UNAVAILABLE,
            ErrorCode.QUOTA_EXCEEDED,
            ErrorCode.DATABASE_QUOTA_EXCEEDED,
        )
    return False
