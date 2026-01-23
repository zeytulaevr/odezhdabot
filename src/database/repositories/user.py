"""Репозиторий для работы с пользователями."""

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UserRole
from src.database.models.user import User
from src.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория пользователей."""
        super().__init__(User, session)

    async def get_by_id(self, user_id: int) -> User | None:
        """Получить пользователя по ID.

        Args:
            user_id: ID пользователя в БД

        Returns:
            Пользователь или None
        """
        return await self.get(user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Пользователь или None
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Получить пользователя по username.

        Args:
            username: Username пользователя в Telegram

        Returns:
            Пользователь или None
        """
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None = None,
    ) -> tuple[User, bool]:
        """Получить существующего пользователя или создать нового.

        Args:
            telegram_id: Telegram ID пользователя
            full_name: Полное имя пользователя
            username: Username пользователя

        Returns:
            Кортеж (пользователь, создан_ли_новый)
        """
        user = await self.get_by_telegram_id(telegram_id)

        if user:
            # Обновление данных если они изменились
            if user.username != username or user.full_name != full_name:
                stmt = (
                    select(User)
                    .where(User.id == user.id)
                )
                user.username = username
                user.full_name = full_name
                await self.session.commit()
                await self.session.refresh(user)
            return user, False

        # Создание нового пользователя
        user = await self.create(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
        )
        return user, True

    async def get_all_admins(self) -> list[User]:
        """Получить всех администраторов.

        Returns:
            Список администраторов
        """
        stmt = select(User).where(
            User.role.in_([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Получить активных (не забаненных) пользователей.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список активных пользователей
        """
        stmt = (
            select(User)
            .where(User.is_banned == False)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def ban_user(self, user_id: int) -> User | None:
        """Забанить пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Обновлённый пользователь или None
        """
        return await self.update(user_id, is_banned=True)

    async def unban_user(self, user_id: int) -> User | None:
        """Разбанить пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Обновлённый пользователь или None
        """
        return await self.update(user_id, is_banned=False)

    async def get_all_users(
        self, skip: int = 0, limit: int = 10, order_by: str = "created_at"
    ) -> list[User]:
        """Получить всех пользователей с пагинацией.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
            order_by: Поле для сортировки

        Returns:
            Список пользователей
        """
        stmt = select(User).order_by(getattr(User, order_by).desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_users(self) -> int:
        """Подсчитать количество пользователей.

        Returns:
            Количество пользователей
        """
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def search_users(self, query: str, limit: int = 20) -> list[User]:
        """Поиск пользователей по имени, username или telegram_id.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список пользователей
        """
        # Проверяем, является ли запрос числом (для поиска по telegram_id)
        if query.isdigit():
            telegram_id = int(query)
            stmt = select(User).where(
                or_(
                    User.telegram_id == telegram_id,
                    User.full_name.ilike(f"%{query}%"),
                    User.username.ilike(f"%{query}%"),
                )
            ).limit(limit)
        else:
            # Поиск по имени и username
            stmt = select(User).where(
                or_(
                    User.full_name.ilike(f"%{query}%"),
                    User.username.ilike(f"%{query}%"),
                )
            ).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
