"""Модель настроек платежей."""

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin


class PaymentSettings(Base, TimestampMixin):
    """Модель настроек платежей (реквизиты для оплаты)."""

    __tablename__ = "payment_settings"
    __table_args__ = {"comment": "Настройки платежей и реквизиты"}

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID настройки"
    )

    # Реквизиты для оплаты
    payment_details: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Реквизиты для оплаты (номер карты, счёт и т.д.)"
    )

    # Дополнительная информация об оплате
    payment_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Инструкции по оплате для клиента"
    )

    @classmethod
    async def get_current_settings(cls, session):
        """Получить текущие настройки платежей.

        Args:
            session: Асинхронная сессия БД

        Returns:
            Настройки платежей или None
        """
        from sqlalchemy import select

        result = await session.execute(
            select(cls).order_by(cls.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()
