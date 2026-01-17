"""Модель отзыва на товар."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.database.models.product import Product
    from src.database.models.user import User


class Review(Base):
    """Модель отзыва на товар."""

    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_product_id", "product_id"),
        Index("ix_reviews_moderation_status", "moderation_status"),
        Index("ix_reviews_created_at", "created_at"),
        {"comment": "Отзывы на товары"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID отзыва"
    )

    # ID пользователя
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID пользователя",
    )

    # ID товара
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID товара",
    )

    # Текст отзыва
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст отзыва")

    # Одобрен ли отзыв
    is_approved: Mapped[bool] = mapped_column(
        nullable=False, default=False, comment="Одобрен ли отзыв для публикации"
    )

    # Статус модерации: 'pending', 'approved', 'rejected', 'flagged'
    moderation_status: Mapped[str] = mapped_column(
        nullable=False, default="pending", comment="Статус модерации"
    )

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания отзыва",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reviews", lazy="selectin")

    product: Mapped["Product"] = relationship("Product", back_populates="reviews", lazy="selectin")

    @property
    def is_pending(self) -> bool:
        """Находится ли отзыв на модерации."""
        return self.moderation_status == "pending"

    @property
    def is_rejected(self) -> bool:
        """Отклонён ли отзыв."""
        return self.moderation_status == "rejected"

    @property
    def is_flagged(self) -> bool:
        """Отмечен ли отзыв как подозрительный."""
        return self.moderation_status == "flagged"
