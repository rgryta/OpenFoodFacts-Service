"""
API Key authentication middleware
"""
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from typing import List

from ..config import settings

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = None) -> bool:
    """
    Verify API key against configured keys.
    Returns True if valid, raises HTTPException if invalid.
    """
    # Get allowed API keys
    allowed_keys: List[str] = settings.api_keys_list

    # Fail closed: no keys configured means service is misconfigured
    if not allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service misconfigured: no API keys set",
        )

    # Check if provided key is valid
    if not api_key or api_key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


async def api_key_dependency(request: Request):
    """
    FastAPI dependency for API key validation.
    Can be used as a dependency in protected routes.
    """
    api_key = request.headers.get("X-API-Key")
    await verify_api_key(api_key)
    return api_key
