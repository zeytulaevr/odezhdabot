"""Модель пользователя."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import UserRole
from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.cart import Cart
    from src.database.models.order import Order
    from src.database.models.review import Review


class User(Base, TimestampMixin):
    """Модель пользователя Telegram бота."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
        Index("ix_users_role", "role"),
        {"comment": "Пользователи Telegram бота"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID пользователя",
    )

    # Telegram ID пользователя (уникальный)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        comment="Telegram ID пользователя",
    )

    # Telegram данные
    username: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Telegram username"
    )

    # Полное имя из Telegram
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Полное имя пользователя"
    )

    # Контактная информация
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Номер телефона"
    )

    # Роль пользователя: 'user', 'admin', 'super_admin'
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserRole.USER.value, comment="Роль пользователя"
    )

    # Статус блокировки
    is_banned: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Заблокирован ли пользователь"
    )

    # Последняя активность
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
        comment="Дата последней активности пользователя",
    )

    # Баланс бонусов
    bonus_balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
        comment="Баланс бонусов пользователя",
    )

    # Relationships
    cart: Mapped["Cart | None"] = relationship(
        "Cart", back_populates="user", uselist=False, lazy="selectin", cascade="all, delete-orphan"
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        """Проверка, является ли пользователь администратором."""
        return self.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]

    @property
    def is_super_admin(self) -> bool:
        """Проверка, является ли пользователь супер-администратором."""
        return self.role == UserRole.SUPER_ADMIN.value
