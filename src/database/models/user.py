"""Модель пользователя."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import UserRole
from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.order import Order


class User(Base, TimestampMixin):
    """Модель пользователя Telegram бота."""

    __tablename__ = "users"
    __table_args__ = {"comment": "Пользователи Telegram бота"}

    # Первичный ключ - Telegram ID
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
        comment="Telegram ID пользователя",
    )

    # Telegram данные
    username: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Telegram username"
    )
    first_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="Имя пользователя")
    last_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Фамилия пользователя"
    )

    # Контактная информация
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Номер телефона"
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Email")

    # Адрес доставки
    address: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Адрес доставки"
    )

    # Роль пользователя
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserRole.USER.value, comment="Роль пользователя"
    )

    # Язык интерфейса
    language: Mapped[str] = mapped_column(
        String(5), nullable=False, default="ru", comment="Код языка (ru, en)"
    )

    # Статус
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Активен ли пользователь"
    )
    is_blocked: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Заблокирован ли пользователь"
    )

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def is_admin(self) -> bool:
        """Проверка, является ли пользователь администратором."""
        return self.role == UserRole.ADMIN.value

    @property
    def is_moderator(self) -> bool:
        """Проверка, является ли пользователь модератором."""
        return self.role in [UserRole.ADMIN.value, UserRole.MODERATOR.value]
