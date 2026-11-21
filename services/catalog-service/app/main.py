"""Punto de entrada del catalog-service.

Se arranca con ``uvicorn app.main:create_app --factory`` para que la configuración se lea
al iniciar el proceso (y no al importar el módulo), lo que facilita los tests.
"""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app import __version__, models  # noqa: F401  (models registra las tablas en Base)
from app.config import Settings
from app.database import build_engine, get_db, init_schema
from app.repository import InsufficientStockError, ProductNotFoundError
from app.routers import products
from app.schemas import HealthOut
from app.security import require_admin
from app.seed import seed_if_empty

SERVICE_NAME = "catalog-service"
logger = logging.getLogger(SERVICE_NAME)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    engine = build_engine(settings.database_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.create_schema:
            init_schema(engine)
        if settings.seed_demo_data:
            with session_factory() as db:
                inserted = seed_if_empty(db)
                if inserted:
                    logger.info("Insertados %s productos de demostración", inserted)
        yield
        engine.dispose()

    app = FastAPI(
        title="Tienda+ · catalog-service",
        version=__version__,
        description="Catálogo de productos y control de stock sin sobreventa.",
        lifespan=lifespan,
        root_path=settings.root_path,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory

    # --- Errores con formato homogéneo { "detail": "..." } --------------------------
    @app.exception_handler(ProductNotFoundError)
    async def _not_found(_: Request, exc: ProductNotFoundError):
        return JSONResponse(status_code=404, content={"detail": "Producto no encontrado"})

    @app.exception_handler(InsufficientStockError)
    async def _no_stock(_: Request, exc: InsufficientStockError):
        return JSONResponse(status_code=409, content={"detail": "Stock insuficiente"})

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Datos de entrada no válidos",
                "errors": jsonable_encoder(exc.errors()),
            },
        )

    app.include_router(products.router)

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
