"""
FAANG-Grade Error Handling for Landing Zone Portal.

Implements:
- Structured error responses
- Error classification
- Safe error messages (no internal leaks)
- Error tracking and metrics
"""
import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ============================================================================
# Error Models
# ============================================================================


class ErrorDetail(BaseModel):
    """Detailed error information for API responses."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    error: bool = Field(True, description="Indicates this is an error response")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    request_id: str = Field(..., description="Unique request identifier for tracking")
    timestamp: str = Field(..., description="Error timestamp in ISO format")
    path: str = Field(..., description="Request path that caused the error")
    errors: list[ErrorDetail] = Field(default_factory=list, description="List of specific errors")

    # Only included in non-production
    debug: Optional[Dict[str, Any]] = Field(
        None, description="Debug information (non-production only)"
    )


# ============================================================================
# Error Codes
# ============================================================================


class ErrorCode:
    """Standardized error codes."""

    # Authentication & Authorization (401, 403)
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"

    # Validation (400, 422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"

    # Resource errors (404, 409)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"

    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (500, 502, 503)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    GCP_API_ERROR = "GCP_API_ERROR"

    # Business logic
    OPERATION_FAILED = "OPERATION_FAILED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


# ============================================================================
# Custom Exceptions
# ============================================================================


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        errors: Optional[list[ErrorDetail]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.errors = errors or []
        super().__init__(self.message)


class ValidationException(AppException):
    """Validation error exception."""

    def __init__(self, message: str, errors: list[ErrorDetail] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=errors or [],
        )


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class AuthenticationException(AppException):
    """Authentication error exception."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTH_REQUIRED,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationException(AppException):
    """Authorization error exception."""

    def __init__(self, message: str = "Insufficient permissions", required_permission: str = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            status_code=status.HTTP_403_FORBIDDEN,
            details={"required_permission": required_permission} if required_permission else None,
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded. Please slow down.",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after},
        )


class ServiceUnavailableException(AppException):
    """Service unavailable exception."""

    def __init__(self, service: str, message: str = None):
        super().__init__(
            message=message or f"Service temporarily unavailable: {service}",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service},
        )


class GCPAPIException(AppException):
    """GCP API error exception."""

    def __init__(self, service: str, operation: str, original_error: str = None):
        super().__init__(
            message=f"GCP {service} operation failed",
            error_code=ErrorCode.GCP_API_ERROR,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service, "operation": operation},
        )
        # Log the original error internally but don't expose it
        if original_error:
            logger.error(f"GCP API Error [{service}/{operation}]: {original_error}")


# ============================================================================
# Error Handler Functions
# ============================================================================


def create_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    errors: list[ErrorDetail] = None,
    details: Dict[str, Any] = None,
    include_debug: bool = False,
) -> JSONResponse:
    """Create a standardized error response."""

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    response_data = ErrorResponse(
        error_code=error_code,
        message=message,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
        path=str(request.url.path),
        errors=errors or [],
    )

    # Include debug info in non-production
    if include_debug and details:
        response_data.debug = details

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump(exclude_none=True)
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""

    logger.warning(
        f"AppException: {exc.error_code} - {exc.message}",
        extra={"correlation_id": getattr(request.state, "request_id", "unknown")},
    )

    return create_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        errors=exc.errors,
        details=exc.details,
        include_debug=not is_production(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""

    # Map status codes to error codes
    error_code_map = {
        400: ErrorCode.INVALID_REQUEST,
        401: ErrorCode.AUTH_REQUIRED,
        403: ErrorCode.AUTH_FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        405: ErrorCode.INVALID_REQUEST,
        409: ErrorCode.RESOURCE_CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.DEPENDENCY_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    message = exc.detail if isinstance(exc.detail, str) else "An error occurred"

    return create_error_response(
        request=request, status_code=exc.status_code, error_code=error_code, message=message
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""

    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(ErrorDetail(code="INVALID_FIELD", message=error["msg"], field=field))

    return create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions safely."""

    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]
    req_id = getattr(request.state, "request_id", "unknown")

    # Log full exception for debugging
    logger.error(
        f"Unhandled exception [error_id={error_id}] [req_id={req_id}]: {type(exc).__name__}: {str(exc)}",
        extra={
            "correlation_id": req_id,
            "error_id": error_id,
            "path": str(request.url.path),
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
    )

    # Return safe error message (no internal details)
    return create_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_ERROR,
        message=f"An internal error occurred. Reference: {error_id}",
        include_debug=False,  # Never include debug for unhandled exceptions
    )


# ============================================================================
# Utility Functions
# ============================================================================


def is_production() -> bool:
    """Check if running in production environment."""
    import os

    return os.getenv("ENVIRONMENT", "development") in ("production", "prod")


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
