"""Базовый класс репозитория для работы с базой данных."""

from typing import Any, Generic, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый репозиторий с CRUD операциями."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        """Инициализация репозитория.

        Args:
            model: SQLAlchemy модель
            session: Async сессия базы данных
        """
        self.model = model
        self.session = session

    async def get(self, id: Any) -> ModelType | None:
        """Получить запись по ID.

        Args:
            id: ID записи

        Returns:
            Запись или None если не найдена
        """
        return await self.session.get(self.model, id)

    async def get_all(
        self, skip: int = 0, limit: int = 100, **filters: Any
    ) -> list[ModelType]:
        """Получить все записи с пагинацией и фильтрацией.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
            **filters: Фильтры для запроса

        Returns:
            Список записей
        """
        stmt = select(self.model).offset(skip).limit(limit)

        if filters:
            stmt = stmt.filter_by(**filters)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **values: Any) -> ModelType:
        """Создать новую запись.

        Args:
            **values: Значения полей для создания

        Returns:
            Созданная запись
        """
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: Any, **values: Any) -> ModelType | None:
        """Обновить запись по ID.

        Args:
            id: ID записи
            **values: Новые значения полей

        Returns:
            Обновлённая запись или None если не найдена
        """
        stmt = update(self.model).where(self.model.id == id).values(**values).returning(self.model)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def delete(self, id: Any) -> bool:
        """Удалить запись по ID.

        Args:
            id: ID записи

        Returns:
            True если запись удалена, False если не найдена
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def count(self, **filters: Any) -> int:
        """Подсчитать количество записей.

        Args:
            **filters: Фильтры для запроса

        Returns:
            Количество записей
        """
        stmt = select(self.model)

        if filters:
            stmt = stmt.filter_by(**filters)

        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def exists(self, **filters: Any) -> bool:
        """Проверить существование записи.

        Args:
            **filters: Фильтры для проверки

        Returns:
            True если запись существует, False иначе
        """
        return await self.count(**filters) > 0
