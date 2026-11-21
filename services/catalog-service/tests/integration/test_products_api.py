from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

pytestmark = pytest.mark.integration

BASE = "/api/v1/products"


# --- Salud ---------------------------------------------------------------------------
def test_liveness_is_public(client):
    assert client.get("/health/live").json() == {"status": "ok"}


def test_health_requires_admin(client, admin_headers):
    assert client.get("/health").status_code == 403
    response = client.get("/health", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --- Alta y consulta (C-001, C-002, C-007) ---------------------------------------------
def test_create_product_requires_admin(client):
    response = client.post(f"{BASE}/create", json={"name": "Taza", "price": 12.5, "stock": 40})
    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso restringido a administradores"}


def test_create_and_get_product(make_product, client):
    created = make_product()
    assert created == {
        "id": created["id"],
        "name": "Taza",
        "category": "menaje",
        "price": 12.5,
        "stock": 40,
    }
    assert client.get(f"{BASE}/{created['id']}").json() == created


def test_create_product_validation_error_format(client, admin_headers):
    response = client.post(f"{BASE}/create", json={"name": "", "price": -1}, headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["detail"] == "Datos de entrada no válidos"


def test_get_unknown_product_returns_404(client):
    response = client.get(f"{BASE}/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Producto no encontrado"}


def test_list_and_filter_by_category(make_product, client):
    make_product(name="Taza", category="menaje")
    make_product(name="Miel", category="alimentacion")
    make_product(name="Plato", category="menaje")

    assert len(client.get(f"{BASE}/list").json()) == 3
    menaje = client.get(f"{BASE}/list", params={"category": "menaje"}).json()
    assert [p["name"] for p in menaje] == ["Taza", "Plato"]


# --- Ajuste de stock (admin) -------------------------------------------------------------
def test_adjust_stock(make_product, client, admin_headers):
    product = make_product(stock=40)
    response = client.patch(
        f"{BASE}/{product['id']}/stock", json={"delta": -5}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == {"id": product["id"], "stock": 35}


def test_adjust_stock_cannot_go_negative(make_product, client, admin_headers):
    product = make_product(stock=2)
    response = client.patch(
        f"{BASE}/{product['id']}/stock", json={"delta": -3}, headers=admin_headers
    )
    assert response.status_code == 409
    assert client.get(f"{BASE}/{product['id']}").json()["stock"] == 2


def test_adjust_stock_unknown_product(client, admin_headers):
    response = client.patch(f"{BASE}/42/stock", json={"delta": 1}, headers=admin_headers)
    assert response.status_code == 404


# --- Reserva / liberación (uso interno) -----------------------------------------------
def test_reserve_and_release(make_product, client, internal_headers):
    product = make_product(stock=40)
    pid = product["id"]

    reserved = client.post(f"{BASE}/{pid}/reserve", json={"quantity": 2}, headers=internal_headers)
    assert reserved.status_code == 200
    assert reserved.json() == {"id": pid, "stock": 38}

    released = client.post(f"{BASE}/{pid}/release", json={"quantity": 2}, headers=internal_headers)
    assert released.json() == {"id": pid, "stock": 40}


def test_reserve_without_enough_stock_is_rejected(make_product, client, internal_headers):
    product = make_product(stock=1)
    response = client.post(
        f"{BASE}/{product['id']}/reserve", json={"quantity": 2}, headers=internal_headers
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Stock insuficiente"}
    assert client.get(f"{BASE}/{product['id']}").json()["stock"] == 1


def test_reserve_unknown_product(client, internal_headers):
    response = client.post(f"{BASE}/7/reserve", json={"quantity": 1}, headers=internal_headers)
    assert response.status_code == 404


def test_reserve_requires_internal_token(make_product, client, admin_headers):
    product = make_product()
    response = client.post(
        f"{BASE}/{product['id']}/reserve", json={"quantity": 1}, headers=admin_headers
    )
    assert response.status_code == 403


def test_successive_reservations_never_oversell(make_product, client, internal_headers):
    product = make_product(stock=3)
    codes = [
        client.post(
            f"{BASE}/{product['id']}/reserve", json={"quantity": 1}, headers=internal_headers
        ).status_code
        for _ in range(5)
    ]
    assert codes == [200, 200, 200, 409, 409]
    assert client.get(f"{BASE}/{product['id']}").json()["stock"] == 0


# --- Datos de demostración -------------------------------------------------------------
def test_seed_demo_data_only_when_empty(settings):
    seeded = replace(settings, seed_demo_data=True)
    with TestClient(create_app(seeded)) as test_client:
        products = test_client.get(f"{BASE}/list").json()
    assert len(products) == 5
