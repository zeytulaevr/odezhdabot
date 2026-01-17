"""Репозиторий для работы с паттернами спама."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.spam_pattern import SpamPattern
from src.database.repositories.base import BaseRepository


class SpamPatternRepository(BaseRepository[SpamPattern]):
    """Репозиторий для работы с паттернами спама."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория паттернов спама."""
        super().__init__(SpamPattern, session)

    async def get_active_patterns(self) -> list[SpamPattern]:
        """Получить активные паттерны спама.

        Returns:
            Список активных паттернов
        """
        stmt = select(SpamPattern).where(SpamPattern.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(self, pattern_type: str) -> list[SpamPattern]:
        """Получить паттерны по типу.

        Args:
            pattern_type: Тип паттерна ('keyword', 'regex', 'url')

        Returns:
            Список паттернов указанного типа
        """
        stmt = select(SpamPattern).where(
            SpamPattern.pattern_type == pattern_type,
            SpamPattern.is_active == True
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def toggle_active(self, pattern_id: int) -> SpamPattern | None:
        """Переключить активность паттерна.

        Args:
            pattern_id: ID паттерна

        Returns:
            Обновлённый паттерн или None
        """
        pattern = await self.get(pattern_id)
        if not pattern:
            return None

        pattern.is_active = not pattern.is_active
        await self.session.commit()
        await self.session.refresh(pattern)
        return pattern
