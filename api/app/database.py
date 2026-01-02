"""
Database connection pool management using asyncpg
"""
import logging
from typing import Optional
import asyncpg

from .config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        logger.info("Creating database connection pool...")
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("Database connection pool created")
    return _pool


async def close_pool():
    """Close the database connection pool"""
    global _pool
    if _pool is not None:
        logger.info("Closing database connection pool...")
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def get_connection() -> asyncpg.Connection:
    """
    Get a database connection from the pool.
    This is a dependency for route handlers.
    """
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection
