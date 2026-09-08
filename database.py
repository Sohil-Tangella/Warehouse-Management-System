"""
database.py

PostgreSQL data-access layer for the Warehouse Management System.

This module handles:
- PostgreSQL connection pooling
- Reading and receiving inventory
- Looking up individual inventory records
- Searching products
- Finding low-stock products
- Creating store orders
- Viewing existing orders
- Transaction-safe inventory updates
- Redis cache integration and invalidation
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from redis_client import (
    delete_inventory_cache,
    get_inventory_cache,
    save_inventory_cache,
)

load_dotenv()

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 25
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


# -------------------------------------------------------------------
# PostgreSQL Connection Pool
# -------------------------------------------------------------------

database_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("DB_NAME", "warehouse"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
)


def get_connection():
    """
    Retrieve a PostgreSQL connection from the connection pool.
    """

    try:
        return database_pool.getconn()

    except Exception as error:
        logger.exception("Unable to retrieve database connection.")

        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable.",
        ) from error


def release_connection(connection):
    """
    Return a PostgreSQL connection to the connection pool.
    """

    if connection is not None:
        database_pool.putconn(connection)


def close_database_pool():
    """
    Close all PostgreSQL connections.

    Intended to be called when the FastAPI application shuts down.
    """

    database_pool.closeall()

    logger.info("PostgreSQL connection pool closed.")


def check_database_connection():
    """
    Verify that PostgreSQL is reachable.
    """

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")

        logger.info("PostgreSQL connection successful.")

        return True

    finally:
        release_connection(connection)


# -------------------------------------------------------------------
# Redis Helpers
# -------------------------------------------------------------------

def safely_get_cached_inventory(sku: str):
    """
    Read inventory from Redis.

    Redis failures should not make the API unavailable, so database
    operations continue normally if Redis cannot be reached.
    """

    try:
        cached_inventory = get_inventory_cache(sku)

        if cached_inventory:
            logger.info("Inventory cache hit for SKU %s.", sku)

        else:
            logger.info("Inventory cache miss for SKU %s.", sku)

        return cached_inventory

    except Exception:
        logger.warning(
            "Redis unavailable while reading SKU %s. "
            "Falling back to PostgreSQL.",
            sku,
        )

        return None


def safely_cache_inventory(
    sku: str,
    inventory: dict,
):
    """
    Save an inventory record to Redis without allowing Redis failures
    to interrupt normal API behavior.
    """

    try:
        save_inventory_cache(
            sku,
            inventory,
        )

    except Exception:
        logger.warning(
            "Unable to cache inventory for SKU %s.",
            sku,
        )


def safely_delete_inventory_cache(sku: str):
    """
    Invalidate cached inventory after inventory-changing operations.
    """

    try:
        delete_inventory_cache(sku)

        logger.info(
            "Invalidated inventory cache for SKU %s.",
            sku,
        )

    except Exception:
        logger.warning(
            "Unable to invalidate inventory cache for SKU %s.",
            sku,
        )


# -------------------------------------------------------------------
# Inventory
# -------------------------------------------------------------------

def get_inventory(
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
):
    """
    Return paginated inventory records.
    """

    limit = min(
        max(limit, 1),
        MAX_PAGE_LIMIT,
    )

    offset = max(
        offset,
        0,
    )

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    products.id,
                    products.sku,
                    products.name,
                    inventory.quantity,
                    inventory.location
                FROM products
                JOIN inventory
                    ON products.id = inventory.product_id
                ORDER BY products.name
                LIMIT %s
                OFFSET %s;
                """,
                (
                    limit,
                    offset,
                ),
            )

            return cursor.fetchall()

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Failed to retrieve inventory."
        )

        raise HTTPException(
            status_code=500,
            detail="Inventory could not be retrieved.",
        ) from error

    finally:
        release_connection(connection)


