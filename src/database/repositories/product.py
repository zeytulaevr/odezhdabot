"""Репозиторий для работы с товарами."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import ProductCategory
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

    async def get_by_category(
        self, category: ProductCategory, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Получить товары по категории.

        Args:
            category: Категория товаров
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список товаров в категории
        """
        stmt = (
            select(Product)
            .where(Product.category == category.value, Product.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_featured_products(self, limit: int = 10) -> list[Product]:
        """Получить рекомендуемые товары.

        Args:
            limit: Максимальное количество товаров

        Returns:
            Список рекомендуемых товаров
        """
        stmt = (
            select(Product)
            .where(Product.is_featured == True, Product.is_active == True)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_available_products(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """Получить товары в наличии.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список товаров в наличии
        """
        stmt = (
            select(Product)
            .where(Product.is_active == True, Product.stock > 0)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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

    async def update_stock(self, product_id: int, quantity_change: int) -> Product | None:
        """Обновить количество товара на складе.

        Args:
            product_id: ID товара
            quantity_change: Изменение количества (может быть отрицательным)

        Returns:
            Обновлённый товар или None

        Raises:
            ValueError: Если недостаточно товара на складе
        """
        product = await self.get(product_id)
        if not product:
            return None

        new_stock = product.stock + quantity_change
        if new_stock < 0:
            raise ValueError(f"Недостаточно товара на складе. Доступно: {product.stock}")

        return await self.update(product_id, stock=new_stock)
