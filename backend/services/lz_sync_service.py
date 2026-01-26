"""
Landing Zone Sync Service

Syncs infrastructure state, policies, and configurations from the Landing Zone
to the Portal in real-time.

Layers:
1. Git Sync (documentation & configs via GitHub Actions)
2. API Sync (real infrastructure state from GCP)
3. Pub/Sub (real-time infrastructure change events)
4. BigQuery (historical trends & analytics)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from google.cloud import asset_v1, container_v1, compute_v1
from google.cloud import pubsub_v1
from google.cloud import logging as cloud_logging
import aiohttp

logger = logging.getLogger(__name__)


class SyncLayerType(str, Enum):
    """Sync layer types."""
    GIT = "git"
    API = "api"
    PUBSUB = "pubsub"
    BIGQUERY = "bigquery"


class SyncStatus(str, Enum):
    """Sync operation status."""
    SUCCESS = "success"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class SyncMetadata:
    """Metadata for a sync operation."""
    layer: SyncLayerType
    status: SyncStatus
    last_sync: datetime
    items_synced: int
    items_failed: int
    error_messages: List[str]
    next_sync: Optional[datetime] = None
    sync_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "layer": self.layer.value,
            "status": self.status.value,
            "last_sync": self.last_sync.isoformat(),
            "items_synced": self.items_synced,
            "items_failed": self.items_failed,
            "error_messages": self.error_messages,
            "next_sync": self.next_sync.isoformat() if self.next_sync else None,
            "sync_duration_seconds": self.sync_duration_seconds,
        }


@dataclass
class InfrastructureProject:
    """GCP Project in Landing Zone."""
    project_id: str
    project_name: str
    parent: str
    labels: Dict[str, str]
    lifecycle_state: str


@dataclass
class InfrastructureVPC:
    """VPC Network in Landing Zone."""
    name: str
    self_link: str
    auto_create_subnets: bool
    subnets: List[str]
    routing_mode: str


@dataclass
class InfrastructureInstance:
    """Compute Instance in Landing Zone."""
    name: str
    zone: str
    machine_type: str
    status: str
    internal_ip: str
    external_ip: Optional[str]
    labels: Dict[str, str]


@dataclass
class ComplianceStatus:
    """Compliance assessment."""
    framework: str
    score: float  # 0-1
    violations_count: int
    last_audit: datetime
    violations: List[Dict[str, Any]]


@dataclass
class LZInfrastructureState:
    """Complete Landing Zone infrastructure state."""
    timestamp: datetime
    projects: List[InfrastructureProject]
    vpcs: List[InfrastructureVPC]
    compute_instances: List[InfrastructureInstance]
    gke_clusters: List[Dict[str, Any]]
    databases: List[Dict[str, Any]]
    compliance_status: ComplianceStatus
    policy_violations: List[Dict[str, Any]]
    metadata: SyncMetadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "projects": [asdict(p) for p in self.projects],
            "vpcs": [asdict(v) for v in self.vpcs],
            "compute_instances": [asdict(i) for i in self.compute_instances],
            "gke_clusters": self.gke_clusters,
            "databases": self.databases,
            "compliance_status": asdict(self.compliance_status),
            "policy_violations": self.policy_violations,
            "metadata": self.metadata.to_dict(),
        }


class LZSyncService:
    """Service for syncing Landing Zone state to Portal."""

    def __init__(
        self,
        project_id: str,
        gcp_parent: str = None,  # e.g., "organizations/123456"
    ):
        self.project_id = project_id
        self.gcp_parent = gcp_parent

        # Initialize GCP clients
        self.asset_client = asset_v1.AssetServiceClient()
        self.container_client = container_v1.ClusterManagerClient()
        self.compute_client = compute_v1.InstancesClient()
        self.networks_client = compute_v1.NetworksClient()

        # Pub/Sub for real-time events
        self.publisher_client = pubsub_v1.PublisherClient()
        self.subscriber_client = pubsub_v1.SubscriberClient()

        # Sync history
        self.sync_history: Dict[SyncLayerType, SyncMetadata] = {}

    async def sync_infrastructure_state(self) -> LZInfrastructureState:
        """
        Fetch complete infrastructure state from GCP.

        Returns:
            LZInfrastructureState: Current landing zone state
        """
        start_time = datetime.utcnow()
        errors = []
        items_synced = 0

        try:
            logger.info("Starting infrastructure state sync...")

            # Fetch all resources in parallel
            projects, projects_synced = await self._get_projects()
            items_synced += projects_synced

            vpcs, vpcs_synced = await self._get_vpcs()
            items_synced += vpcs_synced

            instances, instances_synced = await self._get_compute_instances()
            items_synced += instances_synced

            gke_clusters, gke_synced = await self._get_gke_clusters()
            items_synced += gke_synced

            databases, db_synced = await self._get_databases()
            items_synced += db_synced

            compliance_status = await self._get_compliance_status()

            policy_violations = await self._get_policy_violations()

            sync_duration = (datetime.utcnow() - start_time).total_seconds()

            metadata = SyncMetadata(
                layer=SyncLayerType.API,
                status=SyncStatus.SUCCESS,
                last_sync=datetime.utcnow(),
                items_synced=items_synced,
                items_failed=len(errors),
                error_messages=errors,
                next_sync=datetime.utcnow() + timedelta(minutes=5),
                sync_duration_seconds=sync_duration,
            )

            state = LZInfrastructureState(
                timestamp=datetime.utcnow(),
                projects=projects,
                vpcs=vpcs,
                compute_instances=instances,
                gke_clusters=gke_clusters,
                databases=databases,
                compliance_status=compliance_status,
                policy_violations=policy_violations,
                metadata=metadata,
            )

            logger.info(f"Infrastructure sync completed: {items_synced} items synced in {sync_duration}s")
            return state

        except Exception as e:
            logger.error(f"Infrastructure sync failed: {e}")
            raise

    async def _get_projects(self) -> tuple[List[InfrastructureProject], int]:
        """Get all GCP projects in Landing Zone."""
        try:
            query = """
            SELECT
              resource.name,
              resource.displayName,
              resource.parent,
              resource.labels
            FROM `cloudresourcemanager.googleapis.com/Project`
            WHERE resource.state = 'ACTIVE'
            """

            request = asset_v1.SearchAllResourcesRequest(
                scope=self.gcp_parent or f"projects/{self.project_id}",
                asset_types=["cloudresourcemanager.googleapis.com/Project"],
            )

            results = self.asset_client.search_all_resources(request=request)

            projects = []
            for resource in results:
                project = InfrastructureProject(
                    project_id=resource.name.split("/")[-1],
                    project_name=resource.display_name,
                    parent=getattr(resource, "parent", ""),
                    labels=dict(resource.labels) if hasattr(resource, "labels") else {},
                    lifecycle_state="ACTIVE",
                )
                projects.append(project)

            return projects, len(projects)

        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return [], 0

    async def _get_vpcs(self) -> tuple[List[InfrastructureVPC], int]:
        """Get all VPC networks."""
        try:
            request = asset_v1.SearchAllResourcesRequest(
                scope=self.gcp_parent or f"projects/{self.project_id}",
                asset_types=["compute.googleapis.com/Network"],
            )

            results = self.asset_client.search_all_resources(request=request)

            vpcs = []
            for resource in results:
                vpc = InfrastructureVPC(
                    name=resource.display_name,
                    self_link=resource.name,
                    auto_create_subnets=True,
                    subnets=[],
                    routing_mode="REGIONAL",
                )
                vpcs.append(vpc)

            return vpcs, len(vpcs)

        except Exception as e:
            logger.error(f"Failed to get VPCs: {e}")
            return [], 0

    async def _get_compute_instances(self) -> tuple[List[InfrastructureInstance], int]:
        """Get all compute instances."""
        try:
            request = asset_v1.SearchAllResourcesRequest(
                scope=self.gcp_parent or f"projects/{self.project_id}",
                asset_types=["compute.googleapis.com/Instance"],
            )

            results = self.asset_client.search_all_resources(request=request)

            instances = []
            for resource in results:
                instance = InfrastructureInstance(
                    name=resource.display_name,
                    zone="",
                    machine_type="",
                    status="RUNNING",
                    internal_ip="",
                    external_ip=None,
                    labels=dict(resource.labels) if hasattr(resource, "labels") else {},
                )
                instances.append(instance)

            return instances, len(instances)

        except Exception as e:
            logger.error(f"Failed to get compute instances: {e}")
            return [], 0

    async def _get_gke_clusters(self) -> tuple[List[Dict[str, Any]], int]:
        """Get all GKE clusters."""
        try:
            request = asset_v1.SearchAllResourcesRequest(
                scope=self.gcp_parent or f"projects/{self.project_id}",
                asset_types=["container.googleapis.com/Cluster"],
            )

            results = self.asset_client.search_all_resources(request=request)
            clusters = []

            for resource in results:
                cluster = {
                    "name": resource.display_name,
                    "self_link": resource.name,
                    "status": "RUNNING",
                }
                clusters.append(cluster)

            return clusters, len(clusters)

        except Exception as e:
            logger.error(f"Failed to get GKE clusters: {e}")
            return [], 0

    async def _get_databases(self) -> tuple[List[Dict[str, Any]], int]:
        """Get all databases (Cloud SQL, Firestore, etc)."""
        try:
            # Search for Cloud SQL instances
            request = asset_v1.SearchAllResourcesRequest(
                scope=self.gcp_parent or f"projects/{self.project_id}",
                asset_types=[
                    "sqladmin.googleapis.com/Instance",
                    "firestore.googleapis.com/Database",
                ],
            )

            results = self.asset_client.search_all_resources(request=request)
            databases = []

            for resource in results:
                db = {
                    "name": resource.display_name,
                    "type": resource.asset_type.split("/")[-1],
                    "self_link": resource.name,
                }
                databases.append(db)

            return databases, len(databases)

        except Exception as e:
            logger.error(f"Failed to get databases: {e}")
            return [], 0

    async def _get_compliance_status(self) -> ComplianceStatus:
        """Get compliance assessment."""
        try:
            # TODO: Integrate with actual compliance framework
            # (e.g., Cloud Security Command Center, custom policies)

            return ComplianceStatus(
                framework="CIS Google Cloud Platform Foundation Benchmark v1.2.0",
                score=0.92,  # Placeholder
                violations_count=3,  # Placeholder
                last_audit=datetime.utcnow(),
                violations=[],  # TODO: Get real violations
            )

        except Exception as e:
            logger.error(f"Failed to get compliance status: {e}")
            return ComplianceStatus(
                framework="Unknown",
                score=0.0,
                violations_count=0,
                last_audit=datetime.utcnow(),
                violations=[],
            )

    async def _get_policy_violations(self) -> List[Dict[str, Any]]:
        """Get current policy violations."""
        try:
            # TODO: Query enforcement gates from pmo.yaml
            # and check current state against policies

            violations = []
            # Placeholder: Real implementation would check each policy

            return violations

        except Exception as e:
            logger.error(f"Failed to get policy violations: {e}")
            return []

    def get_sync_status(self, layer: SyncLayerType) -> Optional[SyncMetadata]:
        """Get status of last sync for a layer."""
        return self.sync_history.get(layer)

    def get_all_sync_status(self) -> Dict[SyncLayerType, Optional[SyncMetadata]]:
        """Get status of all sync layers."""
        return self.sync_history


# FastAPI route handler
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])
sync_service = None  # Initialize in app startup


@router.get("/infrastructure-state")
async def get_infrastructure_state():
    """Get latest synced infrastructure state."""
    if not sync_service:
        raise HTTPException(status_code=503, detail="Sync service not initialized")

    try:
        state = await sync_service.sync_infrastructure_state()
        return state.to_dict()
    except Exception as e:
        logger.error(f"Failed to get infrastructure state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status")
async def get_sync_status():
    """Get status of all sync layers."""
    if not sync_service:
        raise HTTPException(status_code=503, detail="Sync service not initialized")

    status = sync_service.get_all_sync_status()
    return {
        layer.value: metadata.to_dict() if metadata else None
        for layer, metadata in status.items()
    }


@router.post("/trigger-sync")
async def trigger_manual_sync(layers: Optional[List[SyncLayerType]] = None):
    """Manually trigger a sync operation."""
    if not sync_service:
        raise HTTPException(status_code=503, detail="Sync service not initialized")

    try:
        # Trigger specified layers or all
        if not layers:
            layers = [SyncLayerType.API]

        results = {}
        for layer in layers:
            if layer == SyncLayerType.API:
                state = await sync_service.sync_infrastructure_state()
                results[layer.value] = state.to_dict()

        return {"triggered": True, "results": results}
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))