def get_inventory_by_sku(sku: str):
    """
    Retrieve one inventory record.

    Redis is checked first. PostgreSQL is queried on a cache miss,
    and the returned record is then cached.
    """

    normalized_sku = sku.strip()

    if not normalized_sku:
        raise HTTPException(
            status_code=400,
            detail="SKU cannot be empty.",
        )

    cached_inventory = safely_get_cached_inventory(
        normalized_sku
    )

    if cached_inventory:
        return cached_inventory

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    products.id,
                    products.sku,
                    products.name,
                    inventory.quantity,
                    inventory.location
                FROM products
                JOIN inventory
                    ON products.id = inventory.product_id
                WHERE products.sku = %s;
                """,
                (normalized_sku,),
            )

            inventory = cursor.fetchone()

            if inventory is None:
                raise HTTPException(
                    status_code=404,
                    detail="Inventory item not found.",
                )

            inventory_dict = dict(inventory)

            safely_cache_inventory(
                normalized_sku,
                inventory_dict,
            )

            return inventory_dict

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Failed to retrieve inventory for SKU %s.",
            normalized_sku,
        )

        raise HTTPException(
            status_code=500,
            detail="Inventory item could not be retrieved.",
        ) from error

    finally:
        release_connection(connection)


def receive_inventory(
    sku: str,
    name: str,
    quantity: int,
    location: str,
):
    """
    Receive inventory for a new or existing product.

    Existing product quantities are incremented atomically.
    """

    normalized_sku = sku.strip()
    normalized_name = name.strip()
    normalized_location = location.strip()

    if not normalized_sku:
        raise HTTPException(
            status_code=400,
            detail="SKU cannot be empty.",
        )

    if not normalized_name:
        raise HTTPException(
            status_code=400,
            detail="Product name cannot be empty.",
        )

    if not normalized_location:
        raise HTTPException(
            status_code=400,
            detail="Location cannot be empty.",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero.",
        )

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                INSERT INTO products (
                    sku,
                    name
                )
                VALUES (
                    %s,
                    %s
                )
                ON CONFLICT (sku)
                DO UPDATE SET
                    name = EXCLUDED.name
                RETURNING
                    id,
                    sku,
                    name;
                """,
                (
                    normalized_sku,
                    normalized_name,
                ),
            )

            product = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO inventory (
                    product_id,
                    quantity,
                    location
                )
                VALUES (
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT (product_id)
                DO UPDATE SET
                    quantity =
                        inventory.quantity
                        + EXCLUDED.quantity,
                    location =
                        EXCLUDED.location
                RETURNING
                    quantity,
                    location;
                """,
                (
                    product["id"],
                    quantity,
                    normalized_location,
                ),
            )

            inventory = cursor.fetchone()

            connection.commit()

            safely_delete_inventory_cache(
                normalized_sku
            )

            logger.info(
                "Received %s units of SKU %s.",
                quantity,
                normalized_sku,
            )

            return {
                "message": "Inventory received successfully.",
                "product": {
                    "id": product["id"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": inventory["quantity"],
                    "location": inventory["location"],
                },
            }

    except HTTPException:
        if connection:
            connection.rollback()

        raise

    except Exception as error:
        if connection:
            connection.rollback()

        logger.exception(
            "Failed to receive inventory for SKU %s.",
            normalized_sku,
        )

        raise HTTPException(
            status_code=500,
            detail="Inventory could not be received.",
        ) from error

    finally:
        release_connection(connection)


def search_inventory(
    keyword: str,
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
):
    """
    Search inventory by SKU or product name.
    """

    normalized_keyword = keyword.strip()

    if not normalized_keyword:
        raise HTTPException(
            status_code=400,
            detail="Search keyword cannot be empty.",
        )

    limit = min(
        max(limit, 1),
        MAX_PAGE_LIMIT,
    )

    offset = max(
        offset,
        0,
    )

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            search_value = f"%{normalized_keyword}%"

            cursor.execute(
                """
                SELECT
                    products.id,
                    products.sku,
                    products.name,
                    inventory.quantity,
                    inventory.location
                FROM products
                JOIN inventory
                    ON products.id = inventory.product_id
                WHERE products.sku ILIKE %s
                   OR products.name ILIKE %s
                ORDER BY products.name
                LIMIT %s
                OFFSET %s;
                """,
                (
                    search_value,
                    search_value,
                    limit,
                    offset,
                ),
            )

            return cursor.fetchall()

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Inventory search failed for keyword %s.",
            normalized_keyword,
        )

        raise HTTPException(
            status_code=500,
            detail="Inventory search failed.",
        ) from error

    finally:
        release_connection(connection)


def get_low_stock_items(
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
):
    """
    Return products below the configured stock threshold.
    """

    limit = min(
        max(limit, 1),
        MAX_PAGE_LIMIT,
    )

    offset = max(
        offset,
        0,
    )

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    products.id,
                    products.sku,
                    products.name,
                    inventory.quantity,
                    inventory.location
                FROM products
                JOIN inventory
                    ON products.id = inventory.product_id
                WHERE inventory.quantity < %s
                ORDER BY inventory.quantity
                LIMIT %s
                OFFSET %s;
                """,
                (
                    LOW_STOCK_THRESHOLD,
                    limit,
                    offset,
                ),
            )

            return cursor.fetchall()

    except Exception as error:
        logger.exception(
            "Failed to retrieve low-stock inventory."
        )

        raise HTTPException(
            status_code=500,
            detail="Low-stock inventory could not be retrieved.",
        ) from error

    finally:
        release_connection(connection)


