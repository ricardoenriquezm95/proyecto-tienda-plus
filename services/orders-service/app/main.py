"""Punto de entrada del orders-service (``uvicorn app.main:create_app --factory``)."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app import __version__, models  # noqa: F401  (models registra las tablas en Base)
from app.catalog_client import (
    CatalogClient,
    CatalogUnavailableError,
    InsufficientStockError,
    ProductNotFoundError,
)
from app.config import Settings
from app.database import build_engine, get_db, init_schema
from app.domain import InvalidTransitionError
from app.routers import orders
from app.schemas import HealthOut
from app.security import require_admin
from app.services import OrderNotFoundError

SERVICE_NAME = "orders-service"
logger = logging.getLogger(SERVICE_NAME)


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def create_app(
    settings: Settings | None = None, catalog_transport: httpx.BaseTransport | None = None
) -> FastAPI:
    """``catalog_transport`` permite inyectar un catálogo simulado en los tests."""
    settings = settings or Settings.from_env()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    engine = build_engine(settings.database_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.create_schema:
            init_schema(engine)
        app.state.catalog = CatalogClient(
            settings.catalog_url,
            settings.internal_token,
            timeout=settings.catalog_timeout_seconds,
            transport=catalog_transport,
        )
        yield
        app.state.catalog.close()
        engine.dispose()

    app = FastAPI(
        title="Tienda+ · orders-service",
        version=__version__,
        description="Pedidos con reserva de stock, cálculo de IVA y ciclo de estados.",
        lifespan=lifespan,
        root_path=settings.root_path,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory

    # --- Errores con formato homogéneo { "detail": "..." } --------------------------
    @app.exception_handler(OrderNotFoundError)
    async def _order_not_found(_: Request, exc: OrderNotFoundError):
        return _error(404, "Pedido no encontrado")

    @app.exception_handler(InvalidTransitionError)
    async def _invalid_transition(_: Request, exc: InvalidTransitionError):
        return _error(409, str(exc))

    @app.exception_handler(InsufficientStockError)
    async def _no_stock(_: Request, exc: InsufficientStockError):
        return _error(409, f"Stock insuficiente para el producto {exc.product_id}")

    @app.exception_handler(ProductNotFoundError)
    async def _unknown_product(_: Request, exc: ProductNotFoundError):
        return _error(422, str(exc))

    @app.exception_handler(CatalogUnavailableError)
    async def _catalog_down(_: Request, exc: CatalogUnavailableError):
        logger.error("Error con catalog-service: %s", exc)
        return _error(503, "Servicio de catálogo no disponible, inténtelo más tarde")

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Datos de entrada no válidos",
                "errors": jsonable_encoder(exc.errors()),
            },
        )

    app.include_router(orders.router)

    # --- Salud -------------------------------------------------------------------------
    @app.get(
        "/health/live", response_model=HealthOut, response_model_exclude_none=True, tags=["health"]
    )
    def liveness():
        """Sonda de vida sin autenticación (HEALTHCHECK de Docker / probes de Azure)."""
        return HealthOut(status="ok")

    @app.get(
        "/health",
        response_model=HealthOut,
        response_model_exclude_none=True,
        tags=["health"],
        dependencies=[Depends(require_admin)],
        responses={403: {"description": "Token no válido"}},
    )
    def health(db: Annotated[Session, Depends(get_db)]):
        """Estado completo del servicio, incluida la conexión a BD (admin)."""
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Base de datos no disponible",
            ) from exc
        return HealthOut(status="ok", service=SERVICE_NAME, version=__version__)

    return app
