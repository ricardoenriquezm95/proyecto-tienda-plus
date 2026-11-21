"""Reglas de negocio puras (sin BD ni HTTP): cálculo de importes y máquina de estados.

Estados permitidos (README, sección 1):
    PENDIENTE -> PAGADO -> ENVIADO
    PENDIENTE -> CANCELADO
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

CENT = Decimal("0.01")


class OrderStatus(StrEnum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"
    ENVIADO = "ENVIADO"
    CANCELADO = "CANCELADO"


ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDIENTE: frozenset({OrderStatus.PAGADO, OrderStatus.CANCELADO}),
    OrderStatus.PAGADO: frozenset({OrderStatus.ENVIADO}),
    OrderStatus.ENVIADO: frozenset(),
    OrderStatus.CANCELADO: frozenset(),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: OrderStatus, target: OrderStatus) -> None:
        super().__init__(f"No se puede pasar un pedido de {current} a {target}")
        self.current = current
        self.target = target


def ensure_transition(current: OrderStatus, target: OrderStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(current, target)


def money(value: Decimal) -> Decimal:
    """Redondeo comercial a céntimos (half-up), no el bancario por defecto de Python."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class OrderLine:
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return money(self.unit_price * self.quantity)


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    tax: Decimal
    total: Decimal


def calculate_totals(lines: Iterable[OrderLine], vat_rate: Decimal) -> Totals:
    """Subtotal = suma de subtotales por línea; IVA sobre el subtotal; total = ambos."""
    subtotal = money(sum((line.subtotal for line in lines), Decimal("0")))
    tax = money(subtotal * vat_rate)
    return Totals(subtotal=subtotal, tax=tax, total=subtotal + tax)


def merge_quantities(items: Iterable[tuple[int, int]]) -> dict[int, int]:
    """Agrupa líneas repetidas del mismo producto para reservar una sola vez."""
    merged: dict[int, int] = {}
    for product_id, quantity in items:
        merged[product_id] = merged.get(product_id, 0) + quantity
    return merged
