"""
models.py

Defines the database tables used by the Warehouse Management System.

This file contains the SQLAlchemy models for:
- Products
- Inventory
- Orders
- Order Items
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String
)

from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        unique=True,
        nullable=False
    )
    quantity = Column(Integer, nullable=False)
    location = Column(String, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    store = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )
    quantity = Column(Integer, nullable=False)