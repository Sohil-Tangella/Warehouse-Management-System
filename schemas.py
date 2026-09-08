"""
schemas.py

Defines the request and response models used by the Warehouse
Management System API.

These schemas provide:
- Request-body validation
- Type validation
- String length validation
- Quantity constraints
- Consistent API response structures
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# -------------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------------

class ReceiveInventoryRequest(BaseModel):
    sku: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
    )
    quantity: int = Field(
        ...,
        gt=0,
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    @field_validator(
        "sku",
        "name",
        "location",
    )
    @classmethod
    def remove_whitespace(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be empty."
            )

        return value


class CreateOrderRequest(BaseModel):
    sku: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    quantity: int = Field(
        ...,
        gt=0,
    )
    store: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    @field_validator(
        "sku",
        "store",
    )
    @classmethod
    def remove_whitespace(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be empty."
            )

        return value


# -------------------------------------------------------------------
# Response Schemas
# -------------------------------------------------------------------

class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    sku: str
    name: str


class InventoryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    sku: str
    name: str
    quantity: int = Field(
        ...,
        ge=0,
    )
    location: str


class OrderResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    store: str
    status: str
    created_at: datetime
    sku: str
    product_name: str
    ordered_quantity: int = Field(
        ...,
        gt=0,
    )
    remaining_quantity: int = Field(
        ...,
        ge=0,
    )


# -------------------------------------------------------------------
# API Response Wrappers
# -------------------------------------------------------------------

class ReceiveInventoryResponse(BaseModel):
    message: str
    product: InventoryResponse


class CreateOrderResponse(BaseModel):
    message: str
    order: OrderResponse
