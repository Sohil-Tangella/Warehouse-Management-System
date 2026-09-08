# Warehouse Management System

## Overview

The Warehouse Management System is a backend application that simulates inventory and order-processing operations within a warehouse environment. It provides RESTful API endpoints for receiving inventory, retrieving and searching products, processing store orders, and monitoring low-stock items.

The project demonstrates backend software engineering concepts including REST API development, PostgreSQL transactions, Redis caching, connection pooling, request validation, pagination, concurrency-safe inventory updates, and database integrity constraints.

---

## Features

- View paginated warehouse inventory
- Retrieve individual products by SKU
- Receive and update inventory shipments
- Search products by SKU or product name
- Create and process store orders
- Automatically update inventory after completed orders
- Prevent orders when inventory is insufficient
- Prevent concurrent orders from overselling inventory
- Generate low-stock alerts
- Cache frequently accessed inventory records using Redis
- Automatically invalidate stale cache entries after inventory changes
- Fall back to PostgreSQL when Redis is unavailable
- Validate incoming API requests with Pydantic
- Monitor PostgreSQL and Redis availability through health checks

---

## Technologies

- **Python**
- **FastAPI**
- **PostgreSQL**
- **Redis**
- **Pydantic**
- **psycopg2**

---

## System Architecture

```text
Client
   │
   ▼
FastAPI
   │
   ├── Inventory API
   └── Orders API
          │
          ▼
     Database Layer
          │
     ┌────┴────┐
     ▼         ▼
PostgreSQL    Redis
   │          Cache
   ▼
Transactions &
Persistent Data
```

PostgreSQL serves as the primary source of truth for inventory and order data. Redis provides a cache-aside layer for frequently accessed inventory records. If Redis is unavailable, requests automatically fall back to PostgreSQL.

---

## Project Structure

```text
Warehouse-Management-System/
│
├── main.py
├── inventory.py
├── orders.py
├── database.py
├── redis_client.py
├── models.py
├── schemas.py
└── README.md
```

### `main.py`

Configures the FastAPI application, registers API routes, initializes the PostgreSQL schema, manages application startup and shutdown, configures logging, and exposes system health endpoints.

### `inventory.py`

Defines API endpoints for retrieving inventory, looking up individual SKUs, receiving shipments, searching products, and viewing low-stock alerts.

### `orders.py`

Defines API endpoints for creating store orders and retrieving paginated order history.

### `database.py`

Handles PostgreSQL connection pooling, SQL queries, transactions, pagination, inventory operations, order processing, and Redis cache integration.

### `redis_client.py`

Manages Redis connectivity, TTL-based inventory caching, cache retrieval, and cache invalidation.

### `models.py`

Defines and initializes the PostgreSQL database schema, integrity constraints, relationships, and indexes.

### `schemas.py`

Defines Pydantic request and response models used for API validation and consistent data structures.

---

## Core Functionality

### Inventory Management

- Retrieve warehouse inventory
- Retrieve individual inventory records by SKU
- Receive new products
- Increment quantities for existing products
- Update warehouse locations
- Paginate inventory results

### Product Search

- Search products by SKU
- Search products by product name
- Perform case-insensitive searches
- Paginate search results

### Order Processing

- Create store orders
- Verify product availability
- Validate requested quantities
- Reduce inventory after successful orders
- Reject orders with insufficient inventory
- Roll back failed database transactions
- Prevent concurrent orders from overselling stock

### Inventory Alerts

- Identify products below the configured inventory threshold
- Return low-stock products ordered by remaining quantity
- Paginate low-stock results

---

## Redis Caching

Individual inventory lookups use a cache-aside strategy.

```text
GET /inventory/{sku}
        │
        ▼
    Check Redis
     /       \
 Cache Hit   Cache Miss
     │           │
     ▼           ▼
   Return    PostgreSQL
                 │
                 ▼
            Cache Result
                 │
                 ▼
               Return
```

Inventory records are stored in Redis with a configurable time-to-live (TTL).

When inventory changes after receiving a shipment or processing an order, the corresponding Redis entry is invalidated to prevent stale inventory data from being returned.

Redis is treated as an optimization rather than a required dependency. If Redis becomes unavailable, the application continues retrieving inventory directly from PostgreSQL.

---

## Transaction-Safe Order Processing

Orders are processed using PostgreSQL transactions to keep inventory and order data consistent.

Before inventory is modified, the corresponding row is locked using:

```sql
SELECT ...
FOR UPDATE;
```

The order workflow is:

```text
Order Request
     │
     ▼
Lock Inventory Row
     │
     ▼
Verify Available Inventory
     │
     ▼
Create Order
     │
     ▼
Create Order Item
     │
     ▼
Decrease Inventory
     │
     ▼
Commit Transaction
     │
     ▼
Invalidate Redis Cache
```

The row-level lock prevents two concurrent orders from consuming the same available inventory. If any part of order processing fails, the transaction is rolled back.

---

## Request Validation

Pydantic validates incoming API requests before they reach the database layer.

Validation includes:

- Positive inventory quantities
- Positive order quantities
- Non-empty SKUs
- Non-empty product names
- Non-empty warehouse locations
- Non-empty store names
- Maximum string lengths

This prevents invalid input from reaching PostgreSQL.

---

## Database Design

The system uses four relational tables.

### Products

Stores product information.

- Product ID
- SKU
- Product Name

SKUs are unique, and database constraints prevent empty product identifiers and names.

### Inventory

Stores warehouse inventory.

- Inventory ID
- Product ID
- Quantity
- Warehouse Location

Each product has one inventory record, and PostgreSQL prevents inventory quantities from becoming negative.

### Orders

Stores store orders.

- Order ID
- Store
- Status
- Created Date

### Order Items

Connects products to orders.

- Order Item ID
- Order ID
- Product ID
- Quantity Ordered

Database constraints ensure ordered quantities are positive.

---

## API Endpoints

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | View API status and information |
| GET | `/health` | Check PostgreSQL and Redis health |

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/inventory` | View paginated inventory |
| GET | `/inventory/{sku}` | Retrieve inventory by SKU |
| POST | `/inventory/receive` | Receive inventory |
| GET | `/inventory/search` | Search inventory |
| GET | `/inventory/alerts` | View low-stock alerts |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders` | View paginated order history |
| POST | `/orders` | Create a store order |

FastAPI also automatically provides interactive API documentation at:

```text
/docs
```

---

## Pagination

Inventory, search, low-stock, and order endpoints support `limit` and `offset` parameters.

Example:

```text
GET /inventory?limit=50&offset=0
GET /orders?limit=25&offset=50
```

API requests are limited to a maximum of 100 records per page.

---

## Reliability and Data Integrity

The system includes several safeguards for reliable inventory and order processing:

- PostgreSQL connection pooling
- Parameterized SQL queries
- Transaction rollback on failed operations
- Row-level locking during order processing
- Database-level integrity constraints
- Database indexes for common query patterns
- Redis cache invalidation after inventory changes
- PostgreSQL fallback when Redis is unavailable
- Pydantic request validation
- Structured application logging
- PostgreSQL and Redis health checks
- Graceful connection cleanup during application shutdown

---

## Example Workflow

1. Receive inventory into the warehouse.
2. Store product and inventory information in PostgreSQL.
3. Retrieve or search available inventory.
4. Cache frequently accessed inventory records in Redis.
5. Receive a store order.
6. Lock the corresponding inventory row.
7. Verify sufficient inventory is available.
8. Create the order and update inventory within a transaction.
9. Commit the transaction.
10. Invalidate the affected Redis cache entry.
11. Generate low-stock alerts when inventory falls below the configured threshold.
