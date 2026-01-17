"""Модели заказов и элементов заказа."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import OrderStatus, PaymentStatus
from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.product import Product
    from src.database.models.user import User


class Order(Base, TimestampMixin):
    """Модель заказа."""

    __tablename__ = "orders"
    __table_args__ = {"comment": "Заказы пользователей"}

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ID пользователя
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID пользователя",
    )

    # Статус заказа
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OrderStatus.PENDING.value,
        comment="Статус заказа",
    )

    # Статус оплаты
    payment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING.value,
        comment="Статус оплаты",
    )

    # Сумма заказа
    total_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False, comment="Общая сумма заказа"
    )

    # Информация о доставке
    delivery_address: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Адрес доставки"
    )
    recipient_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Имя получателя"
    )
    recipient_phone: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Телефон получателя"
    )

    # Комментарий к заказу
    comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Комментарий к заказу"
    )

    # Информация об оплате
    payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="ID платежа в платёжной системе"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="selectin")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def formatted_total(self) -> str:
        """Форматированная общая сумма."""
        return f"{self.total_amount:,.2f} ₽"

    @property
    def is_paid(self) -> bool:
        """Проверка, оплачен ли заказ."""
        return self.payment_status == PaymentStatus.SUCCEEDED.value

    @property
    def can_be_cancelled(self) -> bool:
        """Можно ли отменить заказ."""
        return self.status in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]


class OrderItem(Base):
    """Модель элемента заказа (товар в заказе)."""

    __tablename__ = "order_items"
    __table_args__ = {"comment": "Элементы заказов (товары в заказе)"}

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

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

    # Информация о товаре (сохраняется на момент заказа)
    product_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Название товара на момент заказа"
    )
    product_price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False, comment="Цена товара на момент заказа"
    )

    # Количество
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Количество товара"
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items", lazy="selectin")
    product: Mapped["Product | None"] = relationship(
        "Product", back_populates="order_items", lazy="selectin"
    )

    @property
    def total_price(self) -> Decimal:
        """Общая стоимость позиции (цена * количество)."""
        return self.product_price * self.quantity

    @property
    def formatted_total(self) -> str:
        """Форматированная общая стоимость позиции."""
        return f"{self.total_price:,.2f} ₽"
