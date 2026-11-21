from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import ProductCreate, ProductOut, QuantityRequest

pytestmark = pytest.mark.unit


def test_product_create_valid_and_strips_whitespace():
    product = ProductCreate(name="  Taza  ", price=12.5, stock=40)
    assert product.name == "Taza"
    assert product.price == Decimal("12.5")
    assert product.category == "general"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "price": 1, "stock": 1},
        {"name": "Taza", "price": 0, "stock": 1},
        {"name": "Taza", "price": -3, "stock": 1},
        {"name": "Taza", "price": 1.234, "stock": 1},
        {"name": "Taza", "price": 1, "stock": -1},
        {"name": "Taza", "price": 1, "stock": 1, "extra": "no permitido"},
    ],
)
def test_product_create_rejects_invalid_payloads(payload):
    with pytest.raises(ValidationError):
        ProductCreate(**payload)


@pytest.mark.parametrize("quantity", [0, -1, 10_001])
def test_quantity_must_be_positive_and_bounded(quantity):
    with pytest.raises(ValidationError):
        QuantityRequest(quantity=quantity)


def test_price_is_serialized_as_json_number():
    out = ProductOut(id=1, name="Taza", category="menaje", price=Decimal("12.50"), stock=3)
    assert out.model_dump(mode="json")["price"] == 12.5
