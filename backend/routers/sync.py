import logging

from fastapi import APIRouter, HTTPException

# Late import to avoid circular dependency or use dependency injection
# For now we'll assumesync_service is set up in app state or as a global

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])
logger = logging.getLogger(__name__)

# We will need a way to get the sync_service instance.
# Best practice is to use dependency injection.
# For now, following the existing pattern in the codebase.


@router.get("/infrastructure-state")
async def get_infrastructure_state():
    """Get latest synced infrastructure state."""
    from services.lz_sync_service import lz_sync_service

    try:
        state = await lz_sync_service.sync_infrastructure_state()
        return state.to_dict()
    except Exception as e:
        logger.error(f"Failed to get infrastructure state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_sync_status():
    """Get summary of sync statuses across all layers."""
    from services.lz_sync_service import lz_sync_service

    return lz_sync_service.get_all_sync_status()
