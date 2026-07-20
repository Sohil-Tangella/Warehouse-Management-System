"""
schemas.py

Defines the request and response models used by the Warehouse
Management System API.

These schemas validate incoming requests and format API responses.
"""

from datetime import datetime
from pydantic import BaseModel


class ReceiveInventoryRequest(BaseModel):
    sku: str
    name: str
    quantity: int
    location: str


class CreateOrderRequest(BaseModel):
    sku: str
    quantity: int
    store: str


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str


class InventoryResponse(BaseModel):
    id: int
    sku: str
    name: str
    quantity: int
    location: str


class OrderResponse(BaseModel):
    id: int
    store: str
    status: str
    created_at: datetime
    sku: str
    product_name: str
    ordered_quantity: int
    remaining_quantity: int