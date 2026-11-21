"""Endpoints /api/v1/products."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import repository
from app.database import get_db
from app.schemas import ProductCreate, ProductOut, QuantityRequest, StockAdjust, StockOut
from app.security import require_admin, require_internal

router = APIRouter(prefix="/api/v1/products", tags=["products"])

DbSession = Annotated[Session, Depends(get_db)]

ERR_404 = {404: {"description": "Producto no encontrado"}}
ERR_409 = {409: {"description": "Stock insuficiente"}}
ERR_403 = {403: {"description": "Token no válido"}}


@router.get("/list", response_model=list[ProductOut], summary="Listar productos")
def list_products(
    db: DbSession,
    category: Annotated[
        str | None, Query(max_length=60, description="Filtrar por categoría")
    ] = None,
):
    return repository.list_products(db, category)


@router.get("/{product_id}", response_model=ProductOut, responses=ERR_404, summary="Detalle")
def get_product(product_id: int, db: DbSession):
    return repository.get_product(db, product_id)


@router.post(
    "/create",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    responses=ERR_403,
    summary="Crear producto (admin)",
)
def create_product(payload: ProductCreate, db: DbSession):
    return repository.create_product(db, payload)


@router.patch(
    "/{product_id}/stock",
    response_model=StockOut,
    dependencies=[Depends(require_admin)],
    responses={**ERR_403, **ERR_404, **ERR_409},
    summary="Ajustar stock (admin)",
)
def adjust_stock(product_id: int, payload: StockAdjust, db: DbSession):
    stock = repository.adjust_stock(db, product_id, payload.delta)
    return StockOut(id=product_id, stock=stock)


@router.post(
    "/{product_id}/reserve",
    response_model=StockOut,
    dependencies=[Depends(require_internal)],
    responses={**ERR_403, **ERR_404, **ERR_409},
    summary="Reservar unidades (uso interno)",
)
def reserve(product_id: int, payload: QuantityRequest, db: DbSession):
    stock = repository.reserve(db, product_id, payload.quantity)
    return StockOut(id=product_id, stock=stock)


@router.post(
    "/{product_id}/release",
    response_model=StockOut,
    dependencies=[Depends(require_internal)],
    responses={**ERR_403, **ERR_404},
    summary="Liberar unidades (uso interno)",
)
def release(product_id: int, payload: QuantityRequest, db: DbSession):
    stock = repository.release(db, product_id, payload.quantity)
    return StockOut(id=product_id, stock=stock)
