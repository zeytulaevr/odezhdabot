"""Сервис мониторинга и сбора метрик системы."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.broadcast import Broadcast
from src.database.models.order import Order
from src.database.models.product import Product
from src.database.models.review import Review
from src.database.models.user import User

logger = get_logger(__name__)


class MonitoringService:
    """Сервис для сбора метрик и мониторинга системы."""

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: Сессия БД
        """
        self.session = session

    async def get_system_stats(self) -> dict[str, Any]:
        """Получить общую статистику системы.

        Returns:
            Словарь со всей статистикой
        """
        logger.info("Collecting system stats")

        stats = {
            "users": await self._get_user_stats(),
            "orders": await self._get_order_stats(),
            "products": await self._get_product_stats(),
            "broadcasts": await self._get_broadcast_stats(),
            "reviews": await self._get_review_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info("System stats collected", total_sections=len(stats))
        return stats

    async def get_period_stats(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """Получить статистику за период.

        Args:
            start_date: Начало периода
            end_date: Конец периода

        Returns:
            Словарь со статистикой за период
        """
        logger.info(
            "Collecting period stats",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        stats = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days,
            },
            "users": await self._get_user_period_stats(start_date, end_date),
            "orders": await self._get_order_period_stats(start_date, end_date),
            "products": await self._get_product_period_stats(start_date, end_date),
            "broadcasts": await self._get_broadcast_period_stats(start_date, end_date),
        }

        return stats

    async def _get_user_stats(self) -> dict[str, Any]:
        """Получить статистику пользователей."""
        # Всего пользователей
        total = await self.session.scalar(select(func.count(User.id)))

        # Активные за последние 24 часа
        day_ago = datetime.utcnow() - timedelta(days=1)
        active_24h = await self.session.scalar(
            select(func.count(User.id)).where(User.last_active_at >= day_ago)
        )

        # Активные за последние 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_7d = await self.session.scalar(
            select(func.count(User.id)).where(User.last_active_at >= week_ago)
        )

        # Новые за последние 24 часа
        new_24h = await self.session.scalar(
            select(func.count(User.id)).where(User.created_at >= day_ago)
        )

        # Новые за последние 7 дней
        new_7d = await self.session.scalar(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )

        # По ролям
        roles = await self.session.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        by_role = {role: count for role, count in roles}

        # Заблокированные
        banned = await self.session.scalar(
            select(func.count(User.id)).where(User.is_banned == True)
        )

        return {
            "total": total or 0,
            "active_24h": active_24h or 0,
            "active_7d": active_7d or 0,
            "new_24h": new_24h or 0,
            "new_7d": new_7d or 0,
            "by_role": by_role,
            "banned": banned or 0,
        }

    async def _get_order_stats(self) -> dict[str, Any]:
        """Получить статистику заказов."""
        # Всего заказов
        total = await self.session.scalar(select(func.count(Order.id)))

        # По статусам
        statuses = await self.session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        )
        by_status = {status: count for status, count in statuses}

        # За последние 24 часа
        day_ago = datetime.utcnow() - timedelta(days=1)
        new_24h = await self.session.scalar(
            select(func.count(Order.id)).where(Order.created_at >= day_ago)
        )

        # За последние 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_7d = await self.session.scalar(
            select(func.count(Order.id)).where(Order.created_at >= week_ago)
        )

        # Конверсия (completed / total)
        completed = by_status.get("completed", 0)
        conversion_rate = (completed / total * 100) if total > 0 else 0

        return {
            "total": total or 0,
            "by_status": by_status,
            "new_24h": new_24h or 0,
            "new_7d": new_7d or 0,
            "conversion_rate": round(conversion_rate, 2),
        }

    async def _get_product_stats(self) -> dict[str, Any]:
        """Получить статистику товаров."""
        # Всего товаров
        total = await self.session.scalar(select(func.count(Product.id)))

        # Активные (is_available)
        active = await self.session.scalar(
            select(func.count(Product.id)).where(Product.is_available == True)
        )

        # По категориям
        categories = await self.session.execute(
            select(Product.category_id, func.count(Product.id)).group_by(
                Product.category_id
            )
        )
        by_category = {cat_id: count for cat_id, count in categories}

        # Без категории
        no_category = await self.session.scalar(
            select(func.count(Product.id)).where(Product.category_id == None)
        )

        return {
            "total": total or 0,
            "active": active or 0,
            "inactive": (total or 0) - (active or 0),
            "by_category": by_category,
            "no_category": no_category or 0,
        }

    async def _get_broadcast_stats(self) -> dict[str, Any]:
        """Получить статистику рассылок."""
        # Всего рассылок
        total = await self.session.scalar(select(func.count(Broadcast.id)))

        # По статусам
        statuses = await self.session.execute(
            select(Broadcast.status, func.count(Broadcast.id)).group_by(Broadcast.status)
        )
        by_status = {status: count for status, count in statuses}

        # Всего отправлено сообщений
        total_sent = await self.session.scalar(select(func.sum(Broadcast.sent_count)))

        # Всего успешно доставлено
        total_success = await self.session.scalar(
            select(func.sum(Broadcast.success_count))
        )

        # Всего ошибок
        total_failed = await self.session.scalar(
            select(func.sum(Broadcast.failed_count))
        )

        # Success rate
        success_rate = (
            (total_success / total_sent * 100) if total_sent and total_sent > 0 else 0
        )

        return {
            "total": total or 0,
            "by_status": by_status,
            "total_sent": total_sent or 0,
            "total_success": total_success or 0,
            "total_failed": total_failed or 0,
            "success_rate": round(success_rate, 2),
        }

    async def _get_review_stats(self) -> dict[str, Any]:
        """Получить статистику отзывов."""
        # Всего отзывов
        total = await self.session.scalar(select(func.count(Review.id)))

        # Одобренные
        approved = await self.session.scalar(
            select(func.count(Review.id)).where(Review.is_approved == True)
        )

        # Отклоненные
        rejected = await self.session.scalar(
            select(func.count(Review.id)).where(Review.is_approved == False)
        )

        # На модерации (is_approved == None)
        pending = await self.session.scalar(
            select(func.count(Review.id)).where(Review.is_approved == None)
        )

        return {
            "total": total or 0,
            "approved": approved or 0,
            "rejected": rejected or 0,
            "pending": pending or 0,
        }

    async def _get_user_period_stats(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Получить статистику пользователей за период."""
        # Новые пользователи
        new_users = await self.session.scalar(
            select(func.count(User.id)).where(
                and_(User.created_at >= start_date, User.created_at <= end_date)
            )
        )

        # Активные пользователи
        active_users = await self.session.scalar(
            select(func.count(User.id)).where(
                and_(User.last_active_at >= start_date, User.last_active_at <= end_date)
            )
        )

        return {
            "new": new_users or 0,
            "active": active_users or 0,
        }

    async def _get_order_period_stats(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Получить статистику заказов за период."""
        # Новые заказы
        new_orders = await self.session.scalar(
            select(func.count(Order.id)).where(
                and_(Order.created_at >= start_date, Order.created_at <= end_date)
            )
        )

        # Завершенные заказы
        completed_orders = await self.session.scalar(
            select(func.count(Order.id)).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status == "completed",
                )
            )
        )

        # По статусам
        statuses = await self.session.execute(
            select(Order.status, func.count(Order.id))
            .where(and_(Order.created_at >= start_date, Order.created_at <= end_date))
            .group_by(Order.status)
        )
        by_status = {status: count for status, count in statuses}

        return {
            "new": new_orders or 0,
            "completed": completed_orders or 0,
            "by_status": by_status,
        }

    async def _get_product_period_stats(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Получить статистику товаров за период."""
        # Новые товары
        new_products = await self.session.scalar(
            select(func.count(Product.id)).where(
                and_(Product.created_at >= start_date, Product.created_at <= end_date)
            )
        )

        return {
            "new": new_products or 0,
        }

    async def _get_broadcast_period_stats(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Получить статистику рассылок за период."""
        # Новые рассылки
        new_broadcasts = await self.session.scalar(
            select(func.count(Broadcast.id)).where(
                and_(
                    Broadcast.created_at >= start_date, Broadcast.created_at <= end_date
                )
            )
        )

        # Отправлено сообщений
        sent = await self.session.scalar(
            select(func.sum(Broadcast.sent_count)).where(
                and_(
                    Broadcast.created_at >= start_date, Broadcast.created_at <= end_date
                )
            )
        )

        # Успешно доставлено
        success = await self.session.scalar(
            select(func.sum(Broadcast.success_count)).where(
                and_(
                    Broadcast.created_at >= start_date, Broadcast.created_at <= end_date
                )
            )
        )

        return {
            "new": new_broadcasts or 0,
            "sent": sent or 0,
            "success": success or 0,
        }

    async def get_health_check(self) -> dict[str, Any]:
        """Проверка здоровья системы.

        Returns:
            Статус всех компонентов
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
        }

        # Проверка БД
        try:
            await self.session.execute(select(1))
            health["components"]["database"] = {"status": "healthy"}
        except Exception as e:
            health["status"] = "unhealthy"
            health["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            logger.error("Database health check failed", error=str(e))

        return health
