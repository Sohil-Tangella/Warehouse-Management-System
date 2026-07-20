"""
redis_client.py

Connects the Warehouse Management System to Redis.

This file handles:
- Connecting to Redis
- Reading cached inventory
- Saving inventory to the cache
- Removing cached inventory

Redis is used to reduce database queries by temporarily storing
frequently accessed inventory data.
"""

import os
import json
import redis

from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)


def get_inventory_cache(sku: str):
    key = f"inventory:{sku}"

    data = redis_client.get(key)

    if data:
        return json.loads(data)

    return None


def save_inventory_cache(
    sku: str,
    inventory: dict
):
    key = f"inventory:{sku}"

    redis_client.setex(
        key,
        300,
        json.dumps(inventory)
    )


def delete_inventory_cache(sku: str):
    key = f"inventory:{sku}"

    redis_client.delete(key)


def cache_exists(sku: str):
    key = f"inventory:{sku}"

    return redis_client.exists(key)


def clear_inventory_cache():
    keys = redis_client.keys("inventory:*")

    if keys:
        redis_client.delete(*keys)