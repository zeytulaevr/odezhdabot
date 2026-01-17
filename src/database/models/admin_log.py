"""Модель лога действий администратора."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

# Не используем TYPE_CHECKING т.к. нужно для relationship
from src.database.models.user import User


class AdminLog(Base):
    """Модель лога действий администратора."""

    __tablename__ = "admin_logs"
    __table_args__ = (
        Index("ix_admin_logs_admin_id", "admin_id"),
        Index("ix_admin_logs_action", "action"),
        Index("ix_admin_logs_created_at", "created_at"),
        {"comment": "Логи действий администраторов"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID лога"
    )

    # ID администратора
    admin_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID администратора",
    )

    # Действие
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Название действия"
    )

    # Детали действия (JSONB)
    # Пример: {"order_id": 123, "old_status": "new", "new_status": "processing"}
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Детали действия в формате JSON"
    )

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата и время действия",
    )

    # Relationships
    admin: Mapped["User | None"] = relationship("User", lazy="selectin")

    @property
    def has_details(self) -> bool:
        """Есть ли детали действия."""
        return bool(self.details)
