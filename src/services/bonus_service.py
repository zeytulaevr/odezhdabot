"""Сервис для работы с бонусами."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.bot_settings import BotSettings
from src.database.models.bonus_transaction import BonusTransaction
from src.database.models.order import Order
from src.database.models.promocode import Promocode
from src.database.models.user import User

logger = get_logger(__name__)


class BonusService:
    """Сервис для управления бонусами."""

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: Асинхронная сессия БД
        """
        self.session = session

    async def get_user_bonus_balance(self, user_id: int) -> Decimal:
        """Получить баланс бонусов пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Баланс бонусов
        """
        result = await self.session.execute(
            select(User.bonus_balance).where(User.id == user_id)
        )
        balance = result.scalar_one_or_none()
        return balance or Decimal("0")

    async def add_bonuses(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: str,
        description: str | None = None,
        order_id: int | None = None,
        promocode_id: int | None = None,
        admin_id: int | None = None,
    ) -> BonusTransaction:
        """Начислить бонусы пользователю.

        Args:
            user_id: ID пользователя
            amount: Сумма бонусов для начисления
            transaction_type: Тип транзакции
            description: Описание транзакции
            order_id: ID связанного заказа
            promocode_id: ID промокода
            admin_id: ID администратора

        Returns:
            Созданная транзакция
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Получаем пользователя
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Увеличиваем баланс
        user.bonus_balance += amount
        new_balance = user.bonus_balance

        # Создаём транзакцию
        transaction = BonusTransaction(
            user_id=user_id,
            amount=amount,
            balance_after=new_balance,
            transaction_type=transaction_type,
            description=description,
            order_id=order_id,
            promocode_id=promocode_id,
            admin_id=admin_id,
        )

        self.session.add(transaction)
        await self.session.flush()

        logger.info(
            "Bonuses added",
            user_id=user_id,
            amount=float(amount),
            new_balance=float(new_balance),
            transaction_type=transaction_type,
        )

        return transaction

    async def deduct_bonuses(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: str,
        description: str | None = None,
        order_id: int | None = None,
        admin_id: int | None = None,
    ) -> BonusTransaction:
        """Списать бонусы у пользователя.

        Args:
            user_id: ID пользователя
            amount: Сумма бонусов для списания
            transaction_type: Тип транзакции
            description: Описание транзакции
            order_id: ID связанного заказа
            admin_id: ID администратора

        Returns:
            Созданная транзакция

        Raises:
            ValueError: Если недостаточно бонусов
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Получаем пользователя
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # Проверяем достаточность средств
        if user.bonus_balance < amount:
            raise ValueError(
                f"Insufficient bonus balance. Available: {user.bonus_balance}, required: {amount}"
            )

        # Уменьшаем баланс
        user.bonus_balance -= amount
        new_balance = user.bonus_balance

        # Создаём транзакцию (отрицательная сумма для списания)
        transaction = BonusTransaction(
            user_id=user_id,
            amount=-amount,  # Отрицательное значение для списания
            balance_after=new_balance,
            transaction_type=transaction_type,
            description=description,
            order_id=order_id,
            admin_id=admin_id,
        )

        self.session.add(transaction)
        await self.session.flush()

        logger.info(
            "Bonuses deducted",
            user_id=user_id,
            amount=float(amount),
            new_balance=float(new_balance),
            transaction_type=transaction_type,
        )

        return transaction

    async def activate_promocode(
        self, user_id: int, code: str
    ) -> tuple[BonusTransaction, Promocode]:
        """Активировать промокод.

        Args:
            user_id: ID пользователя
            code: Код промокода

        Returns:
            Кортеж (транзакция, промокод)

        Raises:
            ValueError: Если промокод недействителен
        """
        # Получаем промокод
        result = await self.session.execute(
            select(Promocode).where(Promocode.code == code.upper())
        )
        promocode = result.scalar_one_or_none()

        if not promocode:
            raise ValueError("Промокод не найден")

        if not promocode.can_be_activated:
            if promocode.is_expired:
                raise ValueError("Срок действия промокода истёк")
            if promocode.is_used_up:
                raise ValueError("Промокод уже использован максимальное количество раз")
            if not promocode.is_active:
                raise ValueError("Промокод неактивен")

        if not promocode.can_be_activated_by_user(user_id):
            raise ValueError("Этот промокод недоступен для вас")

        # Проверяем, не использовал ли уже пользователь этот промокод
        existing = await self.session.execute(
            select(BonusTransaction).where(
                BonusTransaction.user_id == user_id,
                BonusTransaction.promocode_id == promocode.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Вы уже использовали этот промокод")

        # Начисляем бонусы
        transaction = await self.add_bonuses(
            user_id=user_id,
            amount=promocode.bonus_amount,
            transaction_type="promocode",
            description=f"Активация промокода {promocode.code}",
            promocode_id=promocode.id,
        )

        # Увеличиваем счётчик активаций
        promocode.activations_count += 1
        await self.session.flush()

        logger.info(
            "Promocode activated",
            user_id=user_id,
            promocode_id=promocode.id,
            code=promocode.code,
            bonus_amount=float(promocode.bonus_amount),
        )

        return transaction, promocode

    async def calculate_purchase_bonus(self, order_amount: Decimal) -> Decimal:
        """Рассчитать бонусы за покупку.

        Args:
            order_amount: Сумма заказа

        Returns:
            Сумма бонусов для начисления
        """
        settings = await BotSettings.get_settings(self.session)

        # Проверяем минимальную сумму заказа
        if order_amount < settings.bonus_min_order_amount:
            return Decimal("0")

        # Рассчитываем бонусы
        bonus_amount = (order_amount * settings.bonus_purchase_percent) / Decimal("100")

        # Округляем до 2 знаков после запятой
        return bonus_amount.quantize(Decimal("0.01"))

    async def accrue_purchase_bonus(
        self, user_id: int, order_id: int, order_amount: Decimal
    ) -> BonusTransaction | None:
        """Начислить бонусы за покупку.

        Args:
            user_id: ID пользователя
            order_id: ID заказа
            order_amount: Сумма заказа

        Returns:
            Транзакция или None если бонусы не начислены
        """
        bonus_amount = await self.calculate_purchase_bonus(order_amount)

        if bonus_amount <= 0:
            return None

        transaction = await self.add_bonuses(
            user_id=user_id,
            amount=bonus_amount,
            transaction_type="purchase",
            description=f"Начисление за заказ #{order_id}",
            order_id=order_id,
        )

        return transaction

    async def get_user_transactions(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[BonusTransaction]:
        """Получить историю транзакций пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список транзакций
        """
        result = await self.session.execute(
            select(BonusTransaction)
            .where(BonusTransaction.user_id == user_id)
            .order_by(BonusTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def calculate_max_bonus_discount(self, order_amount: Decimal) -> Decimal:
        """Рассчитать максимальную скидку бонусами для заказа.

        Args:
            order_amount: Сумма заказа

        Returns:
            Максимальная сумма бонусов, которую можно использовать
        """
        settings = await BotSettings.get_settings(self.session)

        max_discount = (order_amount * settings.bonus_max_payment_percent) / Decimal("100")

        return max_discount.quantize(Decimal("0.01"))
