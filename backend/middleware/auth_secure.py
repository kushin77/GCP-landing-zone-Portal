"""
Enhanced authentication with proper JWT validation, RBAC, and audit logging.
Fixes issue #43: Authentication & Authorization System vulnerabilities.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import google.auth.exceptions
from fastapi import Depends, HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class AuthConfig:
    """Authentication configuration with production safety."""

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION = ENVIRONMENT in ("production", "staging")

    # IAP settings - MUST be set in production
    IAP_AUDIENCE = os.getenv("IAP_AUDIENCE", "")
    IAP_ISSUER = "https://cloud.google.com/iap"

    # JWT validation
    JWT_ALGORITHMS = ["RS256", "ES256"]
    CLOCK_SKEW_SECONDS = 10
    TOKEN_EXPIRY_BUFFER_SECONDS = 60

    # Deny dev bypass in production-like environments
    ALLOW_DEV_BYPASS = os.getenv("ALLOW_DEV_BYPASS", "false").lower() == "true" and ENVIRONMENT in (
        "development",
        "test",
        "local",
    )  # NEVER staging/production

    # Admin emails
    ADMIN_EMAILS = [e.strip() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]

    @classmethod
    def validate(cls):
        """Validate auth config on startup."""
        if cls.IS_PRODUCTION and not cls.IAP_AUDIENCE:
            raise RuntimeError("IAP_AUDIENCE must be set in production environments")
        logger.info(f"Auth config: env={cls.ENVIRONMENT}, dev_bypass={cls.ALLOW_DEV_BYPASS}")


# ============================================================================
# Roles and Permissions
# ============================================================================


class Role:
    """Role constants."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    SERVICE = "service"


class Permission:
    """Permission constants - granular access control."""

    # Projects
    PROJECTS_READ = "projects:read"
    PROJECTS_CREATE = "projects:create"
    PROJECTS_MODIFY = "projects:modify"
    PROJECTS_DELETE = "projects:delete"

    # Costs
    COSTS_READ = "costs:read"
    COSTS_EXPORT = "costs:export"

    # Compliance
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_MANAGE = "compliance:manage"

    # Workflows
    WORKFLOWS_READ = "workflows:read"
    WORKFLOWS_APPROVE = "workflows:approve"
    WORKFLOWS_MANAGE = "workflows:manage"

    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_CONFIG = "admin:config"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Role.VIEWER: [
        Permission.PROJECTS_READ,
        Permission.COSTS_READ,
        Permission.COMPLIANCE_READ,
        Permission.WORKFLOWS_READ,
    ],
    Role.EDITOR: [
        Permission.PROJECTS_READ,
        Permission.PROJECTS_CREATE,
        Permission.PROJECTS_MODIFY,
        Permission.COSTS_READ,
        Permission.COSTS_EXPORT,
        Permission.COMPLIANCE_READ,
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_APPROVE,
    ],
    Role.ADMIN: [
        Permission.PROJECTS_READ,
        Permission.PROJECTS_CREATE,
        Permission.PROJECTS_MODIFY,
        Permission.PROJECTS_DELETE,
        Permission.COSTS_READ,
        Permission.COSTS_EXPORT,
        Permission.COMPLIANCE_READ,
        Permission.COMPLIANCE_MANAGE,
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_APPROVE,
        Permission.WORKFLOWS_MANAGE,
        Permission.ADMIN_USERS,
        Permission.ADMIN_AUDIT,
        Permission.ADMIN_CONFIG,
    ],
    Role.SERVICE: [
        Permission.PROJECTS_READ,
        Permission.PROJECTS_CREATE,
        Permission.COSTS_READ,
        Permission.COMPLIANCE_READ,
    ],
}


def get_permissions_for_roles(roles: List[str]) -> List[str]:
    """Compute all permissions for a list of roles."""
    permissions = set()
    for role in roles:
        role_perms = ROLE_PERMISSIONS.get(role.lower(), [])
        permissions.update(role_perms)
    return sorted(list(permissions))


# ============================================================================
# User Model
# ============================================================================


