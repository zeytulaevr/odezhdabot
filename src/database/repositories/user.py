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
        stmt = select(User).where(User.role.in_(["admin", "super_admin"]))
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
