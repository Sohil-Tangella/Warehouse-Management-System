# Warehouse-Management-System
# Warehouse Management System

## Overview

The Warehouse Management System is a backend application that simulates inventory operations within a warehouse environment. It provides RESTful API endpoints for receiving inventory, searching products, managing store orders, and identifying low-stock items. The project demonstrates backend software engineering concepts including API development, relational database design, caching, and business logic implementation.

---

## Features

- View all warehouse inventory
- Receive new inventory shipments
- Search products by SKU or product name
- Create store orders
- Automatically update inventory after orders
- Generate low-stock alerts
- Cache inventory data using Redis
- RESTful API built with FastAPI

---

## Technologies

- Python
- FastAPI
- PostgreSQL
- Redis

---

## System Architecture

```
Client
   │
   ▼
FastAPI
   │
   ├── Inventory API
   ├── Orders API
   │
   ▼
Business Logic
   │
   ├── PostgreSQL
   └── Redis Cache
```

---

## Project Structure

```
warehouse-management-system/

├── main.py
├── inventory.py
├── orders.py
├── database.py
├── redis_client.py
├── models.py
├── schemas.py
└── README.md
```

---

## Core Functionality

### Inventory Management

- View current warehouse inventory
- Receive new products
- Update inventory quantities
- Store warehouse locations

### Product Search

- Search products by SKU
- Search products by product name

### Order Management

- Create store orders
- Verify inventory availability
- Reduce inventory quantities after successful orders
- Prevent orders with insufficient inventory

### Inventory Alerts

- Identify products below the minimum inventory threshold
- Return low-stock inventory reports

### Redis Caching

- Cache frequently accessed inventory data
- Reduce unnecessary database queries
- Improve API response time

---

## Database Design

The system uses four primary tables:

### Products

Stores product information.

- Product ID
- SKU
- Product Name

### Inventory

Stores warehouse inventory.

- Product ID
- Quantity
- Warehouse Location

### Orders

Stores store orders.

- Order ID
- Store
- Status
- Created Date

### Order Items

Connects products to orders.

- Order ID
- Product ID
- Quantity Ordered

---

## API Endpoints

### Inventory

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/inventory` | View inventory |
| POST | `/inventory/receive` | Receive inventory |
| GET | `/inventory/search` | Search inventory |
| GET | `/inventory/alerts` | View low-stock alerts |

### Orders

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/orders` | View all orders |
| POST | `/orders` | Create a store order |

---

## Example Workflow

1. Receive inventory into the warehouse.
2. Search available inventory.
3. Create a store order.
4. Validate inventory availability.
5. Update warehouse inventory.
6. Return the completed order.
7. Generate low-stock alerts when inventory falls below the threshold.

---

## Skills Demonstrated

- REST API Development
- Backend Software Engineering
- FastAPI
- PostgreSQL
- Redis Caching
- SQL
- Database Design
- Business Logic Implementation
- Inventory Management
- Order Processing
- Software Architecture