class AuthenticatedUser:
    """Authenticated user with validated claims."""

    def __init__(
        self,
        user_id: str,
        email: str,
        roles: List[str],
        auth_method: str,
        token_exp: Optional[int] = None,
        name: str = "",
        organization: Optional[str] = None,
    ):
        self.id = user_id
        self.email = email
        self.roles = roles
        self.permissions = get_permissions_for_roles(roles)
        self.auth_method = auth_method
        self.token_exp = token_exp
        self.name = name
        self.organization = organization

    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.email.split("@")[1] if "@" in self.email else ""

    def has_permission(self, permission: str) -> bool:
        """Check if user has permission."""
        return permission in self.permissions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "id": self.id,
            "email": self.email,
            "roles": self.roles,
            "auth_method": self.auth_method,
            "is_admin": self.is_admin,
        }


# ============================================================================
# JWT Validation
# ============================================================================


class JWTValidator:
    """Validates JWT tokens with signature verification."""

    def __init__(self):
        self._request_adapter = google_requests.Request()

    def validate_iap_token(self, token: str) -> Dict[str, Any]:
        """
        Validate Google IAP JWT with signature verification.

        Raises:
            ValueError: If token is invalid
        """
        if not AuthConfig.IAP_AUDIENCE:
            raise ValueError("IAP_AUDIENCE not configured")

        try:
            # Verify JWT signature and get claims
            claims = google_id_token.verify_oauth2_token(
                token, self._request_adapter, clock_skew_in_seconds=AuthConfig.CLOCK_SKEW_SECONDS
            )

            # Validate issuer
            if claims.get("iss") != AuthConfig.IAP_ISSUER:
                raise ValueError(f"Invalid issuer: {claims.get('iss')}")

            # Validate audience
            if claims.get("aud") != AuthConfig.IAP_AUDIENCE:
                raise ValueError(f"Invalid audience: {claims.get('aud')}")

            # Validate expiration
            exp = claims.get("exp", 0)
            if exp < time.time():
                raise ValueError("Token expired")

            return claims

        except google.auth.exceptions.GoogleAuthError as e:
            logger.error(f"JWT validation failed: {e}")
            raise ValueError(f"JWT validation failed: {e}") from e

    def validate_oauth_token(self, token: str) -> Dict[str, Any]:
        """Validate Google OAuth token."""
        try:
            claims = google_id_token.verify_oauth2_token(
                token, self._request_adapter, clock_skew_in_seconds=AuthConfig.CLOCK_SKEW_SECONDS
            )

            # Validate client ID if configured
            if AuthConfig.OAUTH_CLIENT_ID and claims.get("aud") != AuthConfig.OAUTH_CLIENT_ID:
                raise ValueError("Invalid client ID")

            # Validate expiration
            exp = claims.get("exp", 0)
            if exp < time.time():
                raise ValueError("Token expired")

            return claims

        except google.auth.exceptions.GoogleAuthError as e:
            logger.error(f"OAuth token validation failed: {e}")
            raise ValueError(f"OAuth validation failed: {e}") from e


# ============================================================================
# Audit Logging
# ============================================================================


class AuditLogger:
    """Immutable audit logging for security events."""

    @staticmethod
    async def log_auth_event(
        user_id: str,
        email: str,
        action: str,  # "login", "permission_denied", "failed_validation", etc.
        status: str,  # "success", "denied", "failed"
        ip_address: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log authentication event."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "email": email,
            "action": action,
            "status": status,
            "ip_address": ip_address,
            "details": details or {},
        }

        # In production, send to Cloud Logging
        if AuthConfig.IS_PRODUCTION:
            try:
                from google.cloud import logging as cloud_logging

                client = cloud_logging.Client()
                logger_obj = client.logger("auth-audit")
                logger_obj.log_struct(event, severity="INFO")
            except Exception as e:
                logger.error(f"Failed to log to Cloud Logging: {e}")
                # Fall back to stderr
                logger.info(f"AUDIT: {json.dumps(event)}")
        else:
            logger.info(f"AUDIT: {json.dumps(event)}")

    @staticmethod
    async def log_permission_denied(
        user_id: str,
        email: str,
        required_permission: str,
        action: str,
        resource: str,
        ip_address: str,
    ):
        """Log permission denied event."""
        await AuditLogger.log_auth_event(
            user_id=user_id,
            email=email,
            action="permission_denied",
            status="denied",
            ip_address=ip_address,
            details={
                "required_permission": required_permission,
                "attempted_action": action,
                "resource": resource,
            },
        )


