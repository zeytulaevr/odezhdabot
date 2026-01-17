"""Репозиторий для работы с пользователями."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User
from src.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория пользователей."""
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Пользователь или None
        """
        return await self.get(telegram_id)

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
        username: str | None,
        first_name: str,
        last_name: str | None = None,
    ) -> tuple[User, bool]:
        """Получить существующего пользователя или создать нового.

        Args:
            telegram_id: Telegram ID пользователя
            username: Username пользователя
            first_name: Имя пользователя
            last_name: Фамилия пользователя

        Returns:
            Кортеж (пользователь, создан_ли_новый)
        """
        user = await self.get_by_telegram_id(telegram_id)

        if user:
            # Обновление данных если они изменились
            if user.username != username or user.first_name != first_name:
                await self.update(
                    telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                )
                await self.session.refresh(user)
            return user, False

        # Создание нового пользователя
        user = await self.create(
            id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        return user, True

    async def get_all_admins(self) -> list[User]:
        """Получить всех администраторов.

        Returns:
            Список администраторов
        """
        from src.core.constants import UserRole

        stmt = select(User).where(User.role == UserRole.ADMIN.value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Получить активных пользователей.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список активных пользователей
        """
        stmt = (
            select(User)
            .where(User.is_active == True, User.is_blocked == False)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def block_user(self, telegram_id: int) -> User | None:
        """Заблокировать пользователя.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Обновлённый пользователь или None
        """
        return await self.update(telegram_id, is_blocked=True)

    async def unblock_user(self, telegram_id: int) -> User | None:
        """Разблокировать пользователя.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Обновлённый пользователь или None
        """
        return await self.update(telegram_id, is_blocked=False)
