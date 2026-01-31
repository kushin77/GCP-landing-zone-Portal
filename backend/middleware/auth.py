"""
FAANG-Grade Authentication Middleware for Landing Zone Portal.

Implements:
- Google IAP JWT validation
- OAuth 2.0 token verification
- Role-based access control (RBAC)
- Audit logging for all auth events
"""
import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import google.auth.exceptions
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth import jwt as google_jwt

# Google Auth libraries
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================


class AuthConfig:
    """Authentication configuration from environment."""

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

    # Google IAP settings
    IAP_AUDIENCE = os.getenv(
        "IAP_AUDIENCE", ""
    )  # /projects/{project_number}/global/backendServices/{service_id}
    IAP_ISSUER = "https://cloud.google.com/iap"

    # OAuth settings
    OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
    OAUTH_ALLOWED_DOMAINS = [d for d in os.getenv("OAUTH_ALLOWED_DOMAINS", "").split(",") if d]

    # JWT settings
    JWT_ALGORITHMS = ["RS256", "ES256"]
    TOKEN_EXPIRY_BUFFER_SECONDS = 60

    # RBAC
    ADMIN_EMAILS = [e for e in os.getenv("ADMIN_EMAILS", "").split(",") if e]

    # Feature flags
    REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    ALLOW_DEV_BYPASS = (
        os.getenv("ALLOW_DEV_BYPASS", "false").lower() == "true" and not IS_PRODUCTION
    )


# ============================================================================
# Models
# ============================================================================


class User(BaseModel):
    """Authenticated user model."""

    id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(default="", description="Display name")
    picture: Optional[str] = Field(default=None, description="Profile picture URL")
    roles: List[str] = Field(default_factory=list, description="Assigned roles")
    permissions: List[str] = Field(default_factory=list, description="Computed permissions")
    organization: Optional[str] = Field(default=None, description="Organization/domain")
    auth_method: str = Field(..., description="Authentication method used")
    token_exp: Optional[int] = Field(default=None, description="Token expiration timestamp")

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def domain(self) -> str:
        return self.email.split("@")[1] if "@" in self.email else ""


# ============================================================================
# Role-Based Access Control
# ============================================================================


