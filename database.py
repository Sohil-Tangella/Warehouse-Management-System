"""
database.py

Connects the Warehouse Management System to PostgreSQL.

This file handles:
- Reading inventory
- Receiving inventory
- Searching products
- Finding low-stock products
- Creating store orders
- Viewing existing orders

Database settings are loaded from environment variables.
"""

import os

from dotenv import load_dotenv
from fastapi import HTTPException
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

load_dotenv()

database_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("DB_NAME", "warehouse"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres")
)

LOW_STOCK_THRESHOLD = 25


def get_connection():
    return database_pool.getconn()


def release_connection(connection):
    database_pool.putconn(connection)


def get_inventory():
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
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
                ORDER BY products.name;
                """
            )

            return cursor.fetchall()

    finally:
        release_connection(connection)


def receive_inventory(
    sku: str,
    name: str,
    quantity: int,
    location: str
):
    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero."
        )

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO products (sku, name)
                VALUES (%s, %s)
                ON CONFLICT (sku)
                DO UPDATE SET name = EXCLUDED.name
                RETURNING id, sku, name;
                """,
                (sku, name)
            )

            product = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO inventory (
                    product_id,
                    quantity,
                    location
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (product_id)
                DO UPDATE SET
                    quantity = inventory.quantity + EXCLUDED.quantity,
                    location = EXCLUDED.location
                RETURNING quantity, location;
                """,
                (
                    product["id"],
                    quantity,
                    location
                )
            )

            inventory = cursor.fetchone()

            connection.commit()

            return {
                "message": "Inventory received successfully.",
                "product": {
                    "id": product["id"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": inventory["quantity"],
                    "location": inventory["location"]
                }
            }

    except Exception:
        connection.rollback()
        raise

    finally:
        release_connection(connection)


def search_inventory(keyword: str):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            search_value = f"%{keyword}%"

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
                ORDER BY products.name;
                """,
                (
                    search_value,
                    search_value
                )
            )

            return cursor.fetchall()

    finally:
        release_connection(connection)


def get_low_stock_items():
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
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
                ORDER BY inventory.quantity;
                """,
                (LOW_STOCK_THRESHOLD,)
            )

            return cursor.fetchall()

    finally:
        release_connection(connection)


def get_orders():
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    orders.id,
                    orders.store,
                    orders.status,
                    orders.created_at,
                    products.sku,
                    products.name,
                    order_items.quantity
                FROM orders
                JOIN order_items
                    ON orders.id = order_items.order_id
                JOIN products
                    ON products.id = order_items.product_id
                ORDER BY orders.created_at DESC;
                """
            )

            return cursor.fetchall()

    finally:
        release_connection(connection)


def create_order(
    sku: str,
    quantity: int,
    store: str
):
    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero."
        )

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    products.id,
                    products.sku,
                    products.name,
                    inventory.quantity
                FROM products
                JOIN inventory
                    ON products.id = inventory.product_id
                WHERE products.sku = %s
                FOR UPDATE;
                """,
                (sku,)
            )

            product = cursor.fetchone()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail="Product not found."
                )

            if product["quantity"] < quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient inventory."
                )

            cursor.execute(
                """
                INSERT INTO orders (store, status)
                VALUES (%s, %s)
                RETURNING id, store, status, created_at;
                """,
                (
                    store,
                    "completed"
                )
            )

            order = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity
                )
                VALUES (%s, %s, %s);
                """,
                (
                    order["id"],
                    product["id"],
                    quantity
                )
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
                    product["id"]
                )
            )

            updated_inventory = cursor.fetchone()

            connection.commit()

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
                    "remaining_quantity": updated_inventory["quantity"]
                }
            }

    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail="The order could not be created."
        )

    finally:
        release_connection(connection)