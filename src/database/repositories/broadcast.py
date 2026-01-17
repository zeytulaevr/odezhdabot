"""Репозиторий для работы с рассылками."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.broadcast import Broadcast
from src.database.repositories.base import BaseRepository


class BroadcastRepository(BaseRepository[Broadcast]):
    """Репозиторий для работы с рассылками."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория рассылок."""
        super().__init__(Broadcast, session)

    async def create_broadcast(
        self,
        text: str,
        created_by: int,
        filters: dict[str, Any] | None = None,
    ) -> Broadcast:
        """Создать новую рассылку.

        Args:
            text: Текст рассылки
            created_by: ID администратора
            filters: Фильтры для сегментации

        Returns:
            Созданная рассылка
        """
        broadcast = await self.create(
            text=text,
            created_by=created_by,
            filters=filters,
            sent_count=0,
        )
        return broadcast

    async def increment_sent_count(
        self, broadcast_id: int, count: int = 1
    ) -> Broadcast | None:
        """Увеличить счётчик отправленных сообщений.

        Args:
            broadcast_id: ID рассылки
            count: Количество отправленных сообщений

        Returns:
            Обновлённая рассылка или None
        """
        broadcast = await self.get(broadcast_id)
        if not broadcast:
            return None

        new_count = broadcast.sent_count + count
        return await self.update(broadcast_id, sent_count=new_count)

    async def get_recent_broadcasts(self, limit: int = 20) -> list[Broadcast]:
        """Получить недавние рассылки.

        Args:
            limit: Максимальное количество рассылок

        Returns:
            Список недавних рассылок
        """
        stmt = (
            select(Broadcast)
            .order_by(Broadcast.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
