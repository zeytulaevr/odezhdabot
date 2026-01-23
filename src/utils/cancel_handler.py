"""Универсальный обработчик отмены FSM состояний."""

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import (
    get_admin_menu,
    get_superadmin_menu,
    get_user_menu,
)
from src.core.constants import UserRole
from src.database.models.user import User


def get_cancel_keyboard(callback_data: str = "cancel_action") -> InlineKeyboardMarkup:
    """Создать клавиатуру с кнопкой отмены.

    Args:
        callback_data: Callback data для кнопки отмены

    Returns:
        Inline клавиатура с кнопкой отмены
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отменить", callback_data=callback_data)
    )
    return builder.as_markup()


async def cancel_action_and_return_to_menu(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    cancel_message: str = "❌ Действие отменено",
) -> None:
    """Отменить действие, очистить FSM и вернуться в меню.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        user: Пользователь из БД
        cancel_message: Сообщение об отмене
    """
    await state.clear()
    await callback.answer("Отменено")

    # Определяем меню в зависимости от роли пользователя
    if user.role == UserRole.SUPER_ADMIN:
        menu_markup = get_superadmin_menu()
        menu_title = "👑 Супер-админ панель"
    elif user.role == UserRole.ADMIN:
        menu_markup = get_admin_menu()
        menu_title = "👨‍💼 Админ-панель"
    else:
        menu_markup = get_user_menu()
        menu_title = "🏠 Главное меню"

    text = f"{cancel_message}\n\n{menu_title}"

    await callback.message.edit_text(
        text=text,
        reply_markup=menu_markup,
        parse_mode="HTML",
    )
