import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ADMIN_TOKEN = "test-admin-token"
INTERNAL_TOKEN = "test-internal-token"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        admin_token=ADMIN_TOKEN,
        internal_token=INTERNAL_TOKEN,
    )


@pytest.fixture
def client(settings: Settings):
    # El context manager ejecuta el lifespan (creación de tablas) y cada test
    # obtiene una BD en memoria nueva y aislada.
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


@pytest.fixture
def internal_headers() -> dict[str, str]:
    return {"X-Internal-Token": INTERNAL_TOKEN}


@pytest.fixture
def make_product(client, admin_headers):
    def _make(name="Taza", price=12.5, stock=40, category="menaje") -> dict:
        response = client.post(
            "/api/v1/products/create",
            json={"name": name, "price": price, "stock": stock, "category": category},
            headers=admin_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make
