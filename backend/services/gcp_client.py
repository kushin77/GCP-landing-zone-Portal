"""
GCP service clients for interacting with Google Cloud APIs.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.api_core import exceptions
from google.cloud import (
    asset_v1,
    bigquery,
    monitoring_v3,
    resourcemanager_v3,
    secretmanager,
    storage,
)

logger = logging.getLogger(__name__)


class GCPClientManager:
    """Manages GCP API clients with caching and error handling."""

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "landing-zone-hub")
        self._projects_client = None
        self._bigquery_client = None
        self._asset_client = None
        self._monitoring_client = None
        self._secrets_client = None
        self._storage_client = None

    @property
    def projects(self):
        """Resource Manager Projects client."""
        if not self._projects_client:
            self._projects_client = resourcemanager_v3.ProjectsClient()
        return self._projects_client

    @property
    def bigquery(self):
        """BigQuery client for cost analysis."""
        if not self._bigquery_client:
            self._bigquery_client = bigquery.Client(project=self.project_id)
        return self._bigquery_client

    @property
    def assets(self):
        """Cloud Asset Inventory client."""
        if not self._asset_client:
            self._asset_client = asset_v1.AssetServiceClient()
        return self._asset_client

    @property
    def monitoring(self):
        """Cloud Monitoring client."""
        if not self._monitoring_client:
            self._monitoring_client = monitoring_v3.MetricServiceClient()
        return self._monitoring_client

    @property
    def secrets(self):
        """Secret Manager client."""
        if not self._secrets_client:
            self._secrets_client = secretmanager.SecretManagerServiceClient()
        return self._secrets_client

    @property
    def storage(self):
        """Cloud Storage client."""
        if not self._storage_client:
            self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client


class ProjectService:
    """Service for GCP project operations."""

    def __init__(self, client_manager: GCPClientManager):
        self.client = client_manager.projects
        self.project_id = client_manager.project_id

    async def list_projects(
        self, parent: Optional[str] = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """List all accessible projects."""
        try:
            if parent:
                request = resourcemanager_v3.ListProjectsRequest(parent=parent, page_size=page_size)
            else:
                # List all projects accessible to the service account
                request = resourcemanager_v3.ListProjectsRequest(page_size=page_size)

            projects = []
            for project in self.client.list_projects(request=request):
                projects.append(
                    {
                        "id": project.name,
                        "project_id": project.project_id,
                        "name": project.display_name,
                        "number": project.name.split("/")[-1],
                        "state": project.state.name,
                        "parent": {
                            "type": project.parent.split("/")[0] if project.parent else None,
                            "id": project.parent.split("/")[-1] if project.parent else None,
                        },
                        "created_at": project.create_time,
                        "labels": dict(project.labels) if project.labels else {},
                    }
                )

            return projects
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error listing projects: {e}")
            return []

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details."""
        try:
            project = self.client.get_project(name=f"projects/{project_id}")

            return {
                "id": project.name,
                "project_id": project.project_id,
                "name": project.display_name,
                "number": project.name.split("/")[-1],
                "state": project.state.name,
                "created_at": project.create_time,
                "labels": dict(project.labels) if project.labels else {},
            }
        except exceptions.NotFound:
            logger.warning(f"Project not found: {project_id}")
            return None
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error getting project {project_id}: {e}")
            return None


