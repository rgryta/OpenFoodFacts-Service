"""
Admin endpoints for service management
"""
import logging
from fastapi import APIRouter, Depends, Security

from ..models import SyncTriggerResponse
from ..middleware.auth import api_key_dependency, api_key_header, verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.post("/sync/trigger", response_model=SyncTriggerResponse)
async def trigger_manual_sync(api_key: str = Security(api_key_header)):
    """
    Trigger a manual delta sync.
    Requires API key authentication.

    Note: In the current implementation, this is a placeholder.
    Actual sync is handled by the updater container with cron.
    Future enhancement: Implement IPC to trigger updater script.
    """
    # Validate API key
    await verify_api_key(api_key)

    logger.info("Manual sync trigger requested")

    # Sync is handled by the updater container on a cron schedule (see updater/crontab).
    # This endpoint acknowledges the request. Manual IPC is not implemented because the
    # updater runs as a separate container with its own cron lifecycle.

    return SyncTriggerResponse(
        status="accepted",
        message="Manual sync scheduled for next updater cycle. Check updater logs for progress."
    )
