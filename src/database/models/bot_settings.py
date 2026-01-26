"""Модель настроек бота."""

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, TimestampMixin


class BotSettings(Base, TimestampMixin):
    """Модель настроек бота (все параметры в одном месте)."""

    __tablename__ = "bot_settings"
    __table_args__ = {"comment": "Настройки бота"}

    # Первичный ключ
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="ID настройки"
    )

    # === НАСТРОЙКИ БОНУСНОЙ СИСТЕМЫ ===

    # Процент начисления бонусов за покупку
    bonus_purchase_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default="5.00",
        comment="Процент от суммы заказа, начисляемый в виде бонусов (например, 5.00 = 5%)",
    )

    # Максимальный процент оплаты бонусами
    bonus_max_payment_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default="50.00",
        comment="Максимальный процент от суммы заказа, который можно оплатить бонусами",
    )

    # Минимальная сумма заказа для начисления бонусов
    bonus_min_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="500.00",
        comment="Минимальная сумма заказа для начисления бонусов",
    )

    # Включена ли бонусная система
    bonus_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Включена ли бонусная система",
    )

    # === НАСТРОЙКИ ПЛАТЕЖЕЙ ===

    # Реквизиты для оплаты
    payment_details: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Реквизиты для оплаты (номер карты, счёт и т.д.)"
    )

    # Дополнительная информация об оплате
    payment_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Инструкции по оплате для клиента"
    )

    # Альтернативный контакт для заказов
    alternative_contact_username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Альтернативный контакт для заказов (@username)"
    )

    # === НАСТРОЙКИ ЗАКАЗОВ ===

    # Минимальная сумма заказа
    min_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0.00",
        comment="Минимальная сумма заказа",
    )

    # Максимальное количество товаров в одном заказе
    max_items_per_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="10",
        comment="Максимальное количество разных товаров в одном заказе",
    )

    # Максимальное количество одного товара
    max_quantity_per_item: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="9",
        comment="Максимальное количество одного товара",
    )

    # === НАСТРОЙКИ УВЕДОМЛЕНИЙ ===

    # Текст приветственного сообщения
    welcome_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Текст приветственного сообщения"
    )

    # Текст сообщения помощи
    help_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Текст сообщения помощи"
    )

    # Текст для большого заказа (10+ шт)
    large_order_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Сообщение при попытке заказать 10+ штук одного товара",
    )

    # === НАСТРОЙКИ КАТАЛОГА ===

    # Количество товаров на странице
    products_per_page: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="10",
        comment="Количество товаров на странице каталога",
    )

    # Показывать ли товары без фото
    show_products_without_photos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Показывать ли товары без фото в каталоге",
    )

    @classmethod
    async def get_settings(cls, session):
        """Получить текущие настройки бота.

        Args:
            session: Асинхронная сессия БД

        Returns:
            Настройки бота или настройки по умолчанию
        """
        from sqlalchemy import select

        result = await session.execute(
            select(cls).order_by(cls.created_at.desc()).limit(1)
        )
        settings = result.scalar_one_or_none()

        # Если настроек нет, создаём дефолтные
        if not settings:
            settings = cls()
            session.add(settings)
            await session.flush()

        return settings
