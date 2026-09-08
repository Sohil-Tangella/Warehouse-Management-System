"""
orders.py

Handles all order-related API endpoints.

This file allows users to:
- Create store orders
- View paginated existing orders

Database operations are handled in database.py.
"""

from fastapi import APIRouter, Query

from database import (
    create_order,
    get_orders,
)

from schemas import CreateOrderRequest


router = APIRouter()


@router.get("/")
def view_orders(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):
    return get_orders(
        limit=limit,
        offset=offset,
    )


@router.post("/")
def place_order(
    request: CreateOrderRequest,
):
    return create_order(
        sku=request.sku,
        quantity=request.quantity,
        store=request.store,
    )
