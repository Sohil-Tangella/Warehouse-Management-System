"""
inventory.py

Handles all inventory-related API endpoints.

This file allows users to:
- View paginated inventory
- View a single inventory item by SKU
- Receive new inventory
- Search products
- View low-stock alerts

Database operations are handled in database.py.
"""

from fastapi import APIRouter, Query

from database import (
    get_inventory,
    get_inventory_by_sku,
    get_low_stock_items,
    receive_inventory,
    search_inventory,
)

from schemas import ReceiveInventoryRequest


router = APIRouter()


@router.get("/")
def view_inventory(
    limit: int = Query(
        default=50,
        ge=1,
        le=100
    ),
    offset: int = Query(
        default=0,
        ge=0
    )
):
    return get_inventory(
        limit=limit,
        offset=offset
    )


@router.get("/search")
def search_product(
    keyword: str = Query(
        ...,
        min_length=1
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100
    ),
    offset: int = Query(
        default=0,
        ge=0
    )
):
    return search_inventory(
        keyword=keyword,
        limit=limit,
        offset=offset
    )


@router.get("/alerts")
def low_stock_alerts(
    limit: int = Query(
        default=50,
        ge=1,
        le=100
    ),
    offset: int = Query(
        default=0,
        ge=0
    )
):
    return get_low_stock_items(
        limit=limit,
        offset=offset
    )


@router.get("/{sku}")
def view_inventory_item(
    sku: str
):
    return get_inventory_by_sku(
        sku
    )


@router.post("/receive")
def receive_product(
    request: ReceiveInventoryRequest
):
    return receive_inventory(
        sku=request.sku,
        name=request.name,
        quantity=request.quantity,
        location=request.location
    )
