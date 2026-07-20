"""
inventory.py

Handles all inventory-related API endpoints.

This file allows users to:
- View inventory
- Receive new inventory
- Search products
- View low stock alerts

Database operations are handled in database.py.
"""

from fastapi import APIRouter
from database import (
    get_inventory,
    receive_inventory,
    search_inventory,
    get_low_stock_items
)

router = APIRouter()


@router.get("/")
def view_inventory():
    return get_inventory()


@router.post("/receive")
def receive_product(
    sku: str,
    name: str,
    quantity: int,
    location: str
):
    return receive_inventory(
        sku,
        name,
        quantity,
        location
    )


@router.get("/search")
def search_product(keyword: str):
    return search_inventory(keyword)


@router.get("/alerts")
def low_stock_alerts():
    return get_low_stock_items()