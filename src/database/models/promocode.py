"""Модель промокода."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.user import User


class Promocode(Base, TimestampMixin):
    """Модель промокода для начисления бонусов."""

    __tablename__ = "promocodes"
    __table_args__ = (
        Index("ix_promocodes_code", "code", unique=True),
        Index("ix_promocodes_is_active", "is_active"),
        Index("ix_promocodes_promocode_type", "promocode_type"),
        {"comment": "Промокоды для начисления бонусов"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID промокода"
    )

    # Уникальный код промокода
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="Уникальный код промокода"
    )

    # Количество бонусов для начисления
    bonus_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Количество бонусов для начисления"
    )

    # Тип промокода: personal (для конкретного пользователя) или public (для всех)
    promocode_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="public",
        comment="Тип промокода: personal или public",
    )

    # ID пользователя для персонального промокода
    target_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        comment="ID пользователя для персонального промокода",
    )

    # Максимальное количество активаций (для публичных промокодов)
    max_activations: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Максимальное количество активаций (null = неограничено)"
    )

    # Счётчик активаций
    activations_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="Количество активаций"
    )

    # Дата истечения промокода
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Дата истечения промокода"
    )

    # Активен ли промокод
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Активен ли промокод"
    )

    # Описание промокода (для администратора)
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание промокода"
    )

    # ID создателя промокода
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID администратора, создавшего промокод",
    )

    # Relationships
    target_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[target_user_id], lazy="selectin"
    )
    creator: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by], lazy="selectin"
    )

    @property
    def is_expired(self) -> bool:
        """Истёк ли промокод."""
        if not self.expires_at:
            return False
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used_up(self) -> bool:
        """Исчерпан ли лимит активаций."""
        if not self.max_activations:
            return False
        return self.activations_count >= self.max_activations

    @property
    def can_be_activated(self) -> bool:
        """Можно ли активировать промокод."""
        return self.is_active and not self.is_expired and not self.is_used_up

    @property
    def remaining_activations(self) -> int | None:
        """Оставшееся количество активаций."""
        if not self.max_activations:
            return None
        return max(0, self.max_activations - self.activations_count)

    def can_be_activated_by_user(self, user_id: int) -> bool:
        """Может ли конкретный пользователь активировать промокод.

        Args:
            user_id: ID пользователя

        Returns:
            True если может активировать
        """
        if not self.can_be_activated:
            return False

        # Для персональных промокодов проверяем совпадение user_id
        if self.promocode_type == "personal":
            return self.target_user_id == user_id

        return True
