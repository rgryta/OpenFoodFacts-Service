"""
Health check endpoint
"""
import logging
from fastapi import APIRouter, Depends
import asyncpg

from ..models import HealthResponse
from ..database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns service status, database connection, and product count.
    No authentication required.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Test database connection and get product count
            count = await conn.fetchval("SELECT COUNT(*) FROM products")

            # Get last update timestamp
            last_update = await conn.fetchval(
                "SELECT MAX(updated_at) FROM products"
            )

            return HealthResponse(
                status="healthy",
                database="connected",
                product_count=count,
                last_update=str(last_update) if last_update else None
            )
    except Exception as e:
        logger.exception("Health check failed")
        return HealthResponse(
            status="unhealthy",
            database="disconnected",
            product_count=0,
            last_update=None
        )