# ============================================================================
# Authentication Functions
# ============================================================================


def extract_user_from_iap_claims(claims: Dict[str, Any]) -> AuthenticatedUser:
    """Extract user info from IAP JWT claims."""
    user_email = claims.get("email", "unknown@example.com")
    user_id = claims.get("sub", claims.get("user_id", ""))

    # Determine roles based on email
    roles = [Role.VIEWER]  # Default role

    # Check if admin
    if user_email in AuthConfig.ADMIN_EMAILS:
        roles = [Role.ADMIN]

    return AuthenticatedUser(
        user_id=user_id,
        email=user_email,
        roles=roles,
        auth_method="iap",
        token_exp=claims.get("exp"),
        name=claims.get("name", ""),
    )


def extract_user_from_oauth_claims(claims: Dict[str, Any]) -> AuthenticatedUser:
    """Extract user info from OAuth claims."""
    user_email = claims.get("email", "unknown@example.com")
    user_id = claims.get("sub", "")

    # Determine roles
    roles = [Role.VIEWER]  # Default role

    if user_email in AuthConfig.ADMIN_EMAILS:
        roles = [Role.ADMIN]

    return AuthenticatedUser(
        user_id=user_id,
        email=user_email,
        roles=roles,
        auth_method="oauth",
        token_exp=claims.get("exp"),
        name=claims.get("name", ""),
    )


# ============================================================================
# FastAPI Dependencies
# ============================================================================


async def get_current_user(request: Request) -> Optional[AuthenticatedUser]:
    """
    Get current user from request.

    Priority:
    1. IAP JWT (if deployed behind Cloud IAP)
    2. Authorization header (OAuth token)
    3. Dev bypass (only in development)
    """
    # Check for dev bypass (ONLY in development)
    if AuthConfig.ALLOW_DEV_BYPASS:
        dev_email = os.getenv("DEV_EMAIL", "dev@example.com")
        logger.warning(f"Using dev bypass with email: {dev_email}")
        return AuthenticatedUser(
            user_id="dev-user",
            email=dev_email,
            roles=[Role.ADMIN],
            auth_method="dev_bypass",
        )

    # Try IAP JWT first
    iap_jwt = request.headers.get("x-goog-iap-jwt-assertion")
    if iap_jwt:
        try:
            validator = JWTValidator()
            claims = validator.validate_iap_token(iap_jwt)
            user = extract_user_from_iap_claims(claims)
            logger.info(f"User authenticated via IAP: {user.email}")
            return user
        except ValueError as e:
            logger.error(f"IAP JWT validation failed: {e}")
            await AuditLogger.log_auth_event(
                user_id="unknown",
                email="unknown",
                action="iap_jwt_validation_failed",
                status="failed",
                ip_address=request.client.host if request.client else "unknown",
                details={"error": str(e)},
            )
            raise HTTPException(status_code=401, detail="Invalid IAP token")

    # Try Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")

            validator = JWTValidator()
            claims = validator.validate_oauth_token(token)
            user = extract_user_from_oauth_claims(claims)
            logger.info(f"User authenticated via OAuth: {user.email}")
            return user
        except ValueError as e:
            logger.error(f"OAuth token validation failed: {e}")
            await AuditLogger.log_auth_event(
                user_id="unknown",
                email="unknown",
                action="oauth_token_validation_failed",
                status="failed",
                ip_address=request.client.host if request.client else "unknown",
                details={"error": str(e)},
            )
            raise HTTPException(status_code=401, detail="Invalid token")

    # No auth found
    logger.warning("No authentication found in request")
    raise HTTPException(status_code=401, detail="Authentication required")


async def require_permission(permission: str):
    """Dependency to require specific permission."""

    async def check_permission(user: AuthenticatedUser = Depends(get_current_user)):
        if not user.has_permission(permission):
            logger.warning(f"Permission denied for user {user.email}: required {permission}")
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user

    return check_permission


async def require_admin(user: AuthenticatedUser = Depends(get_current_user)):
    """Dependency to require admin role."""
    if not user.is_admin:
        await AuditLogger.log_permission_denied(
            user_id=user.id,
            email=user.email,
            required_permission="admin",
            action="admin_action",
            resource="system",
            ip_address="unknown",
        )
        logger.warning(f"Admin action attempted by non-admin: {user.email}")
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