class CostService:
    """Service for cost analysis using BigQuery."""

    def __init__(self, client_manager: GCPClientManager):
        self.client = client_manager.bigquery
        self.project_id = client_manager.project_id
        self.billing_dataset = os.getenv("BILLING_DATASET", "billing_export")

    async def get_current_month_costs(self) -> float:
        """Get total costs for current month."""
        query = f"""
            SELECT SUM(cost) as total_cost
            FROM `{self.project_id}.{self.billing_dataset}.gcp_billing_export_v1`
            WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
            AND cost > 0
        """

        try:
            result = self.client.query(query).result()
            row = next(iter(result), None)
            return float(row.total_cost) if row and row.total_cost else 0.0
        except Exception as e:
            logger.error(f"Error querying current month costs: {e}")
            return 0.0

    async def get_cost_breakdown(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get cost breakdown by service."""
        # Validate days parameter to prevent any injection
        if not isinstance(days, int) or days < 1 or days > 365:
            days = 30

        query = f"""
            SELECT
                service.description as service,
                SUM(cost) as total_cost,
                SUM(usage.amount) as total_usage,
                usage.unit
            FROM `{self.project_id}.{self.billing_dataset}.gcp_billing_export_v1`
            WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
            AND cost > 0
            GROUP BY service, usage.unit
            ORDER BY total_cost DESC
            LIMIT 10
        """

        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("days", "INT64", days)]
            )
            result = self.client.query(query, job_config=job_config).result()
            return [
                {
                    "service": row.service,
                    "cost": float(row.total_cost),
                    "currency": "USD",
                    "usage": float(row.total_usage) if row.total_usage else None,
                    "unit": row.unit,
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error querying cost breakdown: {e}")
            return []

    async def get_project_costs(self, project_id: str, days: int = 30) -> float:
        """Get costs for a specific project."""
        # Validate days parameter
        if not isinstance(days, int) or days < 1 or days > 365:
            days = 30

        query = f"""
            SELECT SUM(cost) as total_cost
            FROM `{self.project_id}.{self.billing_dataset}.gcp_billing_export_v1`
            WHERE project.id = @project_id
            AND DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
            AND cost > 0
        """

        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("project_id", "STRING", project_id),
                    bigquery.ScalarQueryParameter("days", "INT64", days),
                ]
            )
            result = self.client.query(query, job_config=job_config).result()
            row = next(iter(result), None)
            return float(row.total_cost) if row and row.total_cost else 0.0
        except Exception as e:
            logger.error(f"Error querying project costs for {project_id}: {e}")
            return 0.0

    async def get_cost_forecast(self) -> float:
        """Forecast end-of-month costs based on current trend."""
        query = f"""
            WITH daily_costs AS (
                SELECT
                    DATE(usage_start_time) as date,
                    SUM(cost) as daily_cost
                FROM `{self.project_id}.{self.billing_dataset}.gcp_billing_export_v1`
                WHERE DATE(usage_start_time) >= DATE_TRUNC(CURRENT_DATE(), MONTH)
                AND cost > 0
                GROUP BY date
            )
            SELECT AVG(daily_cost) as avg_daily_cost
            FROM daily_costs
        """

        try:
            result = self.client.query(query).result()
            row = next(iter(result), None)
            if row and row.avg_daily_cost:
                avg_daily = float(row.avg_daily_cost)
                days_in_month = 30  # Simplified
                return avg_daily * days_in_month
            return 0.0
        except Exception as e:
            logger.error(f"Error forecasting costs: {e}")
            return 0.0


class AssetService:
    """Service for Cloud Asset Inventory operations."""

    def __init__(self, client_manager: GCPClientManager):
        self.client = client_manager.assets
        self.project_id = client_manager.project_id

    async def search_resources(
        self, asset_types: List[str] = None, query: str = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for resources across the organization."""
        try:
            scope = f"projects/{self.project_id}"

            request = asset_v1.SearchAllResourcesRequest(
                scope=scope, asset_types=asset_types, query=query, page_size=page_size
            )

            resources = []
            for resource in self.client.search_all_resources(request=request):
                resources.append(
                    {
                        "name": resource.name,
                        "asset_type": resource.asset_type,
                        "project": resource.project,
                        "display_name": resource.display_name,
                        "description": resource.description,
                        "location": resource.location,
                        "labels": dict(resource.labels) if resource.labels else {},
                        "network_tags": list(resource.network_tags)
                        if resource.network_tags
                        else [],
                        "create_time": resource.create_time,
                        "update_time": resource.update_time,
                    }
                )

            return resources
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error searching resources: {e}")
            return []


class MonitoringService:
    """Service for Cloud Monitoring operations."""

    def __init__(self, client_manager: GCPClientManager):
        self.client = client_manager.monitoring
        self.project_id = client_manager.project_id

    async def get_metric(
        self, metric_type: str, resource_type: str = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get time series data for a metric."""
        try:
            project_name = f"projects/{self.project_id}"

            now = datetime.utcnow()
            interval = monitoring_v3.TimeInterval(
                {"end_time": now, "start_time": now - timedelta(hours=hours)}
            )

            request = monitoring_v3.ListTimeSeriesRequest(
                {
                    "name": project_name,
                    "filter": f'metric.type = "{metric_type}"',
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )

            results = []
            for series in self.client.list_time_series(request=request):
                data_points = [
                    {
                        "timestamp": point.interval.end_time,
                        "value": point.value.double_value or point.value.int64_value,
                    }
                    for point in series.points
                ]

                results.append(
                    {
                        "metric": series.metric.type,
                        "resource": series.resource.type,
                        "labels": dict(series.metric.labels),
                        "data_points": data_points,
                    }
                )

            return results
        except exceptions.GoogleAPIError as e:
            logger.error(f"Error getting metrics: {e}")
            return []


# Global client manager instance
gcp_clients = GCPClientManager()
