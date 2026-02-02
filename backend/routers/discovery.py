"""Discovery prototype service.

Provides a lightweight, mockable discovery API to enumerate endpoints and services.
This is intentionally small and testable; real GCP API calls will be added later.
"""
from typing import List

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


class EndpointModel(dict):
    """Simple dict-like endpoint model for prototyping."""


@router.get("/endpoints", response_model=List[dict])
async def list_endpoints():
    """Return a small set of mocked discovered endpoints.

    Replace this with actual `gcp_clients` and git parsing logic in later iterations.
    """
    # Mocked sample data to drive frontend integration and tests
    sample = [
        {
            "id": "projects/alpha/services/app-frontend",
            "name": "app-frontend",
            "type": "gke-service",
            "owner": "team-frontend",
            "public_dns": "portal-alpha.example.com",
            "created_at": "2026-01-01T12:00:00Z",
        },
        {
            "id": "projects/alpha/storage/bucket-logs",
            "name": "bucket-logs",
            "type": "gcs-bucket",
            "owner": "team-ops",
            "public_dns": None,
            "created_at": "2025-11-03T08:12:00Z",
        },
    ]

    return sample
