"""Contratos de entrada/salida de la API."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# Los importes se guardan como Decimal (sin errores de redondeo) y se devuelven como número JSON.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class ProductCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=120, examples=["Taza"])
    category: str = Field(default="general", min_length=1, max_length=60, examples=["menaje"])
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=[12.5])
    stock: int = Field(default=0, ge=0, le=1_000_000, examples=[40])


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    price: Money
    stock: int


class StockAdjust(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta: int = Field(ge=-1_000_000, le=1_000_000, examples=[-5])


class QuantityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(gt=0, le=10_000, examples=[2])


class StockOut(BaseModel):
    id: int
    stock: int


class HealthOut(BaseModel):
    status: str
    service: str | None = None
    version: str | None = None
