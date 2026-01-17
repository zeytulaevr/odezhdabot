"""Сервис для работы с пользователями."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.admin_log import AdminLogRepository
from src.database.repositories.user import UserRepository

logger = get_logger(__name__)


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса.

        Args:
            session: Async сессия базы данных
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.log_repo = AdminLogRepository(session)

    async def get_or_create_user(
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
        user, is_new = await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
        )

        if is_new:
            logger.info(
                "New user created",
                user_id=user.id,
                telegram_id=telegram_id,
                username=username,
            )

        return user, is_new

    async def update_user(
        self, user_id: int, **kwargs: Any
    ) -> User | None:
        """Обновить данные пользователя.

        Args:
            user_id: ID пользователя
            **kwargs: Поля для обновления

        Returns:
            Обновлённый пользователь или None
        """
        user = await self.user_repo.update(user_id, **kwargs)

        if user:
            logger.info(
                "User updated",
                user_id=user_id,
                updated_fields=list(kwargs.keys()),
            )

        return user

    async def ban_user(
        self, user_id: int, admin_id: int, reason: str | None = None
    ) -> User | None:
        """Забанить пользователя.

        Args:
            user_id: ID пользователя для бана
            admin_id: ID администратора, выполняющего бан
            reason: Причина бана

        Returns:
            Обновлённый пользователь или None
        """
        user = await self.user_repo.ban_user(user_id)

        if user:
            # Логируем действие администратора
            await self.log_repo.log_action(
                admin_id=admin_id,
                action="user_banned",
                details={
                    "user_id": user_id,
                    "telegram_id": user.telegram_id,
                    "reason": reason,
                },
            )

            logger.info(
                "User banned",
                user_id=user_id,
                banned_by=admin_id,
                reason=reason,
            )

        return user

    async def unban_user(
        self, user_id: int, admin_id: int
    ) -> User | None:
        """Разбанить пользователя.

        Args:
            user_id: ID пользователя для разбана
            admin_id: ID администратора, выполняющего разбан

        Returns:
            Обновлённый пользователь или None
        """
        user = await self.user_repo.unban_user(user_id)

        if user:
            # Логируем действие администратора
            await self.log_repo.log_action(
                admin_id=admin_id,
                action="user_unbanned",
                details={
                    "user_id": user_id,
                    "telegram_id": user.telegram_id,
                },
            )

            logger.info(
                "User unbanned",
                user_id=user_id,
                unbanned_by=admin_id,
            )

        return user

    async def change_role(
        self, user_id: int, new_role: str, admin_id: int
    ) -> User | None:
        """Изменить роль пользователя.

        Args:
            user_id: ID пользователя
            new_role: Новая роль ('user', 'admin', 'super_admin')
            admin_id: ID администратора, изменяющего роль

        Returns:
            Обновлённый пользователь или None
        """
        # Получаем старую роль
        old_user = await self.user_repo.get(user_id)
        if not old_user:
            return None

        old_role = old_user.role

        # Обновляем роль
        user = await self.user_repo.update(user_id, role=new_role)

        if user:
            # Логируем действие администратора
            await self.log_repo.log_action(
                admin_id=admin_id,
                action="user_role_changed",
                details={
                    "user_id": user_id,
                    "telegram_id": user.telegram_id,
                    "old_role": old_role,
                    "new_role": new_role,
                },
            )

            logger.info(
                "User role changed",
                user_id=user_id,
                old_role=old_role,
                new_role=new_role,
                changed_by=admin_id,
            )

        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Пользователь или None
        """
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def get_all_admins(self) -> list[User]:
        """Получить всех администраторов.

        Returns:
            Список администраторов
        """
        return await self.user_repo.get_all_admins()

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Получить активных пользователей.

        Args:
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список активных пользователей
        """
        return await self.user_repo.get_active_users(skip=skip, limit=limit)
