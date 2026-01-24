"""Модели корзины покупок."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.product import Product
    from src.database.models.user import User


class Cart(Base, TimestampMixin):
    """Корзина пользователя."""

    __tablename__ = "carts"
    __table_args__ = (
        Index("ix_carts_user_id", "user_id"),
        {"comment": "Корзины пользователей"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID корзины"
    )

    # ID пользователя
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # У пользователя только одна активная корзина
        comment="ID пользователя",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cart", lazy="selectin")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def total_items(self) -> int:
        """Общее количество товаров в корзине."""
        return sum(item.quantity for item in self.items)

    @property
    def is_empty(self) -> bool:
        """Пуста ли корзина."""
        return len(self.items) == 0


class CartItem(Base, TimestampMixin):
    """Товар в корзине."""

    __tablename__ = "cart_items"
    __table_args__ = (
        Index("ix_cart_items_cart_id", "cart_id"),
        Index("ix_cart_items_product_id", "product_id"),
        {"comment": "Товары в корзинах"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID записи"
    )

    # ID корзины
    cart_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID корзины",
    )

    # ID товара
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID товара",
    )

    # Размер товара
    size: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="Размер товара (XS, S, M, L, XL, XXL)"
    )

    # Цвет товара
    color: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Выбранный цвет товара"
    )

    # Количество
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Количество товара"
    )

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")

    @property
    def display_name(self) -> str:
        """Полное название товара для отображения."""
        parts = [self.product.name if self.product else "Товар"]
        if self.color:
            parts.append(f"({self.color})")
        parts.append(f"[{self.size.upper()}]")
        return " ".join(parts)
