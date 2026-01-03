"""
OpenFoodFacts API Service
FastAPI application entry point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import get_pool, close_pool
from .routers import health, search, admin

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Manages database connection pool lifecycle.
    """
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.version}")
    logger.info(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'N/A'}")
    logger.info(f"API Keys configured: {len(settings.api_keys_list)}")

    # Initialize database pool
    await get_pool()

    yield

    # Shutdown
    logger.info("Shutting down service...")
    await close_pool()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    description="Self-hosted OpenFoodFacts product search service with PostgreSQL backend",
    version=settings.version,
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

# CORS middleware (adjust origins as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(search.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs"""
    return {
        "service": settings.service_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health"
    }
