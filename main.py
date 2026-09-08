"""
main.py

Entry point for the Warehouse Management System API.

This module handles:
- FastAPI application configuration
- Application startup and shutdown
- PostgreSQL schema initialization
- PostgreSQL and Redis health checks
- Logging configuration
- Inventory and order route registration
- API health endpoints
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import (
    check_database_connection,
    close_database_pool,
)
from inventory import router as inventory_router
from models import initialize_database
from orders import router as orders_router
from redis_client import (
    check_redis_connection,
    close_redis_connection,
)


# -------------------------------------------------------------------
# Logging Configuration
# -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Application Lifecycle
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    Startup:
    - Verify PostgreSQL connectivity
    - Initialize the PostgreSQL schema
    - Check Redis availability
    - Log service status

    Shutdown:
    - Close PostgreSQL connections
    - Close Redis connections
    """

    logger.info(
        "Starting Warehouse Management System API."
    )

    try:
        check_database_connection()

        logger.info(
            "PostgreSQL connection verified."
        )

        initialize_database()

        logger.info(
            "PostgreSQL schema initialized."
        )

    except Exception:
        logger.exception(
            "PostgreSQL startup initialization failed."
        )

        raise

    redis_available = check_redis_connection()

    if redis_available:
        logger.info(
            "Redis caching is available."
        )

    else:
        logger.warning(
            "Redis is unavailable. "
            "The API will continue using PostgreSQL."
        )

    logger.info(
        "Warehouse Management System API started successfully."
    )

    try:
        yield

    finally:
        logger.info(
            "Shutting down Warehouse Management System API."
        )

        close_database_pool()
        close_redis_connection()

        logger.info(
            "Warehouse Management System API shutdown complete."
        )


# -------------------------------------------------------------------
# FastAPI Application
# -------------------------------------------------------------------

app = FastAPI(
    title="Warehouse Management System API",
    description=(
        "REST API for warehouse inventory management, "
        "inventory caching, low-stock monitoring, "
        "and transaction-safe order processing."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# -------------------------------------------------------------------
# Register API Routes
# -------------------------------------------------------------------

app.include_router(
    inventory_router,
    prefix="/inventory",
    tags=["Inventory"],
)

app.include_router(
    orders_router,
    prefix="/orders",
    tags=["Orders"],
)


# -------------------------------------------------------------------
# Root Endpoint
# -------------------------------------------------------------------

@app.get(
    "/",
    tags=["System"],
)
def root():
    """
    Return basic API information.
    """

    return {
        "name": "Warehouse Management System API",
        "version": "2.0.0",
        "status": "online",
        "documentation": "/docs",
    }


# -------------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------------

@app.get(
    "/health",
    tags=["System"],
)
def health_check():
    """
    Return application dependency status.

    PostgreSQL is required for the application to operate.
    Redis is optional because inventory requests can fall back
    to PostgreSQL when the cache is unavailable.
    """

    database_status = "healthy"
    redis_status = "healthy"

    try:
        check_database_connection()

    except Exception:
        database_status = "unhealthy"

    if not check_redis_connection():
        redis_status = "unavailable"

    overall_status = (
        "healthy"
        if database_status == "healthy"
        else "unhealthy"
    )

    return {
        "status": overall_status,
        "services": {
            "postgresql": database_status,
            "redis": redis_status,
        },
    }