class Permission:
    """Permission constants."""

    # Projects
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
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
    WORKFLOWS_ADMIN = "workflows:admin"

    # AI
    AI_QUERY = "ai:query"
    AI_ADMIN = "ai:admin"

    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_CONFIG = "admin:config"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "viewer": [
        Permission.PROJECTS_READ,
        Permission.COSTS_READ,
        Permission.COMPLIANCE_READ,
        Permission.WORKFLOWS_READ,
        Permission.AI_QUERY,
    ],
    "editor": [
        Permission.PROJECTS_READ,
        Permission.PROJECTS_WRITE,
        Permission.COSTS_READ,
        Permission.COSTS_EXPORT,
        Permission.COMPLIANCE_READ,
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_APPROVE,
        Permission.AI_QUERY,
    ],
    "admin": [
        Permission.PROJECTS_READ,
        Permission.PROJECTS_WRITE,
        Permission.PROJECTS_DELETE,
        Permission.COSTS_READ,
        Permission.COSTS_EXPORT,
        Permission.COMPLIANCE_READ,
        Permission.COMPLIANCE_MANAGE,
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_APPROVE,
        Permission.WORKFLOWS_ADMIN,
        Permission.AI_QUERY,
        Permission.AI_ADMIN,
        Permission.ADMIN_USERS,
        Permission.ADMIN_AUDIT,
        Permission.ADMIN_CONFIG,
    ],
    "service": [
        Permission.PROJECTS_READ,
        Permission.PROJECTS_WRITE,
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
    return list(permissions)


# ============================================================================
# Token Validators
# ============================================================================


class TokenValidator:
    """Base token validator."""

    def __init__(self):
        self._request_adapter = google_requests.Request()

    async def validate(self, token: str, request: Request) -> Optional[User]:
        """Validate token and return user. Override in subclasses."""
        raise NotImplementedError


class IAPTokenValidator(TokenValidator):
    """Validates Google Identity-Aware Proxy JWT tokens."""

    async def validate(self, token: str, request: Request) -> Optional[User]:
        """Validate IAP JWT from x-goog-iap-jwt-assertion header."""
        try:
            # Get the IAP JWT from header (passed by IAP proxy)
            iap_jwt = request.headers.get("x-goog-iap-jwt-assertion")
            if not iap_jwt:
                return None

            # Verify the JWT
            if not AuthConfig.IAP_AUDIENCE:
                logger.error("IAP_AUDIENCE not configured")
                return None

            # Decode and verify the IAP JWT
            decoded = id_token.verify_token(
                iap_jwt,
                self._request_adapter,
                audience=AuthConfig.IAP_AUDIENCE,
                certs_url="https://www.gstatic.com/iap/verify/public_key",
            )

            email = decoded.get("email", "")

            # Determine roles based on email/groups
            roles = self._get_roles_for_user(email, decoded)

            return User(
                id=decoded.get("sub", ""),
                email=email,
                name=decoded.get("name", email.split("@")[0]),
                roles=roles,
                permissions=get_permissions_for_roles(roles),
                organization=decoded.get("hd"),  # Hosted domain
                auth_method="iap",
                token_exp=decoded.get("exp"),
            )

        except google.auth.exceptions.GoogleAuthError as e:
            logger.warning(f"IAP token validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating IAP token: {e}")
            return None

    def _get_roles_for_user(self, email: str, claims: Dict[str, Any]) -> List[str]:
        """Determine user roles based on email and token claims."""
        roles = ["viewer"]  # Default role

        # Check if admin
        if email in AuthConfig.ADMIN_EMAILS:
            roles = ["admin"]

        # Check Google Groups (if available in claims)
        groups = claims.get("google", {}).get("groups", [])
        if "platform-admins@company.com" in groups:
            roles = ["admin"]
        elif "platform-editors@company.com" in groups:
            roles = ["editor"]

        return roles


class OAuth2TokenValidator(TokenValidator):
    """Validates OAuth 2.0 Bearer tokens."""

    async def validate(self, token: str, request: Request) -> Optional[User]:
        """Validate OAuth2 Bearer token."""
        try:
            if not AuthConfig.OAUTH_CLIENT_ID:
                logger.debug("OAuth2 client ID not configured, skipping OAuth2 validation")
                return None

            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, self._request_adapter, AuthConfig.OAUTH_CLIENT_ID
            )

            # Verify issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                logger.warning(f"Invalid token issuer: {idinfo['iss']}")
                return None

            # Verify domain if configured
            email = idinfo.get("email", "")
            domain = email.split("@")[1] if "@" in email else ""

            if AuthConfig.OAUTH_ALLOWED_DOMAINS and domain not in AuthConfig.OAUTH_ALLOWED_DOMAINS:
                logger.warning(f"Domain not allowed: {domain}")
                return None

            # Determine roles
            roles = ["viewer"]
            if email in AuthConfig.ADMIN_EMAILS:
                roles = ["admin"]

            return User(
                id=idinfo.get("sub", ""),
                email=email,
                name=idinfo.get("name", ""),
                picture=idinfo.get("picture"),
                roles=roles,
                permissions=get_permissions_for_roles(roles),
                organization=idinfo.get("hd"),
                auth_method="oauth2",
                token_exp=idinfo.get("exp"),
            )

        except ValueError as e:
            logger.warning(f"OAuth2 token validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating OAuth2 token: {e}")
            return None


class ServiceAccountValidator(TokenValidator):
    """Validates GCP service account tokens for service-to-service auth."""

    async def validate(self, token: str, request: Request) -> Optional[User]:
        """Validate service account token."""
        try:
            # Verify the token - decode to check format first
            claims = google_jwt.decode(token, verify=False)

            # Verify it's a service account
            email = claims.get("email", "")
            if not email.endswith(".iam.gserviceaccount.com"):
                return None

            # Full verification
            if not AuthConfig.OAUTH_CLIENT_ID:
                return None

            idinfo = id_token.verify_token(
                token, self._request_adapter, audience=AuthConfig.OAUTH_CLIENT_ID
            )

            return User(
                id=idinfo.get("sub", ""),
                email=email,
                name=f"Service Account: {email.split('@')[0]}",
                roles=["service"],
                permissions=get_permissions_for_roles(["service"]),
                auth_method="service_account",
                token_exp=idinfo.get("exp"),
            )

        except Exception as e:
            logger.debug(f"Service account validation failed: {e}")
            return None


# ============================================================================
# Authentication Service
# ============================================================================


