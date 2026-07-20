"""
orders.py

Handles all order-related API endpoints.

This file allows users to:
- Create store orders
- View existing orders

Database operations are handled in database.py.
"""

from fastapi import APIRouter
from database import (
    create_order,
    get_orders
)

router = APIRouter()


@router.get("/")
def view_orders():
    return get_orders()


@router.post("/")
def place_order(
    sku: str,
    quantity: int,
    store: str
):
    return create_order(
        sku,
        quantity,
        store
    )