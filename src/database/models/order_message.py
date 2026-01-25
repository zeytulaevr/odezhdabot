"""Модель сообщения в рамках заказа."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.order import Order
    from src.database.models.user import User


class OrderMessage(Base, TimestampMixin):
    """Модель сообщения в чате заказа (переписка админа с клиентом)."""

    __tablename__ = "order_messages"
    __table_args__ = (
        Index("ix_order_messages_order_id", "order_id"),
        Index("ix_order_messages_sender_id", "sender_id"),
        Index("ix_order_messages_created_at", "created_at"),
        {"comment": "Сообщения в рамках заказов (чат с клиентом)"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID сообщения"
    )

    # ID заказа
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID заказа",
    )

    # ID отправителя (может быть как клиент, так и админ)
    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID отправителя сообщения",
    )

    # Текст сообщения
    message_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Текст сообщения"
    )

    # Прочитано ли сообщение
    is_read: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Прочитано ли сообщение"
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="messages")
    sender: Mapped["User"] = relationship("User", lazy="selectin")

    @property
    def is_from_admin(self) -> bool:
        """Отправлено ли сообщение от админа."""
        return self.sender.is_admin or self.sender.is_superadmin
