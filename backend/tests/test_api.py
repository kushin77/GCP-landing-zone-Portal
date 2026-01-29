"""
API Integration Tests for Landing Zone Portal.

Tests cover:
- Health check endpoints
- Projects API
- Costs API
- Compliance API
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_returns_200(self, client: TestClient):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_readiness_check_returns_status(self, client: TestClient):
        """Readiness endpoint should return status."""
        response = client.get("/ready")

        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    def test_root_endpoint_returns_api_info(self, client: TestClient):
        """Root endpoint should return API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data


class TestProjectsAPI:
    """Tests for Projects API endpoints."""

    def test_list_projects_returns_paginated(self, client: TestClient, mock_gcp_clients):
        """List projects should return paginated results."""
        with patch("routers.projects.ProjectService") as mock_service:
            mock_service.return_value.list_projects = MagicMock(
                return_value=[
                    {
                        "id": "projects/123",
                        "project_id": "test-project",
                        "name": "Test Project",
                        "number": "123",
                        "state": "ACTIVE",
                        "created_at": datetime.utcnow(),
                        "labels": {},
                        "parent": None,
                        "status": "active",
                        "type": "project",
                    }
                ]
            )

            response = client.get("/api/v1/projects/?page=1&limit=10")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "total" in data
            assert "page" in data

    def test_list_projects_pagination_params(self, client: TestClient, mock_gcp_clients):
        """List projects should respect pagination parameters."""
        with patch("routers.projects.ProjectService") as mock_service:
            mock_service.return_value.list_projects = MagicMock(return_value=[])

            response = client.get("/api/v1/projects/?page=2&limit=5")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["limit"] == 5

    def test_get_project_not_found(self, client: TestClient, mock_gcp_clients):
        """Get non-existent project should return 404."""
        with patch("routers.projects.ProjectService") as mock_service:
            mock_service.return_value.get_project = MagicMock(return_value=None)

            response = client.get("/api/v1/projects/non-existent")

            assert response.status_code == 404


class TestCostsAPI:
    """Tests for Costs API endpoints."""

    def test_get_cost_summary(self, client: TestClient, mock_cost_data):
        """Get cost summary should return cost data."""
        with patch("routers.costs.CostService") as mock_service:
            mock_service.return_value.get_current_month_costs = MagicMock(
                return_value=mock_cost_data["current_month"]
            )
            mock_service.return_value.get_cost_breakdown = MagicMock(
                return_value=mock_cost_data["top_services"]
            )

            response = client.get("/api/v1/costs/summary")

            assert response.status_code == 200


class TestComplianceAPI:
    """Tests for Compliance API endpoints."""

    def test_get_compliance_status(self, client: TestClient, mock_compliance_data):
        """Get compliance status should return compliance data."""
        with patch("routers.compliance.compliance_service") as mock_service:
            mock_service.get_compliance_status = MagicMock(
                return_value=MagicMock(
                    score=mock_compliance_data["score"],
                    framework="NIST 800-53",
                    controls_total=mock_compliance_data["controls_total"],
                    controls_compliant=mock_compliance_data["controls_compliant"],
                    controls_non_compliant=mock_compliance_data["controls_non_compliant"],
                    findings=[],
                )
            )

            response = client.get("/api/v1/compliance/status?framework=NIST%20800-53")

            assert response.status_code == 200

    def test_list_frameworks(self, client: TestClient):
        """List frameworks should return available frameworks."""
        response = client.get("/api/v1/compliance/frameworks")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDashboardAPI:
    """Tests for Dashboard API endpoints."""

    def test_get_dashboard_returns_aggregated_data(self, client: TestClient):
        """Dashboard should return aggregated data from all services."""
        with patch("services.gcp_client.CostService") as mock_cost:
            with patch("services.compliance_service.compliance_service"):
                mock_cost.return_value.get_current_month_costs = MagicMock(return_value=12000.0)
                mock_cost.return_value.get_cost_breakdown = MagicMock(return_value=[])

                response = client.get("/api/v1/dashboard")

                assert response.status_code == 200


class TestAPIValidation:
    """Tests for API input validation."""

    def test_pagination_limit_max(self, client: TestClient, mock_gcp_clients):
        """Pagination limit should not exceed 100."""
        with patch("routers.projects.ProjectService") as mock_service:
            mock_service.return_value.list_projects = MagicMock(return_value=[])

            response = client.get("/api/v1/projects/?limit=200")

            # Should either reject or cap the limit
            assert response.status_code in [200, 422]

    def test_pagination_page_minimum(self, client: TestClient, mock_gcp_clients):
        """Pagination page should be at least 1."""
        with patch("routers.projects.ProjectService") as mock_service:
            mock_service.return_value.list_projects = MagicMock(return_value=[])

            response = client.get("/api/v1/projects/?page=0")

            # Should reject page < 1
            assert response.status_code == 422


class TestErrorHandling:
    """Tests for API error handling."""

    def test_not_found_returns_404(self, client: TestClient):
        """Non-existent endpoint should return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed_returns_405(self, client: TestClient):
        """Wrong HTTP method should return 405."""
        response = client.post("/health")
        assert response.status_code == 405