class AuthenticationService:
    """Central authentication service."""

    def __init__(self):
        self.validators: List[TokenValidator] = [
            IAPTokenValidator(),
            OAuth2TokenValidator(),
            ServiceAccountValidator(),
        ]

    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate request using all available validators."""

        # Check for IAP header first (highest priority)
        iap_jwt = request.headers.get("x-goog-iap-jwt-assertion")
        if iap_jwt:
            validator = IAPTokenValidator()
            user = await validator.validate(iap_jwt, request)
            if user:
                return user

        # Check for Bearer token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

            for validator in self.validators:
                user = await validator.validate(token, request)
                if user:
                    return user

        return None


# Singleton instance
auth_service = AuthenticationService()
security = HTTPBearer(auto_error=False)


# ============================================================================
# Dependency Injection for FastAPI
# ============================================================================


async def get_current_user(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected_endpoint(user: User = Depends(get_current_user)):
            return {"email": user.email}
    """
    # Development bypass (ONLY in non-production with explicit flag)
    if AuthConfig.ALLOW_DEV_BYPASS and not AuthConfig.IS_PRODUCTION:
        dev_user_header = request.headers.get("x-dev-user-email")
        if dev_user_header:
            logger.warning(f"DEV BYPASS: Authenticating as {dev_user_header}")
            return User(
                id="dev-user",
                email=dev_user_header,
                name="Development User",
                roles=["admin"],
                permissions=get_permissions_for_roles(["admin"]),
                auth_method="dev_bypass",
            )

    # Normal authentication flow
    user = await auth_service.authenticate(request)

    if not user:
        if not AuthConfig.REQUIRE_AUTH and not AuthConfig.IS_PRODUCTION:
            # Development fallback with limited permissions
            logger.warning("Auth disabled in development - returning limited viewer user")
            return User(
                id="anonymous-dev",
                email="anonymous@example.com",
                name="Anonymous (Dev Mode)",
                roles=["viewer"],
                permissions=get_permissions_for_roles(["viewer"]),
                auth_method="anonymous",
            )

        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log successful authentication
    logger.info(f"Authenticated user: {user.email} via {user.auth_method}")

    return user


async def get_optional_user(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


# ============================================================================
# Permission Decorators
# ============================================================================


def require_permissions(*required_permissions: str):
    """
    Decorator to require specific permissions for an endpoint.

    Usage:
        @app.get("/admin/users")
        @require_permissions(Permission.ADMIN_USERS)
        async def list_users(user: User = Depends(get_current_user)):
            return {"users": [...]}
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by Depends)
            user: Optional[User] = kwargs.get("user")

            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Check permissions
            missing = [p for p in required_permissions if p not in user.permissions]
            if missing:
                logger.warning(f"Permission denied for {user.email}: missing {missing}")
                raise HTTPException(
                    status_code=403, detail=f"Missing required permissions: {', '.join(missing)}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_roles(*required_roles: str):
    """
    Decorator to require specific roles for an endpoint.

    Usage:
        @app.delete("/projects/{id}")
        @require_roles("admin")
        async def delete_project(id: str, user: User = Depends(get_current_user)):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user: Optional[User] = kwargs.get("user")

            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

            if not any(role in user.roles for role in required_roles):
                logger.warning(f"Role denied for {user.email}: requires one of {required_roles}")
                raise HTTPException(
                    status_code=403, detail=f"Requires one of roles: {', '.join(required_roles)}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Auth Middleware
# ============================================================================


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authentication and request context.
    Adds user info to request state for logging/audit.
    """

    SKIP_PATHS = {"/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks and docs (support base path like /lz)
        path = request.url.path
        if path in self.SKIP_PATHS or path.endswith(tuple(self.SKIP_PATHS)):
            return await call_next(request)

        # Try to authenticate (but don't block - let endpoint decide)
        start_time = time.time()
        user = await auth_service.authenticate(request)
        auth_time = time.time() - start_time

        # Attach to request state for downstream use
        request.state.user = user
        request.state.auth_time = auth_time

        # Add user context to response headers (for debugging)
        response = await call_next(request)

        if user:
            response.headers["X-Authenticated-User"] = user.email
            response.headers["X-Auth-Method"] = user.auth_method

        return response


# ============================================================================
# Audit Logging
# ============================================================================


class AuditLogger:
    """Audit logger for security events."""

    def __init__(self):
        self.logger = logging.getLogger("audit")

    def log_auth_success(self, user: User, request: Request):
        """Log successful authentication."""
        self.logger.info(
            {
                "event": "auth_success",
                "user_id": user.id,
                "email": user.email,
                "auth_method": user.auth_method,
                "ip": request.client.host if request.client else "unknown",
                "path": request.url.path,
                "user_agent": request.headers.get("user-agent", ""),
            }
        )

    def log_auth_failure(self, request: Request, reason: str):
        """Log failed authentication attempt."""
        self.logger.warning(
            {
                "event": "auth_failure",
                "reason": reason,
                "ip": request.client.host if request.client else "unknown",
                "path": request.url.path,
                "user_agent": request.headers.get("user-agent", ""),
            }
        )

    def log_permission_denied(self, user: User, permission: str, request: Request):
        """Log permission denied event."""
        self.logger.warning(
            {
                "event": "permission_denied",
                "user_id": user.id,
                "email": user.email,
                "permission": permission,
                "path": request.url.path,
            }
        )


audit_logger = AuditLogger()
