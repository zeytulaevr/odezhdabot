"""Сервис для работы с заказами."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.order import Order
from src.database.models.product import Product
from src.database.models.user import User

logger = get_logger(__name__)


class OrderService:
    """Сервис для управления заказами."""

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: Асинхронная сессия БД
        """
        self.session = session

    async def create_order(
        self,
        user_id: int,
        product_id: int,
        size: str,
        customer_contact: str,
        color: str | None = None,
        quantity: int = 1,
    ) -> Order:
        """Создать новый заказ.

        Args:
            user_id: ID пользователя
            product_id: ID товара
            size: Размер товара
            customer_contact: Контактные данные клиента
            color: Выбранный цвет (опционально)
            quantity: Количество товара (по умолчанию 1)

        Returns:
            Созданный заказ
        """
        order = Order(
            user_id=user_id,
            product_id=product_id,
            size=size,
            color=color,
            quantity=quantity,
            customer_contact=customer_contact,
            status="new",
        )

        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)

        logger.info(
            "Order created",
            order_id=order.id,
            user_id=user_id,
            product_id=product_id,
            size=size,
            color=color,
            quantity=quantity,
        )

        return order

    async def get_order(self, order_id: int) -> Order | None:
        """Получить заказ по ID.

        Args:
            order_id: ID заказа

        Returns:
            Заказ или None
        """
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_order_status(
        self,
        order_id: int,
        status: str,
        admin_notes: str | None = None,
    ) -> Order | None:
        """Обновить статус заказа.

        Args:
            order_id: ID заказа
            status: Новый статус
            admin_notes: Заметки администратора (опционально)

        Returns:
            Обновленный заказ или None
        """
        order = await self.get_order(order_id)

        if not order:
            return None

        old_status = order.status
        order.status = status

        if admin_notes:
            if order.admin_notes:
                order.admin_notes += f"\n\n{admin_notes}"
            else:
                order.admin_notes = admin_notes

        await self.session.flush()

        logger.info(
            "Order status updated",
            order_id=order_id,
            old_status=old_status,
            new_status=status,
        )

        return order

    async def cancel_order(self, order_id: int, reason: str | None = None) -> Order | None:
        """Отменить заказ.

        Args:
            order_id: ID заказа
            reason: Причина отмены

        Returns:
            Обновленный заказ или None
        """
        order = await self.get_order(order_id)

        if not order:
            return None

        if not order.can_be_cancelled:
            logger.warning(
                "Cannot cancel order",
                order_id=order_id,
                status=order.status,
            )
            return None

        admin_note = f"Заказ отменён. {reason}" if reason else "Заказ отменён."
        return await self.update_order_status(order_id, "cancelled", admin_note)

    async def get_user_orders(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """Получить заказы пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список заказов
        """
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_orders_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Order]:
        """Получить заказы по статусу.

        Args:
            status: Статус заказа
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список заказов
        """
        result = await self.session.execute(
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_pending_orders(self, limit: int = 50) -> list[Order]:
        """Получить новые заказы для обработки.

        Args:
            limit: Максимальное количество

        Returns:
            Список новых заказов
        """
        return await self.get_orders_by_status("new", limit=limit)

    async def get_all_orders(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Order]:
        """Получить все заказы.

        Args:
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список заказов
        """
        result = await self.session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_orders_by_status(self, status: str) -> int:
        """Подсчитать количество заказов по статусу.

        Args:
            status: Статус заказа

        Returns:
            Количество заказов
        """
        result = await self.session.execute(
            select(func.count(Order.id)).where(Order.status == status)
        )
        return result.scalar_one()

    async def get_order_stats(self) -> dict[str, int]:
        """Получить статистику по заказам.

        Returns:
            Словарь со статистикой по каждому статусу
        """
        statuses = ["new", "processing", "paid", "shipped", "completed", "cancelled"]
        stats = {}

        for status in statuses:
            count = await self.count_orders_by_status(status)
            stats[status] = count

        # Общее количество
        result = await self.session.execute(select(func.count(Order.id)))
        stats["total"] = result.scalar_one()

        logger.info("Order stats retrieved", stats=stats)

        return stats

    async def add_admin_note(self, order_id: int, note: str) -> Order | None:
        """Добавить заметку администратора к заказу.

        Args:
            order_id: ID заказа
            note: Текст заметки

        Returns:
            Обновленный заказ или None
        """
        order = await self.get_order(order_id)

        if not order:
            return None

        if order.admin_notes:
            order.admin_notes += f"\n\n{note}"
        else:
            order.admin_notes = note

        await self.session.flush()

        logger.info("Admin note added to order", order_id=order_id)

        return order
