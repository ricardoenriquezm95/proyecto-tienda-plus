"""Pruebas de integración extremo a extremo contra el entorno de Docker Compose.

Todo el tráfico entra por el API Gateway (Nginx), igual que en producción:

    docker compose up -d --build
    pip install -r tests/e2e/requirements.txt
    pytest tests/e2e            # lee ADMIN_TOKEN de la variable de entorno o de .env
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")


def _admin_token() -> str:
    if token := os.getenv("ADMIN_TOKEN"):
        return token
    env_file = Path(__file__).resolve().parents[2] / ".env"
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("ADMIN_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("ADMIN_TOKEN no definido")


ADMIN = {"X-Admin-Token": _admin_token()}


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=GATEWAY_URL, timeout=15) as client:
        yield client


def new_product(api: httpx.Client, stock: int, price: float = 12.5) -> int:
    response = api.post(
        "/api/v1/products/create",
        json={
            "name": f"e2e-{uuid.uuid4().hex[:8]}",
            "price": price,
            "stock": stock,
            "category": "e2e",
        },
        headers=ADMIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def stock_of(api: httpx.Client, product_id: int) -> int:
    return api.get(f"/api/v1/products/{product_id}").json()["stock"]


def order(api: httpx.Client, product_id: int, quantity: int) -> httpx.Response:
    return api.post(
        "/api/v1/orders/create",
        json={
            "customer_email": "e2e@example.com",
            "items": [{"product_id": product_id, "quantity": quantity}],
        },
    )


# --- Gateway ---------------------------------------------------------------------------
def test_gateway_is_healthy_and_hardened(api):
    response = api.get("/healthz")
    assert response.status_code == 200
    assert "nginx/" not in response.headers.get("server", "")  # server_tokens off
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"]


def test_gateway_blocks_internal_endpoints(api):
    pid = new_product(api, stock=3)
    for path in (
        f"/api/v1/products/{pid}/reserve",
        f"/api/v1/products/{pid}/release",
        f"/catalog/api/v1/products/{pid}/reserve",
    ):
        response = api.post(path, json={"quantity": 1})
        assert response.status_code == 403, path
    assert stock_of(api, pid) == 3


def test_gateway_unknown_route_is_404(api):
    assert api.get("/no-existe").status_code == 404


def test_swagger_is_served_through_gateway(api):
    for prefix in ("/catalog", "/orders"):
        assert api.get(f"{prefix}/docs").status_code == 200
        spec = api.get(f"{prefix}/openapi.json").json()
        assert spec["servers"][0]["url"] == prefix


# --- Microservicios --------------------------------------------------------------------
def test_services_are_healthy(api):
    for prefix in ("/catalog", "/orders"):
        assert api.get(f"{prefix}/health/live").status_code == 200
        assert api.get(f"{prefix}/health").status_code == 403
        assert api.get(f"{prefix}/health", headers=ADMIN).json()["status"] == "ok"


def test_order_lifecycle_and_stock(api):
    pid = new_product(api, stock=3)

    created = order(api, pid, 2)
    assert created.status_code == 201, created.text
    assert created.json()["total"] == 30.25
    assert stock_of(api, pid) == 1

    # No se puede sobrevender: el pedido se rechaza y el stock no cambia.
    assert order(api, pid, 2).status_code == 409
    assert stock_of(api, pid) == 1

    # Cancelar devuelve el stock reservado.
    order_id = created.json()["id"]
    assert api.post(f"/api/v1/orders/{order_id}/cancel").json()["status"] == "CANCELADO"
    assert stock_of(api, pid) == 3
    assert api.post(f"/api/v1/orders/{order_id}/pay").status_code == 409

    # Flujo feliz: pagar y enviar.
    second = order(api, pid, 1).json()["id"]
    assert api.post(f"/api/v1/orders/{second}/pay").json()["status"] == "PAGADO"
    assert api.post(f"/api/v1/orders/{second}/ship").status_code == 403
    shipped = api.post(f"/api/v1/orders/{second}/ship", headers=ADMIN)
    assert shipped.json()["status"] == "ENVIADO"


def test_concurrent_orders_never_oversell(api):
    """20 clientes compran a la vez el mismo producto con stock 5: solo 5 lo consiguen."""
    pid = new_product(api, stock=5)

    def buy(_: int) -> int:
        with httpx.Client(base_url=GATEWAY_URL, timeout=30) as client:
            return order(client, pid, 1).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(buy, range(20)))

    # Regla de negocio: exactamente 5 compras aceptadas y el stock a 0 (nunca se sobrevende).
    assert codes.count(201) == 5, codes
    # El resto se rechaza: 409 (sin stock) o 429 (límite de peticiones del gateway).
    assert all(code in (409, 429) for code in codes if code != 201), codes
    assert stock_of(api, pid) == 0
