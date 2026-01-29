"""
Unit tests for the Authentication module.

Tests cover:
- Token validation
- User authentication flow
- RBAC permissions
- Auth middleware
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException

from middleware.auth import (
    User,
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_roles,
    get_current_user,
    require_permissions,
    require_roles,
    AuthConfig,
    AuthenticationService,
    IAPTokenValidator,
    OAuth2TokenValidator,
)


class TestPermissions:
    """Tests for permission calculations."""

    def test_viewer_has_read_permissions(self):
        """Viewer role should have read-only permissions."""
        perms = get_permissions_for_roles(["viewer"])

        assert Permission.PROJECTS_READ in perms
        assert Permission.COSTS_READ in perms
        assert Permission.COMPLIANCE_READ in perms
        assert Permission.PROJECTS_WRITE not in perms
        assert Permission.ADMIN_USERS not in perms

    def test_editor_has_write_permissions(self):
        """Editor role should have write permissions."""
        perms = get_permissions_for_roles(["editor"])

        assert Permission.PROJECTS_READ in perms
        assert Permission.PROJECTS_WRITE in perms
        assert Permission.WORKFLOWS_APPROVE in perms
        assert Permission.PROJECTS_DELETE not in perms
        assert Permission.ADMIN_USERS not in perms

    def test_admin_has_all_permissions(self):
        """Admin role should have all permissions."""
        perms = get_permissions_for_roles(["admin"])

        assert Permission.PROJECTS_READ in perms
        assert Permission.PROJECTS_WRITE in perms
        assert Permission.PROJECTS_DELETE in perms
        assert Permission.ADMIN_USERS in perms
        assert Permission.ADMIN_CONFIG in perms

    def test_multiple_roles_combine_permissions(self):
        """Multiple roles should combine their permissions."""
        perms = get_permissions_for_roles(["viewer", "editor"])

        # Should have all viewer and editor permissions
        assert Permission.PROJECTS_READ in perms
        assert Permission.PROJECTS_WRITE in perms
        assert Permission.WORKFLOWS_APPROVE in perms

    def test_unknown_role_returns_empty(self):
        """Unknown role should return empty permissions."""
        perms = get_permissions_for_roles(["unknown_role"])
        assert len(perms) == 0


class TestUserModel:
    """Tests for User model."""

    def test_user_is_admin_property(self):
        """is_admin property should return True for admin role."""
        admin = User(
            id="1",
            email="admin@test.com",
            roles=["admin"],
            permissions=[],
            auth_method="test"
        )
        viewer = User(
            id="2",
            email="viewer@test.com",
            roles=["viewer"],
            permissions=[],
            auth_method="test"
        )

        assert admin.is_admin is True
        assert viewer.is_admin is False

    def test_user_domain_extraction(self):
        """domain property should extract domain from email."""
        user = User(
            id="1",
            email="user@example.com",
            roles=["viewer"],
            permissions=[],
            auth_method="test"
        )

        assert user.domain == "example.com"


class TestAuthenticationService:
    """Tests for AuthenticationService."""

    @pytest.mark.asyncio
    async def test_authenticate_no_headers_returns_none(self):
        """Missing auth headers should return None."""
        service = AuthenticationService()

        request = MagicMock()
        request.headers = {}
        request.headers.get = lambda x, default="": default

        user = await service.authenticate(request)
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_bearer_returns_none(self):
        """Invalid bearer token should return None."""
        service = AuthenticationService()

        request = MagicMock()
        request.headers = {"authorization": "Bearer invalid_token"}
        request.headers.get = lambda x, default="": request.headers.get(x, default)

        with patch.object(OAuth2TokenValidator, "validate", return_value=None):
            with patch.object(IAPTokenValidator, "validate", return_value=None):
                user = await service.authenticate(request)
                # Will be None because token validation fails
                assert user is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_unauthenticated_in_production_raises(self):
        """Unauthenticated request in production should raise 401."""
        with patch.object(AuthConfig, "IS_PRODUCTION", True):
            with patch.object(AuthConfig, "REQUIRE_AUTH", True):
                request = MagicMock()
                request.headers = {}
                request.headers.get = lambda x, default="": default

                with patch("middleware.auth.auth_service.authenticate", return_value=None):
                    with pytest.raises(HTTPException) as exc_info:
                        await get_current_user(request, None)

                    assert exc_info.value.status_code == 401


class TestRequirePermissions:
    """Tests for require_permissions decorator."""

    @pytest.mark.asyncio
    async def test_missing_permission_raises_403(self):
        """Missing permission should raise 403."""
        user = User(
            id="1",
            email="viewer@test.com",
            roles=["viewer"],
            permissions=[Permission.PROJECTS_READ],
            auth_method="test"
        )

        @require_permissions(Permission.ADMIN_USERS)
        async def protected_func(user=None):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await protected_func(user=user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_has_permission_succeeds(self):
        """Having required permission should succeed."""
        user = User(
            id="1",
            email="admin@test.com",
            roles=["admin"],
            permissions=[Permission.ADMIN_USERS],
            auth_method="test"
        )

        @require_permissions(Permission.ADMIN_USERS)
        async def protected_func(user=None):
            return "success"

        result = await protected_func(user=user)
        assert result == "success"


class TestRequireRoles:
    """Tests for require_roles decorator."""

    @pytest.mark.asyncio
    async def test_missing_role_raises_403(self):
        """Missing role should raise 403."""
        user = User(
            id="1",
            email="viewer@test.com",
            roles=["viewer"],
            permissions=[],
            auth_method="test"
        )

        @require_roles("admin")
        async def admin_only(user=None):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await admin_only(user=user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_has_role_succeeds(self):
        """Having required role should succeed."""
        user = User(
            id="1",
            email="admin@test.com",
            roles=["admin"],
            permissions=[],
            auth_method="test"
        )

        @require_roles("admin")
        async def admin_only(user=None):
            return "success"

        result = await admin_only(user=user)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_one_of_multiple_roles_succeeds(self):
        """Having one of multiple required roles should succeed."""
        user = User(
            id="1",
            email="editor@test.com",
            roles=["editor"],
            permissions=[],
            auth_method="test"
        )

        @require_roles("admin", "editor")
        async def admin_or_editor(user=None):
            return "success"

        result = await admin_or_editor(user=user)
        assert result == "success"
