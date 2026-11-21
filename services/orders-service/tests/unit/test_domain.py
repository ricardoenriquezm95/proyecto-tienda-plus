from decimal import Decimal

import pytest

from app.domain import (
    InvalidTransitionError,
    OrderLine,
    OrderStatus,
    calculate_totals,
    ensure_transition,
    merge_quantities,
    money,
)

pytestmark = pytest.mark.unit

VAT = Decimal("0.21")


def line(price: str, quantity: int, product_id: int = 1) -> OrderLine:
    return OrderLine(product_id, "x", Decimal(price), quantity)


# --- Cálculo del pedido --------------------------------------------------------------
def test_readme_example_two_mugs():
    """README: 2 tazas de 12,50 € -> subtotal 25,00 + IVA 21 % = 30,25 €."""
    totals = calculate_totals([line("12.50", 2)], VAT)
    assert totals.subtotal == Decimal("25.00")
    assert totals.tax == Decimal("5.25")
    assert totals.total == Decimal("30.25")


def test_totals_with_several_lines():
    totals = calculate_totals([line("12.50", 2), line("8.90", 3, product_id=2)], VAT)
    assert totals.subtotal == Decimal("51.70")
    assert totals.tax == Decimal("10.86")  # 10.857 -> 10.86
    assert totals.total == Decimal("62.56")


def test_line_subtotal():
    assert line("4.75", 3).subtotal == Decimal("14.25")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0.125", "0.13"), ("0.135", "0.14"), ("2.004", "2.00"), ("2.005", "2.01")],
)
def test_money_rounds_half_up(value, expected):
    assert money(Decimal(value)) == Decimal(expected)


def test_totals_with_zero_vat():
    assert calculate_totals([line("10.00", 1)], Decimal("0")).total == Decimal("10.00")


def test_merge_quantities_groups_same_product():
    assert merge_quantities([(1, 2), (2, 1), (1, 3)]) == {1: 5, 2: 1}


# --- Máquina de estados --------------------------------------------------------------
@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.PENDIENTE, OrderStatus.PAGADO),
        (OrderStatus.PENDIENTE, OrderStatus.CANCELADO),
        (OrderStatus.PAGADO, OrderStatus.ENVIADO),
    ],
)
def test_allowed_transitions(current, target):
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.PENDIENTE, OrderStatus.ENVIADO),
        (OrderStatus.PAGADO, OrderStatus.CANCELADO),
        (OrderStatus.PAGADO, OrderStatus.PAGADO),
        (OrderStatus.CANCELADO, OrderStatus.PAGADO),
        (OrderStatus.ENVIADO, OrderStatus.CANCELADO),
    ],
)
def test_forbidden_transitions(current, target):
    with pytest.raises(InvalidTransitionError) as exc_info:
        ensure_transition(current, target)
    assert str(current) in str(exc_info.value)
