import pytest

pytestmark = pytest.mark.integration

BASE = "/api/v1/orders"


# --- Salud ---------------------------------------------------------------------------
def test_liveness_is_public(client):
    assert client.get("/health/live").json() == {"status": "ok"}


def test_health_requires_admin(client, admin_headers):
    assert client.get("/health").status_code == 403
    assert client.get("/health", headers=admin_headers).json()["status"] == "ok"


# --- C-003 Crear pedido --------------------------------------------------------------
def test_create_order_reserves_stock_and_computes_total(make_order, catalog):
    order = make_order([{"product_id": 1, "quantity": 2}])
    assert order == {"id": order["id"], "status": "PENDIENTE", "total": 30.25}
    assert catalog.stock(1) == 38


def test_create_order_merges_repeated_products(make_order, catalog, client):
    order = make_order([{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 2}])
    detail = client.get(f"{BASE}/{order['id']}").json()
    assert len(detail["items"]) == 1
    assert detail["items"][0]["quantity"] == 3
    assert catalog.stock(1) == 37


def test_insufficient_stock_rejects_whole_order_and_releases(client, catalog):
    response = client.post(
        f"{BASE}/create",
        json={
            "customer_email": "ana@example.com",
            "items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 5}],
        },
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Stock insuficiente para el producto 2"}
    # La reserva del producto 1 se ha compensado: el stock vuelve a su valor original.
    assert catalog.stock(1) == 40
    assert catalog.stock(2) == 1
    assert ("release", "1") in catalog.calls
    assert client.get(BASE, params={"customer_email": "ana@example.com"}).json() == []


def test_unknown_product_is_422_and_releases(client, catalog):
    response = client.post(
        f"{BASE}/create",
        json={
            "customer_email": "ana@example.com",
            "items": [{"product_id": 1, "quantity": 1}, {"product_id": 99, "quantity": 1}],
        },
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "El producto 99 no existe"}
    assert catalog.stock(1) == 40


def test_catalog_down_returns_503(client, catalog):
    catalog.available = False
    response = client.post(
        f"{BASE}/create",
        json={"customer_email": "ana@example.com", "items": [{"product_id": 1, "quantity": 1}]},
    )
    assert response.status_code == 503


@pytest.mark.parametrize(
    "payload",
    [
        {"customer_email": "no-es-un-email", "items": [{"product_id": 1, "quantity": 1}]},
        {"customer_email": "ana@example.com", "items": []},
        {"customer_email": "ana@example.com", "items": [{"product_id": 1, "quantity": 0}]},
    ],
)
def test_invalid_payload_is_422(client, payload):
    response = client.post(f"{BASE}/create", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Datos de entrada no válidos"


# --- C-006 Consultar pedidos ---------------------------------------------------------
def test_get_order_detail(make_order, client):
    order = make_order([{"product_id": 1, "quantity": 2}, {"product_id": 3, "quantity": 1}])
    detail = client.get(f"{BASE}/{order['id']}").json()
    assert detail["customer_email"] == "ana@example.com"
    assert detail["status"] == "PENDIENTE"
    assert detail["subtotal"] == 29.75
    assert detail["tax"] == 6.25  # 6.2475 -> 6.25
    assert detail["total"] == 36.0
    assert [(i["product_id"], i["quantity"]) for i in detail["items"]] == [(1, 2), (3, 1)]


def test_get_unknown_order_is_404(client):
    response = client.get(f"{BASE}/12345")
    assert response.status_code == 404
    assert response.json() == {"detail": "Pedido no encontrado"}


def test_list_orders_by_customer(make_order, client):
    first = make_order(email="ana@example.com")
    second = make_order(email="Ana@Example.com")
    make_order(email="luis@example.com")
    orders = client.get(BASE, params={"customer_email": "ana@example.com"}).json()
    assert [o["id"] for o in orders] == [second["id"], first["id"]]


# --- C-004 / C-008 Pagar y enviar ----------------------------------------------------
def test_pay_then_ship(make_order, client, admin_headers):
    order = make_order()
    paid = client.post(f"{BASE}/{order['id']}/pay")
    assert paid.json() == {"id": order["id"], "status": "PAGADO"}

    assert client.post(f"{BASE}/{order['id']}/ship").status_code == 403
    shipped = client.post(f"{BASE}/{order['id']}/ship", headers=admin_headers)
    assert shipped.json() == {"id": order["id"], "status": "ENVIADO"}


def test_cannot_ship_pending_order(make_order, client, admin_headers):
    order = make_order()
    response = client.post(f"{BASE}/{order['id']}/ship", headers=admin_headers)
    assert response.status_code == 409
    assert response.json() == {"detail": "No se puede pasar un pedido de PENDIENTE a ENVIADO"}


def test_pay_twice_is_409(make_order, client):
    order = make_order()
    client.post(f"{BASE}/{order['id']}/pay")
    assert client.post(f"{BASE}/{order['id']}/pay").status_code == 409


def test_pay_unknown_order_is_404(client):
    assert client.post(f"{BASE}/999/pay").status_code == 404


# --- C-005 Cancelar ------------------------------------------------------------------
def test_cancel_pending_order_releases_stock(make_order, client, catalog):
    order = make_order([{"product_id": 1, "quantity": 5}])
    assert catalog.stock(1) == 35
    response = client.post(f"{BASE}/{order['id']}/cancel")
    assert response.json() == {"id": order["id"], "status": "CANCELADO"}
    assert catalog.stock(1) == 40


def test_cancel_twice_does_not_release_twice(make_order, client, catalog):
    order = make_order([{"product_id": 1, "quantity": 5}])
    client.post(f"{BASE}/{order['id']}/cancel")
    assert client.post(f"{BASE}/{order['id']}/cancel").status_code == 409
    assert catalog.stock(1) == 40


def test_cannot_cancel_paid_order(make_order, client, catalog):
    order = make_order([{"product_id": 1, "quantity": 2}])
    client.post(f"{BASE}/{order['id']}/pay")
    assert client.post(f"{BASE}/{order['id']}/cancel").status_code == 409
    assert catalog.stock(1) == 38


def test_cannot_pay_cancelled_order(make_order, client):
    order = make_order()
    client.post(f"{BASE}/{order['id']}/cancel")
    assert client.post(f"{BASE}/{order['id']}/pay").status_code == 409
