"""Motor de base de datos, sesión por petición e inicialización del esquema."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def build_engine(url: str | URL) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        # Usado solo en tests: BD en memoria compartida entre hilos.
        return create_engine(
            parsed, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    return create_engine(
        parsed,
        pool_pre_ping=True,  # detecta conexiones caídas (Azure SQL cierra las inactivas)
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
    )


def init_schema(engine: Engine, retries: int = 10, delay_seconds: float = 3.0) -> None:
    """Crea las tablas si no existen, reintentando mientras la BD arranca."""
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(engine)
            return
        except OperationalError:
            if attempt == retries:
                raise
            logger.warning("BD no disponible (intento %s/%s); reintentando...", attempt, retries)
            time.sleep(delay_seconds)


def get_db(request: Request) -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición, cerrada siempre al terminar."""
    with request.app.state.session_factory() as session:
        yield session
