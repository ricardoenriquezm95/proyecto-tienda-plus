import pytest
from sqlalchemy.engine import URL

from app.config import Settings, database_url_from_env

pytestmark = pytest.mark.unit


def test_settings_require_secrets(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        Settings.from_env()


def test_database_url_is_built_and_escapes_password(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "catalog_user")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:w/rd")
    monkeypatch.setenv("DB_HOST", "mssql")
    url = database_url_from_env("catalog_db")
    assert isinstance(url, URL)
    assert url.drivername == "mssql+pymssql"
    assert url.password == "p@ss:w/rd"
    assert url.database == "catalog_db"
    assert "p%40ss" in url.render_as_string(hide_password=False)


def test_explicit_database_url_wins(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    assert database_url_from_env("catalog_db") == "sqlite+pysqlite:///:memory:"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "a")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "b")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    monkeypatch.setenv("ROOT_PATH", "/catalog")
    settings = Settings.from_env()
    assert settings.seed_demo_data is True
    assert settings.root_path == "/catalog"
    assert settings.create_schema is True
