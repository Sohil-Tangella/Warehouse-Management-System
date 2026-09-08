"""
models.py

Defines and initializes the PostgreSQL database schema used by the
Warehouse Management System.

The application uses four relational tables:
- Products
- Inventory
- Orders
- Order Items

Database constraints enforce important data-integrity rules at the
PostgreSQL level.
"""

import logging

from database import get_connection, release_connection


logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Database Schema
# -------------------------------------------------------------------

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,

    CONSTRAINT products_sku_not_empty
        CHECK (LENGTH(TRIM(sku)) > 0),

    CONSTRAINT products_name_not_empty
        CHECK (LENGTH(TRIM(name)) > 0)
);


CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,

    product_id INTEGER UNIQUE NOT NULL
        REFERENCES products(id)
        ON DELETE CASCADE,

    quantity INTEGER NOT NULL DEFAULT 0,

    location VARCHAR(100) NOT NULL,

    CONSTRAINT inventory_quantity_nonnegative
        CHECK (quantity >= 0),

    CONSTRAINT inventory_location_not_empty
        CHECK (LENGTH(TRIM(location)) > 0)
);


CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,

    store VARCHAR(100) NOT NULL,

    status VARCHAR(30) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT orders_store_not_empty
        CHECK (LENGTH(TRIM(store)) > 0),

    CONSTRAINT orders_status_not_empty
        CHECK (LENGTH(TRIM(status)) > 0)
);


CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,

    order_id INTEGER NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,

    product_id INTEGER NOT NULL
        REFERENCES products(id),

    quantity INTEGER NOT NULL,

    CONSTRAINT order_items_quantity_positive
        CHECK (quantity > 0)
);
"""


# -------------------------------------------------------------------
# Database Indexes
# -------------------------------------------------------------------

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_products_name
    ON products(name);

CREATE INDEX IF NOT EXISTS idx_orders_created_at
    ON orders(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_inventory_quantity
    ON inventory(quantity);
"""


# -------------------------------------------------------------------
# Schema Initialization
# -------------------------------------------------------------------

def initialize_database():
    """
    Create the Warehouse Management System tables and indexes if
    they do not already exist.

    The entire initialization runs inside one transaction. If any
    statement fails, all schema changes are rolled back.
    """

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLES_SQL)
            cursor.execute(CREATE_INDEXES_SQL)

        connection.commit()

        logger.info(
            "Warehouse database schema initialized successfully."
        )

    except Exception:
        if connection:
            connection.rollback()

        logger.exception(
            "Failed to initialize warehouse database schema."
        )

        raise

    finally:
        release_connection(connection)
