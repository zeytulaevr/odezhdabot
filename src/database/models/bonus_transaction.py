"""Модель транзакции бонусов."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.order import Order
    from src.database.models.promocode import Promocode
    from src.database.models.user import User


class BonusTransaction(Base, TimestampMixin):
    """Модель транзакции бонусов (начисление/списание)."""

    __tablename__ = "bonus_transactions"
    __table_args__ = (
        Index("ix_bonus_transactions_user_id", "user_id"),
        Index("ix_bonus_transactions_transaction_type", "transaction_type"),
        Index("ix_bonus_transactions_created_at", "created_at"),
        {"comment": "История транзакций бонусов"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID транзакции"
    )

    # ID пользователя
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID пользователя",
    )

    # Сумма транзакции (положительная для начисления, отрицательная для списания)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Сумма бонусов (+начисление, -списание)"
    )

    # Баланс после транзакции
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Баланс бонусов после транзакции"
    )

    # Тип транзакции
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Тип транзакции: purchase, admin_grant, promocode, order_discount, admin_deduct",
    )

    # Описание транзакции
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание транзакции"
    )

    # Связанный заказ (если транзакция связана с заказом)
    order_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID связанного заказа",
    )

    # Связанный промокод (если транзакция по промокоду)
    promocode_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("promocodes.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID использованного промокода",
    )

    # ID администратора, выполнившего операцию (для admin_grant и admin_deduct)
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID администратора, выполнившего операцию",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    order: Mapped["Order | None"] = relationship("Order", lazy="selectin")
    promocode: Mapped["Promocode | None"] = relationship("Promocode", lazy="selectin")
    admin: Mapped["User | None"] = relationship("User", foreign_keys=[admin_id], lazy="selectin")

    @property
    def is_debit(self) -> bool:
        """Является ли транзакция начислением."""
        return self.amount > 0

    @property
    def is_credit(self) -> bool:
        """Является ли транзакция списанием."""
        return self.amount < 0

    @property
    def formatted_amount(self) -> str:
        """Отформатированная сумма с знаком."""
        sign = "+" if self.amount > 0 else ""
        return f"{sign}{self.amount:,.2f}"
