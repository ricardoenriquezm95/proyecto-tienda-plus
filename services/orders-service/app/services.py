"""Casos de uso de pedidos (C-003 a C-006 y C-008).

La creación de pedidos sigue un patrón *saga* con compensación: se reserva el stock
producto a producto en el catálogo y, si cualquier paso falla (sin stock, producto
inexistente, catálogo caído o error de BD), se liberan las reservas ya hechas y el
pedido se rechaza completo.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.catalog_client import CatalogClient, CatalogError
from app.domain import (
    InvalidTransitionError,
    OrderLine,
    OrderStatus,
    calculate_totals,
    ensure_transition,
    merge_quantities,
)
from app.models import Order, OrderItem, utc_now
from app.schemas import OrderCreate

logger = logging.getLogger(__name__)


class OrderNotFoundError(Exception):
    def __init__(self, order_id: int) -> None:
        super().__init__(f"Pedido {order_id} no encontrado")
        self.order_id = order_id


def _compensate(catalog: CatalogClient, reserved: list[tuple[int, int]]) -> None:
    for product_id, quantity in reversed(reserved):
        try:
            catalog.release(product_id, quantity)
        except CatalogError:
            # Se registra para reconciliación manual; nunca se oculta el error original.
            logger.exception(
                "No se pudo liberar la reserva de %s uds. del producto %s", quantity, product_id
            )


def create_order(
    db: Session, catalog: CatalogClient, payload: OrderCreate, vat_rate: Decimal
) -> Order:
    requested = merge_quantities((item.product_id, item.quantity) for item in payload.items)
    reserved: list[tuple[int, int]] = []
    lines: list[OrderLine] = []
    try:
        for product_id, quantity in requested.items():
            product = catalog.get_product(product_id)
            catalog.reserve(product_id, quantity)
            reserved.append((product_id, quantity))
            lines.append(
                OrderLine(
                    product_id=product_id,
                    product_name=product["name"],
                    unit_price=Decimal(str(product["price"])),
                    quantity=quantity,
                )
            )

        totals = calculate_totals(lines, vat_rate)
        order = Order(
            customer_email=str(payload.customer_email).lower(),
            status=OrderStatus.PENDIENTE.value,
            subtotal=totals.subtotal,
            tax=totals.tax,
            total=totals.total,
            items=[
                OrderItem(
                    product_id=line.product_id,
                    product_name=line.product_name,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    line_subtotal=line.subtotal,
                )
                for line in lines
            ],
        )
        db.add(order)
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        _compensate(catalog, reserved)
        raise
    logger.info("Pedido %s creado (%s €)", order.id, order.total)
    return order


def get_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def list_orders(db: Session, customer_email: str) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.customer_email == customer_email.lower())
        .order_by(Order.id.desc())
    )
    return list(db.scalars(stmt))


def _transition(db: Session, order_id: int, target: OrderStatus) -> Order:
    """Cambia de estado de forma atómica (compare-and-set sobre el estado actual).

    Si dos peticiones intentan, p. ej., cancelar el mismo pedido a la vez, solo una
    actualiza la fila; la otra recibe 409. Así el stock nunca se libera dos veces.
    """
    order = get_order(db, order_id)
    current = OrderStatus(order.status)
    ensure_transition(current, target)
    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == current.value)
        .values(status=target.value, updated_at=utc_now())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        db.rollback()
        db.refresh(order)
        raise InvalidTransitionError(OrderStatus(order.status), target)
    db.commit()
    db.refresh(order)
    return order


def pay_order(db: Session, order_id: int) -> Order:
    """Pago simulado (C-004): no hay pasarela real."""
    return _transition(db, order_id, OrderStatus.PAGADO)


def ship_order(db: Session, order_id: int) -> Order:
    return _transition(db, order_id, OrderStatus.ENVIADO)


def cancel_order(db: Session, catalog: CatalogClient, order_id: int) -> Order:
    """Cancela un pedido pendiente y devuelve su stock al catálogo (C-005).

    Primero se confirma la cancelación y después se libera el stock. Si el catálogo
    falla en ese momento se pierde, como mucho, stock disponible (infraventa) pero
    nunca se libera dos veces (lo que provocaría sobreventa, el riesgo a evitar).
    """
    order = _transition(db, order_id, OrderStatus.CANCELADO)
    _compensate(catalog, [(item.product_id, item.quantity) for item in order.items])
    return order
