"""Модель модерируемого сообщения из канала."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.user import User


class ModeratedMessage(Base):
    """Модель сообщения, прошедшего модерацию."""

    __tablename__ = "moderated_messages"
    __table_args__ = (
        Index("ix_moderated_messages_user_id", "user_id"),
        Index("ix_moderated_messages_status", "status"),
        Index("ix_moderated_messages_spam_score", "spam_score"),
        Index("ix_moderated_messages_created_at", "created_at"),
        {"comment": "История модерации сообщений из канала"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID записи"
    )

    # ID пользователя, отправившего сообщение
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID пользователя",
    )

    # Telegram ID сообщения
    message_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Telegram ID сообщения"
    )

    # Telegram ID канала/чата
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="Telegram ID чата"
    )

    # ID ветки (thread_id)
    thread_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="ID ветки в канале"
    )

    # Текст сообщения
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст сообщения")

    # Статус модерации: 'pending', 'approved', 'rejected', 'auto_approved', 'auto_rejected'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="Статус модерации"
    )

    # Оценка спама (0-100)
    spam_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Оценка спама (0-100)"
    )

    # Причины подозрений (JSON список найденных паттернов)
    spam_reasons: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Причины подозрений в спаме (JSON)"
    )

    # ID администратора, который проверил (если проверял вручную)
    moderator_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID модератора",
    )

    # Комментарий модератора
    moderator_comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Комментарий модератора"
    )

    # Дата создания сообщения
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания сообщения",
    )

    # Дата модерации
    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Дата модерации"
    )

    # Удалено ли сообщение
    is_deleted: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Удалено ли сообщение"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], lazy="selectin"
    )

    moderator: Mapped["User"] = relationship(
        "User", foreign_keys=[moderator_id], lazy="selectin"
    )

    @property
    def is_pending(self) -> bool:
        """Ожидает ли сообщение проверки."""
        return self.status == "pending"

    @property
    def is_approved(self) -> bool:
        """Одобрено ли сообщение."""
        return self.status in ["approved", "auto_approved"]

    @property
    def is_rejected(self) -> bool:
        """Отклонено ли сообщение."""
        return self.status in ["rejected", "auto_rejected"]

    @property
    def is_high_spam(self) -> bool:
        """Высокая ли вероятность спама."""
        return self.spam_score >= 90

    @property
    def is_suspicious(self) -> bool:
        """Подозрительное ли сообщение."""
        return 50 <= self.spam_score < 90
