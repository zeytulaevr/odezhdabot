"""Репозиторий для работы с категориями."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.category import Category
from src.database.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Репозиторий для работы с категориями товаров."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория категорий."""
        super().__init__(Category, session)

    async def get_active_categories(self) -> list[Category]:
        """Получить все активные категории.

        Returns:
            Список активных категорий
        """
        stmt = select(Category).where(Category.is_active == True).order_by(Category.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Category | None:
        """Получить категорию по названию.

        Args:
            name: Название категории

        Returns:
            Категория или None
        """
        stmt = select(Category).where(Category.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_thread_id(self, thread_id: int) -> Category | None:
        """Получить категорию по ID ветки в канале.

        Args:
            thread_id: ID ветки (topic) в канале

        Returns:
            Категория или None
        """
        stmt = select(Category).where(Category.thread_id == thread_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def toggle_active(self, category_id: int) -> Category | None:
        """Переключить активность категории.

        Args:
            category_id: ID категории

        Returns:
            Обновлённая категория или None
        """
        category = await self.get(category_id)
        if not category:
            return None

        category.is_active = not category.is_active
        await self.session.commit()
        await self.session.refresh(category)
        return category
