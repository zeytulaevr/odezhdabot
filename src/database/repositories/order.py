"""Репозиторий для работы с заказами."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.order import Order
from src.database.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Репозиторий для работы с заказами."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория заказов."""
        super().__init__(Order, session)

    async def get_user_orders(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """Получить заказы пользователя.

        Args:
            user_id: ID пользователя
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список заказов пользователя
        """
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """Получить заказы по статусу.

        Args:
            status: Статус заказа ('new', 'processing', 'paid', 'shipped', 'completed', 'cancelled')
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список заказов с указанным статусом
        """
        stmt = select(Order).where(Order.status == status).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_order(
        self,
        user_id: int,
        product_id: int,
        size: str,
        customer_contact: str,
    ) -> Order:
        """Создать новый заказ.

        Args:
            user_id: ID пользователя
            product_id: ID товара
            size: Размер товара
            customer_contact: Контактные данные клиента

        Returns:
            Созданный заказ
        """
        order = await self.create(
            user_id=user_id,
            product_id=product_id,
            size=size,
            customer_contact=customer_contact,
            status="new",
        )
        return order

    async def update_status(self, order_id: int, status: str) -> Order | None:
        """Обновить статус заказа.

        Args:
            order_id: ID заказа
            status: Новый статус

        Returns:
            Обновлённый заказ или None
        """
        return await self.update(order_id, status=status)

    async def add_admin_notes(
        self, order_id: int, notes: str
    ) -> Order | None:
        """Добавить заметки администратора к заказу.

        Args:
            order_id: ID заказа
            notes: Заметки администратора

        Returns:
            Обновлённый заказ или None
        """
        return await self.update(order_id, admin_notes=notes)

    async def cancel_order(self, order_id: int) -> Order | None:
        """Отменить заказ.

        Args:
            order_id: ID заказа

        Returns:
            Обновлённый заказ или None
        """
        return await self.update(order_id, status="cancelled")
