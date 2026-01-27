"""Модель настроек бонусной системы."""

from decimal import Decimal

from sqlalchemy import Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin


class BonusSettings(Base, TimestampMixin):
    """Модель настроек бонусной системы."""

    __tablename__ = "bonus_settings"
    __table_args__ = {"comment": "Настройки бонусной системы"}

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID настройки"
    )

    # Процент начисления бонусов за покупку
    purchase_bonus_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default="5.00",
        comment="Процент от суммы заказа, начисляемый в виде бонусов (например, 5.00 = 5%)",
    )

    # Максимальный процент оплаты бонусами
    max_bonus_payment_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default="50.00",
        comment="Максимальный процент от суммы заказа, который можно оплатить бонусами (например, 50.00 = 50%)",
    )

    # Минимальная сумма заказа для начисления бонусов
    min_order_amount_for_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="500.00",
        comment="Минимальная сумма заказа для начисления бонусов",
    )

    @classmethod
    async def get_current_settings(cls, session):
        """Получить текущие настройки бонусной системы.

        Args:
            session: Асинхронная сессия БД

        Returns:
            Настройки бонусной системы или настройки по умолчанию
        """
        from sqlalchemy import select

        result = await session.execute(
            select(cls).order_by(cls.created_at.desc()).limit(1)
        )
        settings = result.scalar_one_or_none()

        # Если настроек нет, создаём дефолтные
        if not settings:
            settings = cls(
                purchase_bonus_percent=Decimal("5.00"),
                max_bonus_payment_percent=Decimal("50.00"),
                min_order_amount_for_bonus=Decimal("500.00"),
            )
            session.add(settings)
            await session.flush()

        return settings
