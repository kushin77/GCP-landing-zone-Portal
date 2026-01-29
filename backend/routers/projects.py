"""
Projects API router.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from models.schemas import Project, ResourceListResponse
from services.gcp_client import ProjectService, gcp_clients

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_project_service():
    """Dependency to get project service."""
    return ProjectService(gcp_clients)


@router.get("/", response_model=ResourceListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    parent: Optional[str] = None,
    service: ProjectService = Depends(get_project_service),
):
    """List all accessible GCP projects."""
    projects = await service.list_projects(parent=parent, page_size=limit)

    # Apply pagination
    start = (page - 1) * limit
    end = start + limit
    paginated = projects[start:end]

    return {
        "data": paginated,
        "total": len(projects),
        "page": page,
        "limit": limit,
        "pages": (len(projects) + limit - 1) // limit,
    }


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Get project details."""
    project = await service.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return project


@router.get("/{project_id}/resources")
async def get_project_resources(
    project_id: str,
    resource_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    """Get resources in a project."""
    # This would integrate with Cloud Asset Inventory
    return {"data": [], "total": 0, "page": page, "limit": limit}


@router.get("/{project_id}/costs")
async def get_project_costs(project_id: str, days: int = Query(30, ge=1, le=365)):
    """Get cost information for a project."""
    from services.gcp_client import CostService

    cost_service = CostService(gcp_clients)
    total_cost = await cost_service.get_project_costs(project_id, days)

    return {
        "project_id": project_id,
        "period_days": days,
        "total_cost": total_cost,
        "currency": "USD",
    }
