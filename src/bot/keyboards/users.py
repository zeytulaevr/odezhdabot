"""Клавиатуры для управления пользователями."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.models.user import User


def get_users_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню управления пользователями.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📋 Список пользователей",
            callback_data="users:list:0",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск пользователя",
            callback_data="users:search",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_users_list_keyboard(
    users: list[User], page: int = 0, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Клавиатура списка пользователей.

    Args:
        users: Список пользователей
        page: Текущая страница
        total_pages: Всего страниц

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    for user in users:
        # Иконка статуса
        status_icon = "🚫" if user.is_banned else "✅"
        role_icon = "👑" if user.is_super_admin else "👤" if user.is_admin else "👥"

        # Имя пользователя
        display_name = user.full_name[:25] + "..." if len(user.full_name) > 25 else user.full_name
        username_str = f" (@{user.username})" if user.username else ""

        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {role_icon} {display_name}{username_str}",
                callback_data=f"users:view:{user.id}",
            )
        )

    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Пред.", callback_data=f"users:list:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="След. ▶️", callback_data=f"users:list:{page+1}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопки управления
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск", callback_data="users:search")
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_user_profile_keyboard(user: User) -> InlineKeyboardMarkup:
    """Клавиатура профиля пользователя.

    Args:
        user: Пользователь

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Действия с пользователем (если не супер-админ)
    if not user.is_super_admin:
        if user.is_banned:
            builder.row(
                InlineKeyboardButton(
                    text="✅ Разблокировать",
                    callback_data=f"users:unban:{user.id}",
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="🚫 Заблокировать",
                    callback_data=f"users:ban:{user.id}",
                )
            )

    # Управление бонусами
    builder.row(
        InlineKeyboardButton(
            text="💰 Редактировать бонусы",
            callback_data=f"users:edit_bonus:{user.id}",
        )
    )

    # Заказы пользователя
    builder.row(
        InlineKeyboardButton(
            text="🛍 Заказы пользователя",
            callback_data=f"users:orders:{user.id}",
        )
    )

    # Навигация
    builder.row(
        InlineKeyboardButton(text="◀️ К списку", callback_data="users:list:0")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_user_ban_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения блокировки.

    Args:
        user_id: ID пользователя

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, заблокировать",
            callback_data=f"users:ban_confirm:{user_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"users:view:{user_id}",
        ),
    )

    return builder.as_markup()
