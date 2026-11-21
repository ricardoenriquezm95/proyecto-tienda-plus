"""Configuración del servicio leída de variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.engine import URL


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def database_url_from_env(default_db: str) -> str | URL:
    """Devuelve DATABASE_URL si existe; si no, la construye a partir de DB_*.

    Construirla con ``URL.create`` evita problemas con contraseñas que contienen
    caracteres especiales (@, :, /...), ya que se escapan automáticamente.
    """
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
    create_schema: bool = True
    seed_demo_data: bool = False
    log_level: str = "INFO"
    # Prefijo con el que el API Gateway publica el servicio (p. ej. "/catalog").
    # Solo afecta a las URLs de Swagger/OpenAPI; las rutas de la API no cambian.
    root_path: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        admin_token = os.getenv("ADMIN_TOKEN")
        internal_token = os.getenv("INTERNAL_API_TOKEN")
        if not admin_token or not internal_token:
            # Fail fast: no arrancamos con secretos vacíos.
            raise RuntimeError("Las variables ADMIN_TOKEN e INTERNAL_API_TOKEN son obligatorias")
        return cls(
            database_url=database_url_from_env("catalog_db"),
            admin_token=admin_token,
            internal_token=internal_token,
            create_schema=_as_bool(os.getenv("CREATE_SCHEMA"), default=True),
            seed_demo_data=_as_bool(os.getenv("SEED_DEMO_DATA"), default=False),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            root_path=os.getenv("ROOT_PATH", ""),
        )
