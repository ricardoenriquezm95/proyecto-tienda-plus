import httpx
import pytest

from app.catalog_client import (
    CatalogClient,
    CatalogUnavailableError,
    InsufficientStockError,
    ProductNotFoundError,
)

pytestmark = pytest.mark.unit


def client_returning(status: int, body: dict | None = None) -> CatalogClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Internal-Token"] == "secret"
        return httpx.Response(status, json=body or {})

    return CatalogClient("http://catalog.test", "secret", transport=httpx.MockTransport(handler))


def test_get_product_ok():
    product = {"id": 1, "name": "Taza", "price": 12.5, "stock": 40}
    assert client_returning(200, product).get_product(1) == product


def test_get_product_not_found():
    with pytest.raises(ProductNotFoundError):
        client_returning(404).get_product(1)


def test_reserve_ok_returns_remaining_stock():
    assert client_returning(200, {"id": 1, "stock": 38}).reserve(1, 2) == 38


def test_reserve_conflict_means_insufficient_stock():
    with pytest.raises(InsufficientStockError):
        client_returning(409).reserve(1, 2)


def test_release_not_found():
    with pytest.raises(ProductNotFoundError):
        client_returning(404).release(1, 2)


@pytest.mark.parametrize("status", [403, 500, 503])
def test_unexpected_status_is_unavailable(status):
    with pytest.raises(CatalogUnavailableError):
        client_returning(status).reserve(1, 1)


def test_connection_error_is_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=request)

    client = CatalogClient("http://catalog.test", "secret", transport=httpx.MockTransport(handler))
    with pytest.raises(CatalogUnavailableError):
        client.get_product(1)
    client.close()
