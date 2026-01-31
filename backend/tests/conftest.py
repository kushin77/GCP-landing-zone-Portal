"""
FAANG-Grade Test Configuration for Landing Zone Portal.

This module provides:
- Pytest fixtures for API testing
- Mock services for GCP clients
- Test database fixtures
- Authentication helpers
"""
import asyncio
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["REQUIRE_AUTH"] = "false"
os.environ["ALLOW_DEV_BYPASS"] = "true"

# Ensure backend package modules are importable when pytest runs from workspace root
import sys
import os as _os
_backend_dir = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_workspace_root = _os.path.abspath(_os.path.join(_backend_dir, ".."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

from main import app  # noqa: E402
from middleware.auth import User, get_permissions_for_roles  # noqa: E402

# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Application Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def test_app() -> FastAPI:
    """Get the FastAPI application for testing."""
    return app


@pytest.fixture(scope="module")
def client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an asynchronous test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def mock_admin_user() -> User:
    """Create a mock admin user."""
    return User(
        id="test-admin-001",
        email="admin@test.example.com",
        name="Test Admin",
        roles=["admin"],
        permissions=get_permissions_for_roles(["admin"]),
        auth_method="test",
        organization="test.example.com",
    )


@pytest.fixture
def mock_editor_user() -> User:
    """Create a mock editor user."""
    return User(
        id="test-editor-001",
        email="editor@test.example.com",
        name="Test Editor",
        roles=["editor"],
        permissions=get_permissions_for_roles(["editor"]),
        auth_method="test",
        organization="test.example.com",
    )


@pytest.fixture
def mock_viewer_user() -> User:
    """Create a mock viewer user."""
    return User(
        id="test-viewer-001",
        email="viewer@test.example.com",
        name="Test Viewer",
        roles=["viewer"],
        permissions=get_permissions_for_roles(["viewer"]),
        auth_method="test",
        organization="test.example.com",
    )


@pytest.fixture
def admin_headers() -> Dict[str, str]:
    """Get headers for admin user authentication in dev mode."""
    return {"X-Dev-User-Email": "admin@test.example.com"}


@pytest.fixture
def editor_headers() -> Dict[str, str]:
    """Get headers for editor user authentication in dev mode."""
    return {"X-Dev-User-Email": "editor@test.example.com"}


@pytest.fixture
def viewer_headers() -> Dict[str, str]:
    """Get headers for viewer user authentication in dev mode."""
    return {"X-Dev-User-Email": "viewer@test.example.com"}


# ============================================================================
# GCP Client Mocks
# ============================================================================


@pytest.fixture
def mock_gcp_clients():
    """Mock all GCP clients."""
    with patch("services.gcp_client.GCPClientManager") as mock:
        manager = MagicMock()

        # Mock Projects client
        manager.projects = MagicMock()
        manager.projects.list_projects.return_value = iter(
            [
                MagicMock(
                    name="projects/123456789",
                    project_id="test-project-1",
                    display_name="Test Project 1",
                    state=MagicMock(name="ACTIVE"),
                    parent="folders/12345",
                    create_time=datetime.utcnow(),
                    labels={"env": "test"},
                ),
                MagicMock(
                    name="projects/987654321",
                    project_id="test-project-2",
                    display_name="Test Project 2",
                    state=MagicMock(name="ACTIVE"),
                    parent="folders/12345",
                    create_time=datetime.utcnow(),
                    labels={"env": "prod"},
                ),
            ]
        )

        # Mock BigQuery client
        manager.bigquery = MagicMock()

        # Mock Asset client
        manager.assets = MagicMock()

        # Mock Storage client
        manager.storage = MagicMock()

        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_cost_data() -> Dict[str, Any]:
    """Mock cost data for testing."""
    return {
        "current_month": 12543.21,
        "previous_month": 11234.56,
        "trend": "+11.7%",
        "top_services": [
            {"service": "Compute Engine", "cost": 6200.00, "currency": "USD"},
            {"service": "Cloud Storage", "cost": 3100.00, "currency": "USD"},
            {"service": "BigQuery", "cost": 2000.00, "currency": "USD"},
            {"service": "Cloud SQL", "cost": 800.00, "currency": "USD"},
            {"service": "Networking", "cost": 443.21, "currency": "USD"},
        ],
        "forecast_end_of_month": 15000.00,
    }


@pytest.fixture
def mock_compliance_data() -> Dict[str, Any]:
    """Mock compliance data for testing."""
    return {
        "score": 99.1,
        "framework": "NIST 800-53",
        "controls_total": 325,
        "controls_compliant": 322,
        "controls_non_compliant": 3,
        "last_assessed": datetime.utcnow().isoformat(),
        "findings": [
            {
                "id": "AC-1",
                "name": "Access Control Policy",
                "status": "compliant",
                "severity": "high",
            },
            {"id": "AC-2", "name": "Account Management", "status": "compliant", "severity": "high"},
        ],
    }


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch("google.cloud.firestore.Client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


# ============================================================================
# Utility Functions
# ============================================================================


def create_mock_project(
    project_id: str = "test-project",
    name: str = "Test Project",
    state: str = "ACTIVE",
    labels: Dict[str, str] = None,
) -> Dict[str, Any]:
    """Create a mock project dictionary."""
    return {
        "id": f"projects/{project_id}",
        "project_id": project_id,
        "name": name,
        "number": "123456789",
        "state": state,
        "parent": {"type": "folder", "id": "12345"},
        "created_at": datetime.utcnow().isoformat(),
        "labels": labels or {},
    }


def create_mock_cost_breakdown(
    service: str = "Compute Engine", cost: float = 1000.0, days: int = 30
) -> Dict[str, Any]:
    """Create a mock cost breakdown."""
    return {
        "service": service,
        "cost": cost,
        "currency": "USD",
        "period_days": days,
        "usage": 720.0,
        "unit": "hours",
    }


# ============================================================================
# Async Test Helpers
# ============================================================================


class AsyncContextManager:
    """Helper for async context managers in tests."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


# Minimal 'mocker' fixture for environments without pytest-mock plugin
@pytest.fixture
def mocker():
    """Provide a simple mocker with a .patch() helper that is cleaned up after each test."""
    from unittest.mock import patch

    patches = []

    class Mocker:
        def patch(self, target, *args, **kwargs):
            # Support positional 'new' arg and keyword args like unittest.mock.patch
            if args:
                kwargs["new"] = args[0]
            p = patch(target, **kwargs)
            started = p.start()
            patches.append(p)
            return started

    m = Mocker()
    yield m

    for p in patches:
        try:
            p.stop()
        except Exception:
            pass
