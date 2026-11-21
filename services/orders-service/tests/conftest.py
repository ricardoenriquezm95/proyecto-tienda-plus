"""Fixtures: BD SQLite en memoria + catalog-service simulado con httpx.MockTransport."""

import json
import re
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ADMIN_TOKEN = "test-admin-token"
INTERNAL_TOKEN = "test-internal-token"
PRODUCT_PATH = re.compile(r"^/api/v1/products/(\d+)(?:/(reserve|release))?$")


class FakeCatalog:
    """Imita el contrato REST del catalog-service manteniendo el stock en memoria."""

    def __init__(self) -> None:
        self.products: dict[int, dict] = {
            1: {"id": 1, "name": "Taza", "category": "menaje", "price": 12.5, "stock": 40},
            2: {"id": 2, "name": "Miel", "category": "alimentacion", "price": 8.9, "stock": 1},
            3: {"id": 3, "name": "Jabón", "category": "cosmetica", "price": 4.75, "stock": 10},
        }
        self.calls: list[tuple[str, str]] = []
        self.available = True

    def stock(self, product_id: int) -> int:
        return self.products[product_id]["stock"]

    def handler(self, request: httpx.Request) -> httpx.Response:
        if not self.available:
            raise httpx.ConnectError("catálogo caído", request=request)
        if request.headers.get("X-Internal-Token") != INTERNAL_TOKEN:
            return httpx.Response(403, json={"detail": "Operación reservada a servicios internos"})

        match = PRODUCT_PATH.match(request.url.path)
        if not match:
            return httpx.Response(404, json={"detail": "Not Found"})
        product_id, action = int(match[1]), match[2]
        self.calls.append((action or "get", str(product_id)))

        product = self.products.get(product_id)
        if product is None:
            return httpx.Response(404, json={"detail": "Producto no encontrado"})
        if action is None:
            return httpx.Response(200, json=product)

        quantity = json.loads(request.content)["quantity"]
        if action == "reserve":
            if product["stock"] < quantity:
                return httpx.Response(409, json={"detail": "Stock insuficiente"})
            product["stock"] -= quantity
        else:
            product["stock"] += quantity
        return httpx.Response(200, json={"id": product_id, "stock": product["stock"]})


@pytest.fixture
def catalog() -> FakeCatalog:
    return FakeCatalog()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        admin_token=ADMIN_TOKEN,
        internal_token=INTERNAL_TOKEN,
        catalog_url="http://catalog.test",
        vat_rate=Decimal("0.21"),
    )


@pytest.fixture
def client(settings: Settings, catalog: FakeCatalog):
    app = create_app(settings, catalog_transport=httpx.MockTransport(catalog.handler))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


@pytest.fixture
def make_order(client):
    def _make(items=None, email="ana@example.com") -> dict:
        items = items or [{"product_id": 1, "quantity": 2}]
        response = client.post(
            "/api/v1/orders/create", json={"customer_email": email, "items": items}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make
