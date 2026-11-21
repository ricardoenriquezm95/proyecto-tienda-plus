"""Datos de demostración para el entorno local (SEED_DEMO_DATA=true)."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product

DEMO_PRODUCTS = [
    {"name": "Taza artesanal", "category": "menaje", "price": Decimal("12.50"), "stock": 40},
    {
        "name": "Miel de romero 500 g",
        "category": "alimentacion",
        "price": Decimal("8.90"),
        "stock": 25,
    },
    {
        "name": "Aceite de oliva virgen extra 1 L",
        "category": "alimentacion",
        "price": Decimal("11.20"),
        "stock": 30,
    },
    {
        "name": "Jabón natural de lavanda",
        "category": "cosmetica",
        "price": Decimal("4.75"),
        "stock": 60,
    },
    {"name": "Cesta de mimbre", "category": "hogar", "price": Decimal("24.00"), "stock": 10},
]


def seed_if_empty(db: Session) -> int:
    if db.scalar(select(func.count()).select_from(Product)):
        return 0
    db.add_all(Product(**data) for data in DEMO_PRODUCTS)
    db.commit()
    return len(DEMO_PRODUCTS)
