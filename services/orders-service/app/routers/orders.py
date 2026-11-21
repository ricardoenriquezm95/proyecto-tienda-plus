"""Endpoints /api/v1/orders."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app import services
from app.catalog_client import CatalogClient
from app.database import get_db
from app.schemas import OrderCreate, OrderCreated, OrderOut, OrderStatusOut, OrderSummary
from app.security import require_admin

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def get_catalog(request: Request) -> CatalogClient:
    return request.app.state.catalog


DbSession = Annotated[Session, Depends(get_db)]
Catalog = Annotated[CatalogClient, Depends(get_catalog)]

ERR_404 = {404: {"description": "Pedido no encontrado"}}
ERR_409 = {409: {"description": "Transición de estado no permitida"}}


@router.post(
    "/create",
    response_model=OrderCreated,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Stock insuficiente"},
        422: {"description": "Datos no válidos o producto inexistente"},
        503: {"description": "catalog-service no disponible"},
    },
    summary="Crear pedido",
)
def create_order(payload: OrderCreate, request: Request, db: DbSession, catalog: Catalog):
    return services.create_order(db, catalog, payload, request.app.state.settings.vat_rate)


@router.get("", response_model=list[OrderSummary], summary="Pedidos de un cliente")
def list_orders(customer_email: Annotated[EmailStr, Query()], db: DbSession):
    return services.list_orders(db, str(customer_email))


@router.get("/{order_id}", response_model=OrderOut, responses=ERR_404, summary="Consultar pedido")
def get_order(order_id: int, db: DbSession):
    return services.get_order(db, order_id)


@router.post(
    "/{order_id}/pay",
    response_model=OrderStatusOut,
    responses={**ERR_404, **ERR_409},
    summary="Pagar (simulado)",
)
def pay_order(order_id: int, db: DbSession):
    return services.pay_order(db, order_id)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderStatusOut,
    responses={**ERR_404, **ERR_409},
    summary="Cancelar y liberar stock",
)
def cancel_order(order_id: int, db: DbSession, catalog: Catalog):
    return services.cancel_order(db, catalog, order_id)


@router.post(
    "/{order_id}/ship",
    response_model=OrderStatusOut,
    dependencies=[Depends(require_admin)],
    responses={403: {"description": "Token no válido"}, **ERR_404, **ERR_409},
    summary="Marcar como enviado (admin)",
)
def ship_order(order_id: int, db: DbSession):
    return services.ship_order(db, order_id)
