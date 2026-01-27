"""Репозиторий для работы с товарами."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.product import Product
from src.database.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Репозиторий для работы с товарами."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория товаров."""
        super().__init__(Product, session)

    async def get_active_products(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """Получить активные товары.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список активных товаров
        """
        stmt = select(Product).where(Product.is_active == True).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category_id(
        self, category_id: int, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Получить товары по ID категории.

        Args:
            category_id: ID категории
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список товаров в категории
        """
        stmt = (
            select(Product)
            .where(Product.category_id == category_id, Product.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(
        self,
        category_id: int,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        """Получить товары по ID категории с фильтрацией.

        Args:
            category_id: ID категории
            is_active: Фильтр по активности (None - все товары)
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список товаров в категории
        """
        stmt = select(Product).where(Product.category_id == category_id)

        if is_active is not None:
            stmt = stmt.where(Product.is_active == is_active)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """Получить активные товары.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список активных товаров
        """
        return await self.get_active_products(skip=skip, limit=limit)

    async def search_by_name(self, query: str, limit: int = 20) -> list[Product]:
        """Поиск товаров по названию.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список найденных товаров
        """
        stmt = (
            select(Product)
            .where(Product.name.ilike(f"%{query}%"), Product.is_active == True)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
