"""Сервис для управления рассылками."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.broadcast import Broadcast
from src.database.models.order import Order
from src.database.models.user import User

logger = get_logger(__name__)


class BroadcastService:
    """Сервис для работы с рассылками."""

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: Сессия БД
        """
        self.session = session

    async def create_broadcast(
        self,
        text: str,
        admin_id: int,
        filters: dict[str, Any] | None = None,
        media_type: str | None = None,
        media_file_id: str | None = None,
        buttons: dict[str, Any] | None = None,
    ) -> Broadcast:
        """Создать рассылку.

        Args:
            text: Текст сообщения
            admin_id: ID администратора
            filters: Фильтры сегментации
            media_type: Тип медиа (photo, video, document)
            media_file_id: File ID медиа
            buttons: Inline кнопки

        Returns:
            Созданная рассылка
        """
        # Получаем количество целевых пользователей
        target_users = await self.get_target_users(filters or {})
        total_target = len(target_users)

        broadcast = Broadcast(
            text=text,
            media_type=media_type,
            media_file_id=media_file_id,
            buttons=buttons,
            filters=filters,
            created_by=admin_id,
            total_target=total_target,
            status="pending",
        )

        self.session.add(broadcast)
        await self.session.flush()

        logger.info(
            "Broadcast created",
            broadcast_id=broadcast.id,
            admin_id=admin_id,
            total_target=total_target,
            has_media=broadcast.has_media,
        )

        return broadcast

    async def get_target_users(self, filters: dict[str, Any]) -> list[User]:
        """Получить список пользователей по фильтрам.

        Поддерживаемые фильтры:
        - all: True - все пользователи
        - active_days: int - активны за последние N дней
        - has_orders: bool - есть заказы
        - no_orders: bool - нет заказов
        - registered_after: str (YYYY-MM-DD) - регистрация после даты
        - min_orders: int - минимум заказов

        Args:
            filters: Словарь фильтров

        Returns:
            Список пользователей
        """
        # Фильтруем только не заблокированных пользователей
        query = select(User).where(User.is_banned == False)

        # Фильтр: все пользователи (no additional filters)
        if filters.get("all"):
            result = await self.session.execute(query)
            return list(result.scalars().all())

        conditions = []

        # Фильтр: активные пользователи (последняя активность)
        if "active_days" in filters:
            days = filters["active_days"]
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            conditions.append(User.last_active_at >= cutoff_date)

        # Фильтр: регистрация после даты
        if "registered_after" in filters:
            date_str = filters["registered_after"]
            try:
                cutoff_date = datetime.fromisoformat(date_str)
                conditions.append(User.created_at >= cutoff_date)
            except (ValueError, TypeError):
                logger.warning(f"Invalid registered_after date: {date_str}")

        # Фильтр: есть/нет заказов
        if filters.get("has_orders") or filters.get("no_orders") or "min_orders" in filters:
            # Подзапрос для подсчета заказов
            orders_subquery = (
                select(Order.user_id, func.count(Order.id).label("order_count"))
                .group_by(Order.user_id)
                .subquery()
            )

            query = query.outerjoin(orders_subquery, User.id == orders_subquery.c.user_id)

            if filters.get("has_orders"):
                query = query.where(orders_subquery.c.order_count > 0)
            elif filters.get("no_orders"):
                query = query.where(
                    (orders_subquery.c.order_count == None) | (orders_subquery.c.order_count == 0)
                )

            if "min_orders" in filters:
                min_count = filters["min_orders"]
                query = query.where(orders_subquery.c.order_count >= min_count)

        # Применяем остальные условия
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        users = list(result.scalars().all())

        logger.info(
            "Target users filtered",
            filters=filters,
            count=len(users),
        )

        return users

    async def get_broadcast(self, broadcast_id: int) -> Broadcast | None:
        """Получить рассылку по ID.

        Args:
            broadcast_id: ID рассылки

        Returns:
            Рассылка или None
        """
        result = await self.session.execute(
            select(Broadcast).where(Broadcast.id == broadcast_id)
        )
        return result.scalar_one_or_none()

    async def get_all_broadcasts(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Broadcast]:
        """Получить все рассылки.

        Args:
            limit: Лимит записей
            offset: Смещение

        Returns:
            Список рассылок
        """
        result = await self.session.execute(
            select(Broadcast)
            .order_by(Broadcast.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_broadcasts_by_status(
        self,
        status: str,
        limit: int = 50,
    ) -> list[Broadcast]:
        """Получить рассылки по статусу.

        Args:
            status: Статус (pending, in_progress, completed, failed, cancelled)
            limit: Лимит записей

        Returns:
            Список рассылок
        """
        result = await self.session.execute(
            select(Broadcast)
            .where(Broadcast.status == status)
            .order_by(Broadcast.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_broadcast_status(
        self,
        broadcast_id: int,
        status: str,
    ) -> Broadcast | None:
        """Обновить статус рассылки.

        Args:
            broadcast_id: ID рассылки
            status: Новый статус

        Returns:
            Обновленная рассылка или None
        """
        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            return None

        broadcast.status = status

        if status in ["completed", "failed", "cancelled"]:
            broadcast.completed_at = datetime.utcnow()

        await self.session.flush()

        logger.info(
            "Broadcast status updated",
            broadcast_id=broadcast_id,
            status=status,
        )

        return broadcast

    async def update_broadcast_stats(
        self,
        broadcast_id: int,
        sent_count: int | None = None,
        success_count: int | None = None,
        failed_count: int | None = None,
    ) -> Broadcast | None:
        """Обновить статистику рассылки.

        Args:
            broadcast_id: ID рассылки
            sent_count: Количество отправленных
            success_count: Количество успешных
            failed_count: Количество ошибок

        Returns:
            Обновленная рассылка или None
        """
        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            return None

        if sent_count is not None:
            broadcast.sent_count = sent_count
        if success_count is not None:
            broadcast.success_count = success_count
        if failed_count is not None:
            broadcast.failed_count = failed_count

        await self.session.flush()
        return broadcast

    async def increment_broadcast_stats(
        self,
        broadcast_id: int,
        sent: int = 0,
        success: int = 0,
        failed: int = 0,
    ) -> Broadcast | None:
        """Инкрементировать статистику рассылки.

        Args:
            broadcast_id: ID рассылки
            sent: Инкремент отправленных
            success: Инкремент успешных
            failed: Инкремент ошибок

        Returns:
            Обновленная рассылка или None
        """
        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            return None

        broadcast.sent_count += sent
        broadcast.success_count += success
        broadcast.failed_count += failed

        await self.session.flush()
        return broadcast

    async def add_broadcast_error(
        self,
        broadcast_id: int,
        user_id: int,
        error_message: str,
    ) -> Broadcast | None:
        """Добавить ошибку в лог рассылки.

        Args:
            broadcast_id: ID рассылки
            user_id: ID пользователя
            error_message: Сообщение об ошибке

        Returns:
            Обновленная рассылка или None
        """
        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            return None

        if broadcast.error_log is None:
            broadcast.error_log = {"errors": []}

        broadcast.error_log["errors"].append({
            "user_id": user_id,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        })

        await self.session.flush()
        return broadcast

    async def cancel_broadcast(self, broadcast_id: int) -> Broadcast | None:
        """Отменить рассылку.

        Args:
            broadcast_id: ID рассылки

        Returns:
            Обновленная рассылка или None
        """
        return await self.update_broadcast_status(broadcast_id, "cancelled")

    async def get_broadcast_stats(self) -> dict[str, int]:
        """Получить общую статистику по рассылкам.

        Returns:
            Словарь со статистикой
        """
        # Подсчет по статусам
        status_counts = await self.session.execute(
            select(Broadcast.status, func.count(Broadcast.id))
            .group_by(Broadcast.status)
        )

        stats = {
            "total": 0,
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

        for status, count in status_counts:
            stats[status] = count
            stats["total"] += count

        # Общая статистика отправок
        totals = await self.session.execute(
            select(
                func.sum(Broadcast.sent_count),
                func.sum(Broadcast.success_count),
                func.sum(Broadcast.failed_count),
            )
        )
        sent, success, failed = totals.one()

        stats["total_sent"] = sent or 0
        stats["total_success"] = success or 0
        stats["total_failed"] = failed or 0

        return stats
