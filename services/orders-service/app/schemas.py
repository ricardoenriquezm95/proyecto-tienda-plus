"""Contratos de entrada/salida de la API (ver sección 5 del README)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer

from app.domain import OrderStatus

Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class OrderItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0, examples=[1])
    quantity: int = Field(gt=0, le=1_000, examples=[2])


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_email: EmailStr = Field(examples=["ana@example.com"])
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    unit_price: Money
    line_subtotal: Money


class OrderCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    total: Money


class OrderSummary(OrderCreated):
    pass


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_email: str
    items: list[OrderItemOut]
    status: OrderStatus
    subtotal: Money
    tax: Money
    total: Money
    created_at: datetime


class OrderStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus


class HealthOut(BaseModel):
    status: str
    service: str | None = None
    version: str | None = None
