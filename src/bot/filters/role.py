"""Фильтры для проверки ролей пользователей."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from src.database.models.user import User


class RoleFilter(BaseFilter):
    """Фильтр для проверки роли пользователя."""

    def __init__(self, roles: list[str]) -> None:
        """Инициализация фильтра.

        Args:
            roles: Список допустимых ролей
        """
        self.roles = roles

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        """Проверка роли пользователя.

        Args:
            message: Сообщение от пользователя
            user: Пользователь из БД (добавляется AuthMiddleware)

        Returns:
            True если роль пользователя в списке допустимых
        """
        if not user:
            return False

        return user.role in self.roles


class IsAdmin(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором."""

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        """Проверка прав администратора.

        Args:
            message: Сообщение от пользователя
            user: Пользователь из БД

        Returns:
            True если пользователь администратор или супер-админ
        """
        if not user:
            return False

        return user.role in ["admin", "super_admin"]


class IsSuperAdmin(BaseFilter):
    """Фильтр для проверки, является ли пользователь супер-администратором."""

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        """Проверка прав супер-администратора.

        Args:
            message: Сообщение от пользователя
            user: Пользователь из БД

        Returns:
            True если пользователь супер-админ
        """
        if not user:
            return False

        return user.role == "super_admin"


class IsUser(BaseFilter):
    """Фильтр для проверки, является ли пользователь обычным клиентом."""

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        """Проверка обычного пользователя.

        Args:
            message: Сообщение от пользователя
            user: Пользователь из БД

        Returns:
            True если пользователь с ролью 'user'
        """
        if not user:
            return False

        return user.role == "user"
