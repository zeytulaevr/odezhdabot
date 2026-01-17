"""Модель паттерна спама."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class SpamPattern(Base):
    """Модель паттерна для обнаружения спама."""

    __tablename__ = "spam_patterns"
    __table_args__ = (
        Index("ix_spam_patterns_pattern_type", "pattern_type"),
        Index("ix_spam_patterns_is_active", "is_active"),
        {"comment": "Паттерны для обнаружения спама"},
    )

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID паттерна"
    )

    # Паттерн для поиска
    pattern: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Паттерн для поиска спама"
    )

    # Тип паттерна: 'keyword', 'regex', 'url'
    pattern_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Тип паттерна (keyword, regex, url)"
    )

    # Активен ли паттерн
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, comment="Активен ли паттерн"
    )

    # Дата создания
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Дата создания паттерна",
    )

    @property
    def is_keyword(self) -> bool:
        """Является ли паттерн ключевым словом."""
        return self.pattern_type == "keyword"

    @property
    def is_regex(self) -> bool:
        """Является ли паттерн регулярным выражением."""
        return self.pattern_type == "regex"

    @property
    def is_url(self) -> bool:
        """Является ли паттерн URL паттерном."""
        return self.pattern_type == "url"
