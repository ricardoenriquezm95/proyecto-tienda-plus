"""Configuración del servicio leída de variables de entorno (factor III de 12-factor)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.engine import URL


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def database_url_from_env(default_db: str) -> str | URL:
    """Devuelve DATABASE_URL si existe; si no, la construye a partir de DB_* (escapando)."""
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return URL.create(
        drivername=os.getenv("DB_DRIVER", "mssql+pymssql"),
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "1433")),
        database=os.getenv("DB_NAME", default_db),
    )


@dataclass(frozen=True)
class Settings:
    database_url: str | URL
    admin_token: str
    internal_token: str
    catalog_url: str = "http://localhost:8000"
    catalog_timeout_seconds: float = 5.0
    vat_rate: Decimal = Decimal("0.21")
    create_schema: bool = True
    log_level: str = "INFO"
    # Prefijo con el que el API Gateway publica el servicio (p. ej. "/catalog").
    # Solo afecta a las URLs de Swagger/OpenAPI; las rutas de la API no cambian.
    root_path: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        admin_token = os.getenv("ADMIN_TOKEN")
        internal_token = os.getenv("INTERNAL_API_TOKEN")
        if not admin_token or not internal_token:
            raise RuntimeError("Las variables ADMIN_TOKEN e INTERNAL_API_TOKEN son obligatorias")
        return cls(
            database_url=database_url_from_env("orders_db"),
            admin_token=admin_token,
            internal_token=internal_token,
            catalog_url=os.getenv("CATALOG_SERVICE_URL", "http://localhost:8000"),
            catalog_timeout_seconds=float(os.getenv("CATALOG_TIMEOUT_SECONDS", "5")),
            vat_rate=Decimal(os.getenv("VAT_RATE", "0.21")),
            create_schema=_as_bool(os.getenv("CREATE_SCHEMA"), default=True),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            root_path=os.getenv("ROOT_PATH", ""),
        )