# -------------------------------------------------------------------
# Orders
# -------------------------------------------------------------------

def get_orders(
    limit: int = DEFAULT_PAGE_LIMIT,
    offset: int = 0,
):
    """
    Return paginated store orders.
    """

    limit = min(
        max(limit, 1),
        MAX_PAGE_LIMIT,
    )

    offset = max(
        offset,
        0,
    )

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    orders.id,
                    orders.store,
                    orders.status,
                    orders.created_at,
                    products.sku,
                    products.name AS product_name,
                    order_items.quantity
                        AS ordered_quantity
                FROM orders
                JOIN order_items
                    ON orders.id =
                        order_items.order_id
                JOIN products
                    ON products.id =
                        order_items.product_id
                ORDER BY orders.created_at DESC
                LIMIT %s
                OFFSET %s;
                """,
                (
                    limit,
                    offset,
                ),
            )

            return cursor.fetchall()

    except Exception as error:
        logger.exception(
            "Failed to retrieve orders."
        )

        raise HTTPException(
            status_code=500,
            detail="Orders could not be retrieved.",
        ) from error

    finally:
        release_connection(connection)


def create_order(
    sku: str,
    quantity: int,
    store: str,
):
    """
    Create a store order and decrement inventory atomically.

    SELECT ... FOR UPDATE locks the inventory row until the
    transaction completes, preventing concurrent orders from
    overselling the same inventory.
    """

    normalized_sku = sku.strip()
    normalized_store = store.strip()

    if not normalized_sku:
        raise HTTPException(
            status_code=400,
            detail="SKU cannot be empty.",
        )

    if not normalized_store:
        raise HTTPException(
            status_code=400,
            detail="Store cannot be empty.",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero.",
        )

    connection = None

    try:
        connection = get_connection()

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    products.id,
                    products.sku,
                    products.name,
                    inventory.quantity
                FROM products
                JOIN inventory
                    ON products.id =
                        inventory.product_id
                WHERE products.sku = %s
                FOR UPDATE;
                """,
                (normalized_sku,),
            )

            product = cursor.fetchone()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail="Product not found.",
                )

            if product["quantity"] < quantity:
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient inventory.",
                )

            cursor.execute(
                """
                INSERT INTO orders (
                    store,
                    status
                )
                VALUES (
                    %s,
                    %s
                )
                RETURNING
                    id,
                    store,
                    status,
                    created_at;
                """,
                (
                    normalized_store,
                    "completed",
                ),
            )

            order = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity
                )
                VALUES (
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    order["id"],
                    product["id"],
                    quantity,
                ),
            )

            cursor.execute(
                """
                UPDATE inventory
                SET quantity = quantity - %s
                WHERE product_id = %s
                RETURNING quantity;
                """,
                (
                    quantity,
                    product["id"],
                ),
            )

            updated_inventory = cursor.fetchone()

            connection.commit()

            safely_delete_inventory_cache(
                normalized_sku
            )

            logger.info(
                "Created order %s for store %s "
                "using SKU %s.",
                order["id"],
                normalized_store,
                normalized_sku,
            )

            return {
                "message": "Order created successfully.",
                "order": {
                    "id": order["id"],
                    "store": order["store"],
                    "status": order["status"],
                    "created_at": order["created_at"],
                    "sku": product["sku"],
                    "product_name": product["name"],
                    "ordered_quantity": quantity,
                    "remaining_quantity":
                        updated_inventory["quantity"],
                },
            }

    except HTTPException:
        if connection:
            connection.rollback()

        raise

    except Exception as error:
        if connection:
            connection.rollback()

        logger.exception(
            "Failed to create order for SKU %s.",
            normalized_sku,
        )

        raise HTTPException(
            status_code=500,
            detail="The order could not be created.",
        ) from error

    finally:
        release_connection(connection)
