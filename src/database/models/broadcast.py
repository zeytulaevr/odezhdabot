"""Модель рассылки."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
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
        Index("ix_broadcasts_status", "status"),
        {"comment": "Рассылки сообщений"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID рассылки"
    )

    # Текст сообщения рассылки
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст рассылки")

    # Медиа файл (опционально)
    media_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Тип медиа: photo, video, document"
    )

    media_file_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="File ID медиа для Telegram API"
    )

    # Кнопки в сообщении (опционально)
    buttons: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Inline кнопки для сообщения"
    )

    # Статус рассылки
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="Статус: pending, in_progress, completed, failed, cancelled",
    )

    # Фильтры для сегментации (JSONB)
    # Пример: {"all": true, "active_days": 30, "has_orders": true}
    filters: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Фильтры для сегментации аудитории"
    )

    # Статистика
    total_target: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Всего получателей по фильтрам"
    )

    sent_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Успешно отправлено"
    )

    success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Успешно доставлено"
    )

    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Ошибки отправки"
    )

    # Лог ошибок (JSONB)
    error_log: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Логи ошибок отправки"
    )

    # Кто создал рассылку
    created_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID администратора, создавшего рассылку",
    )

    # Даты
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания рассылки",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дата завершения рассылки",
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

    @property
    def is_completed(self) -> bool:
        """Завершена ли рассылка."""
        return self.status in ["completed", "failed", "cancelled"]

    @property
    def has_media(self) -> bool:
        """Есть ли медиа в рассылке."""
        return bool(self.media_type and self.media_file_id)

    @property
    def success_rate(self) -> float:
        """Процент успешных отправок."""
        if self.total_target == 0:
            return 0.0
        return (self.success_count / self.total_target) * 100
