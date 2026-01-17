"""Модель заказа."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.product import Product
    from src.database.models.user import User


class Order(Base, TimestampMixin):
    """Модель заказа (один товар = один заказ)."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_product_id", "product_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
        {"comment": "Заказы пользователей"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID заказа"
    )

    # ID пользователя
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID пользователя",
    )

    # ID товара
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID товара",
    )

    # Размер товара
    size: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="Размер товара (XS, S, M, L, XL, XXL)"
    )

    # Статус заказа: 'new', 'processing', 'paid', 'shipped', 'completed', 'cancelled'
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="new",
        comment="Статус заказа",
    )

    # Контактная информация клиента
    customer_contact: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Контактные данные клиента (телефон, адрес)"
    )

    # Заметки администратора
    admin_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Заметки администратора по заказу"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="selectin")

    product: Mapped["Product | None"] = relationship(
        "Product", back_populates="orders", lazy="selectin"
    )

    @property
    def can_be_cancelled(self) -> bool:
        """Можно ли отменить заказ."""
        return self.status in ["new", "processing"]

    @property
    def is_completed(self) -> bool:
        """Завершён ли заказ."""
        return self.status in ["completed", "cancelled"]
