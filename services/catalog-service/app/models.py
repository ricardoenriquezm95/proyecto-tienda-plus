"""Modelo de persistencia del catálogo."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, Integer, Numeric, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        # Última línea de defensa contra la sobreventa: la BD nunca acepta stock negativo.
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(120), nullable=False)
    category: Mapped[str] = mapped_column(Unicode(60), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
