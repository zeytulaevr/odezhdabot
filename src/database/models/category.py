"""Модель категории товаров."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.product import Product


class Category(Base):
    """Модель категории товаров в канале Telegram."""

    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_thread_id", "thread_id"),
        Index("ix_categories_is_active", "is_active"),
        {"comment": "Категории товаров в канале"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="ID категории",
    )

    # Название категории
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Название категории"
    )

    # ID ветки в канале Telegram
    thread_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="ID ветки (topic) в канале Telegram"
    )

    # ID сообщения в канале
    channel_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="ID сообщения категории в канале"
    )

    # Статус активности
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Активна ли категория"
    )

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания категории",
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category", lazy="selectin"
    )

    @property
    def products_count(self) -> int:
        """Количество товаров в категории."""
        return len(self.products) if self.products else 0
