"""
redis_client.py

Redis caching layer for the Warehouse Management System.

This module handles:
- Connecting to Redis
- Checking Redis availability
- Reading cached inventory
- Saving inventory with a configurable TTL
- Invalidating individual inventory records
- Safely clearing inventory cache entries

Redis reduces PostgreSQL queries by caching frequently accessed
inventory records.
"""

import json
import logging
import os

import redis
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL = int(
    os.getenv("REDIS_CACHE_TTL", "300")
)


# -------------------------------------------------------------------
# Redis Client
# -------------------------------------------------------------------

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0")),
    password=os.getenv("REDIS_PASSWORD") or None,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


# -------------------------------------------------------------------
# Redis Connection
# -------------------------------------------------------------------

def check_redis_connection():
    """
    Verify that Redis is reachable.

    Returns True when Redis responds successfully and False when
    Redis is unavailable.
    """

    try:
        redis_client.ping()

        logger.info("Redis connection successful.")

        return True

    except redis.RedisError:
        logger.warning("Redis connection unavailable.")

        return False


def close_redis_connection():
    """
    Close the Redis client's connection pool.

    Intended to be called when the FastAPI application shuts down.
    """

    redis_client.close()

    logger.info("Redis connection closed.")


# -------------------------------------------------------------------
# Cache Key Helpers
# -------------------------------------------------------------------

def inventory_cache_key(sku: str):
    """
    Create a consistent Redis key for an inventory record.
    """

    return f"inventory:{sku.strip()}"


# -------------------------------------------------------------------
# Inventory Cache Operations
# -------------------------------------------------------------------

def get_inventory_cache(sku: str):
    """
    Retrieve an inventory record from Redis.

    Returns the decoded inventory dictionary when the cache contains
    the SKU, otherwise returns None.
    """

    key = inventory_cache_key(sku)

    data = redis_client.get(key)

    if data is None:
        return None

    try:
        return json.loads(data)

    except json.JSONDecodeError:
        logger.warning(
            "Invalid cached inventory data for SKU %s. "
            "Removing corrupted cache entry.",
            sku,
        )

        redis_client.delete(key)

        return None


def save_inventory_cache(
    sku: str,
    inventory: dict,
    ttl: int = DEFAULT_CACHE_TTL,
):
    """
    Cache an inventory record for the configured number of seconds.
    """

    key = inventory_cache_key(sku)

    redis_client.setex(
        key,
        ttl,
        json.dumps(
            inventory,
            default=str,
        ),
    )


def delete_inventory_cache(sku: str):
    """
    Remove one inventory record from Redis.

    Used after inventory-changing operations to prevent stale data
    from being returned.
    """

    key = inventory_cache_key(sku)

    redis_client.delete(key)


def cache_exists(sku: str):
    """
    Check whether an inventory record currently exists in Redis.
    """

    key = inventory_cache_key(sku)

    return bool(
        redis_client.exists(key)
    )


def clear_inventory_cache():
    """
    Remove all inventory cache entries.

    SCAN is used instead of KEYS so Redis does not perform a
    blocking scan of the entire keyspace.
    """

    deleted_count = 0

    for key in redis_client.scan_iter(
        match="inventory:*",
        count=100,
    ):
        redis_client.delete(key)

        deleted_count += 1

    logger.info(
        "Cleared %s inventory cache entries.",
        deleted_count,
    )

    return deleted_count
