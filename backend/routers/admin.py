"""
Admin API router - protected endpoints for platform admins.
"""
from fastapi import APIRouter, Depends
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(get_current_user)])


@router.get("/settings")
async def get_admin_settings():
    """Return platform admin settings (protected)."""
    return {
        "settings": {
            "enforcement": True,
            "telemetry_enabled": False,
        }
    }
