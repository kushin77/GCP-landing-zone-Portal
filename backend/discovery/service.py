"""Discovery prototype service.

Provides a lightweight, mockable discovery API to enumerate endpoints and services.
This is intentionally small and testable; real GCP API calls will be added later.
"""
import os
from typing import List

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


class EndpointModel(dict):
    """Simple dict-like endpoint model for prototyping."""


def discover_endpoints_from_git_rca_workspace() -> List[dict]:
    """Discover endpoints from the git-rca-workspace submodule."""
    endpoints = []
    workspace_path = os.path.join(os.path.dirname(__file__), "..", "..", "git-rca-workspace")
    services_path = os.path.join(workspace_path, "src", "services")
    
    if os.path.exists(services_path):
        for filename in os.listdir(services_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                service_name = filename[:-3]  # remove .py
                endpoints.append({
                    "id": f"services/platform/{service_name}",
                    "name": service_name,
                    "type": "python-service",
                    "owner": "platform-team",
                    "public_dns": None,  # No public DNS for internal services
                    "created_at": "2026-01-30T00:00:00Z",  # Placeholder
                    "source": "git"
                })
    
    return endpoints


@router.get("/endpoints", response_model=List[dict])
async def list_endpoints():
    """Return discovered endpoints from git-rca-workspace and GCP.

    Uses actual parsing logic for git-rca-workspace.
    """
    # Discover from git-rca-workspace
    git_endpoints = discover_endpoints_from_git_rca_workspace()
    
    # TODO: Add GCP API discovery here
    
    # For now, include some sample GCP endpoints
    gcp_endpoints = [
        {
            "id": "projects/alpha/storage/bucket-logs",
            "name": "bucket-logs",
            "type": "gcs-bucket",
            "owner": "team-ops",
            "public_dns": None,
            "created_at": "2025-11-03T08:12:00Z",
            "source": "gcp"
        },
    ]
    
    return git_endpoints + gcp_endpoints
