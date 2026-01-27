"""Модель товара."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DECIMAL, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.category import Category
    from src.database.models.order import Order
    from src.database.models.review import Review


class Product(Base, TimestampMixin):
    """Модель товара в магазине."""

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_is_active", "is_active"),
        {"comment": "Товары в магазине"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID товара"
    )

    # Основная информация
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Название товара")

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание товара"
    )

    # Цена
    price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2), nullable=False, comment="Цена товара в рублях"
    )

    # Категория (Foreign Key)
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        comment="ID категории",
    )

    # Доступные размеры (JSONB массив)
    sizes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Доступные размеры товара (массив)",
    )

    # Доступные цвета (JSONB массив)
    colors: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Доступные цвета товара (массив)",
    )

    # Тип кроя
    fit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Тип кроя (например: Regular, Slim, Oversize)",
    )

    # Медиа файлы (фото/видео)
    media: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Медиа файлы товара (до 10 фото/видео): [{type: 'photo'|'video', file_id: '...'}]",
    )

    # Telegram file_id для фото (deprecated, используйте media)
    photo_file_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Telegram file_id фотографии товара (устаревшее)"
    )

    # Статус активности
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Активен ли товар"
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category", back_populates="products", lazy="selectin"
    )


    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="product", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def formatted_price(self) -> str:
        """Форматированная цена с валютой."""
        return f"{self.price:,.2f} ₽"

    @property
    def sizes_list(self) -> list[str]:
        """Список доступных размеров."""
        return self.sizes if isinstance(self.sizes, list) else []

    @property
    def colors_list(self) -> list[str]:
        """Список доступных цветов."""
        return self.colors if isinstance(self.colors, list) else []

    @property
    def media_list(self) -> list[dict[str, Any]]:
        """Список медиа файлов."""
        return self.media if isinstance(self.media, list) else []

    @property
    def has_media(self) -> bool:
        """Есть ли медиа файлы."""
        return len(self.media_list) > 0

    @property
    def primary_media(self) -> dict[str, Any] | None:
        """Первый медиа файл (основное фото/видео)."""
        return self.media_list[0] if self.has_media else None
