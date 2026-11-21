"""Acceso a datos y reglas de stock.

La clave del negocio ("vender sin sobrevender") está en ``_apply_delta``: el stock se
modifica con un único UPDATE condicional (compare-and-set)::

    UPDATE products SET stock = stock + :delta
    WHERE id = :id AND stock + :delta >= 0

El motor de BD bloquea la fila durante el UPDATE, de modo que dos reservas concurrentes
nunca pueden leer el mismo stock y dejarlo en negativo. Si no se actualiza ninguna fila,
o el producto no existe o no hay stock suficiente.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Product
from app.schemas import ProductCreate


class ProductNotFoundError(Exception):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"Producto {product_id} no encontrado")
        self.product_id = product_id


class InsufficientStockError(Exception):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"Stock insuficiente para el producto {product_id}")
        self.product_id = product_id


def list_products(db: Session, category: str | None = None) -> list[Product]:
    stmt = select(Product).order_by(Product.id)
    if category:
        stmt = stmt.where(Product.category == category)
    return list(db.scalars(stmt))


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    return product


def create_product(db: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _apply_delta(db: Session, product_id: int, delta: int) -> int:
    stmt = (
        update(Product)
        .where(Product.id == product_id, Product.stock + delta >= 0)
        .values(stock=Product.stock + delta)
        .execution_options(synchronize_session=False)
    )
    result = db.execute(stmt)
    if result.rowcount == 0:
        db.rollback()
        if db.get(Product, product_id) is None:
            raise ProductNotFoundError(product_id)
        raise InsufficientStockError(product_id)
    db.commit()
    return db.scalar(select(Product.stock).where(Product.id == product_id))


def adjust_stock(db: Session, product_id: int, delta: int) -> int:
    return _apply_delta(db, product_id, delta)


def reserve(db: Session, product_id: int, quantity: int) -> int:
    return _apply_delta(db, product_id, -quantity)


def release(db: Session, product_id: int, quantity: int) -> int:
    return _apply_delta(db, product_id, quantity)
