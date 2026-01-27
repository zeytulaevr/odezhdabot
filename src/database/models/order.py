"""Модель заказа."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.order_message import OrderMessage
    from src.database.models.product import Product
    from src.database.models.user import User


class OrderItem(Base, TimestampMixin):
    """Модель товара в заказе."""

    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_product_id", "product_id"),
        {"comment": "Товары в заказах"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID товара в заказе"
    )

    # ID заказа
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID заказа",
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

    # Цвет товара
    color: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Выбранный цвет товара"
    )

    # Количество товара
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Количество товара"
    )

    # Цена на момент заказа (сохраняем для истории)
    price_at_order: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Цена товара на момент заказа"
    )

    # Название товара на момент заказа (на случай удаления товара)
    product_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Название товара на момент заказа"
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product | None"] = relationship("Product", lazy="selectin")

    @property
    def total_price(self) -> Decimal:
        """Общая стоимость товара (цена * количество)."""
        return self.price_at_order * self.quantity

    @property
    def display_name(self) -> str:
        """Отображаемое имя товара (с размером и цветом)."""
        parts = [self.product_name, f"Размер: {self.size}"]
        if self.color:
            parts.append(f"Цвет: {self.color}")
        return " | ".join(parts)


class Order(Base, TimestampMixin):
    """Модель заказа (может содержать несколько товаров)."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
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

    # Скидка по бонусам
    bonus_discount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), comment="Скидка по бонусам"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="selectin")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    messages: Mapped[list["OrderMessage"]] = relationship(
        "OrderMessage", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def can_be_cancelled(self) -> bool:
        """Можно ли отменить заказ."""
        return self.status in ["new", "processing"]

    @property
    def is_completed(self) -> bool:
        """Завершён ли заказ."""
        return self.status in ["completed", "cancelled"]

    @property
    def subtotal(self) -> Decimal:
        """Стоимость товаров без учета скидок."""
        return sum(item.total_price for item in self.items)

    @property
    def total_price(self) -> Decimal:
        """Общая стоимость заказа с учетом бонусной скидки."""
        return max(self.subtotal - self.bonus_discount, Decimal("0"))

    @property
    def total_items(self) -> int:
        """Общее количество товаров в заказе."""
        return sum(item.quantity for item in self.items)

    @property
    def unread_messages_count(self) -> int:
        """Количество непрочитанных сообщений."""
        return sum(1 for msg in self.messages if not msg.is_read)

    def get_unread_messages_for_user(self, user_id: int) -> int:
        """Получить количество непрочитанных сообщений для конкретного пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Количество непрочитанных сообщений от другого участника
        """
        return sum(
            1 for msg in self.messages
            if not msg.is_read and msg.sender_id != user_id
        )
