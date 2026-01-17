"""Модель рассылки."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

# Не используем TYPE_CHECKING т.к. нужно для relationship
from src.database.models.user import User


class Broadcast(Base):
    """Модель рассылки сообщений."""

    __tablename__ = "broadcasts"
    __table_args__ = (
        Index("ix_broadcasts_created_by", "created_by"),
        Index("ix_broadcasts_created_at", "created_at"),
        {"comment": "Рассылки сообщений"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID рассылки"
    )

    # Текст сообщения рассылки
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст рассылки")

    # Количество отправленных сообщений
    sent_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Количество отправленных сообщений"
    )

    # Фильтры для сегментации (JSONB)
    # Пример: {"role": "user", "created_after": "2024-01-01", "has_orders": true}
    filters: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Фильтры для сегментации аудитории"
    )

    # Кто создал рассылку
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID администратора, создавшего рассылку",
    )

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания рассылки",
    )

    # Relationships
    creator: Mapped["User | None"] = relationship("User", lazy="selectin")

    @property
    def has_filters(self) -> bool:
        """Есть ли фильтры для сегментации."""
        return bool(self.filters)

    @property
    def is_sent(self) -> bool:
        """Была ли рассылка отправлена."""
        return self.sent_count > 0
