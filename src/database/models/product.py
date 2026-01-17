"""Модель товара."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import ProductCategory
from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.order import OrderItem


class Product(Base, TimestampMixin):
    """Модель товара в магазине."""

    __tablename__ = "products"
    __table_args__ = {"comment": "Товары в магазине"}

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Основная информация
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Название товара")
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание товара"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProductCategory.TSHIRTS.value,
        comment="Категория товара",
    )

    # Цена и наличие
    price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False, comment="Цена товара в рублях"
    )
    stock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Количество на складе"
    )

    # Характеристики
    size: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="Размер (XS, S, M, L, XL, XXL)"
    )
    color: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Цвет")
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Бренд")

    # Изображения
    image_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL главного изображения"
    )

    # Статус
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Активен ли товар (показывается в каталоге)"
    )
    is_featured: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Рекомендуемый товар"
    )

    # Метаданные
    sku: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, comment="Артикул товара"
    )

    # Relationships
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="product", lazy="selectin"
    )

    @property
    def is_available(self) -> bool:
        """Проверка доступности товара для покупки."""
        return self.is_active and self.stock > 0

    @property
    def formatted_price(self) -> str:
        """Форматированная цена с валютой."""
        return f"{self.price:,.2f} ₽"

    def decrease_stock(self, quantity: int) -> None:
        """Уменьшить количество товара на складе."""
        if quantity > self.stock:
            raise ValueError(f"Недостаточно товара на складе. Доступно: {self.stock}")
        self.stock -= quantity

    def increase_stock(self, quantity: int) -> None:
        """Увеличить количество товара на складе."""
        self.stock += quantity
