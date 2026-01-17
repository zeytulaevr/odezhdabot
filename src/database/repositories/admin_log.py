"""Репозиторий для работы с логами администраторов."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.admin_log import AdminLog
from src.database.repositories.base import BaseRepository


class AdminLogRepository(BaseRepository[AdminLog]):
    """Репозиторий для работы с логами действий администраторов."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория логов."""
        super().__init__(AdminLog, session)

    async def log_action(
        self,
        admin_id: int,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> AdminLog:
        """Записать действие администратора в лог.

        Args:
            admin_id: ID администратора
            action: Название действия
            details: Детали действия

        Returns:
            Созданная запись лога
        """
        log_entry = await self.create(
            admin_id=admin_id,
            action=action,
            details=details,
        )
        return log_entry

    async def get_admin_actions(
        self, admin_id: int, limit: int = 100
    ) -> list[AdminLog]:
        """Получить действия конкретного администратора.

        Args:
            admin_id: ID администратора
            limit: Максимальное количество записей

        Returns:
            Список действий администратора
        """
        stmt = (
            select(AdminLog)
            .where(AdminLog.admin_id == admin_id)
            .order_by(AdminLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_logs(self, limit: int = 50) -> list[AdminLog]:
        """Получить недавние логи.

        Args:
            limit: Максимальное количество записей

        Returns:
            Список недавних логов
        """
        stmt = (
            select(AdminLog)
            .order_by(AdminLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
