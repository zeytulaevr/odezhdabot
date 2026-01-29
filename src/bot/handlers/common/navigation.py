"""Обработчики навигации (кнопка Назад)."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.bot.keyboards.main_menu import (
    get_admin_panel_keyboard,
    get_superadmin_panel_keyboard,
    get_user_menu,
)
from src.core.constants import CallbackPrefix, UserRole
from src.core.logging import get_logger
from src.database.models.user import User
from src.utils.navigation import go_back

logger = get_logger(__name__)

router = Router(name="navigation")


@router.callback_query(F.data == CallbackPrefix.BACK)
async def handle_back_button(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Обработчик кнопки 'Назад'.

    Восстанавливает предыдущий экран из истории навигации.
    Если история пуста, возвращает в главное меню.

    Args:
        callback: Callback query
        state: FSM контекст
        user: Пользователь из БД
    """
    logger.info(
        "Back button pressed",
        user_id=user.id,
        telegram_id=user.telegram_id,
    )

    # Пытаемся вернуться на предыдущий экран
    success = await go_back(
        callback=callback,
        state=state,
        default_text=(
            "🏠 <b>Главное меню</b>\n\n"
            "История навигации пуста.\n"
            "Выберите действие из меню ниже."
        ),
    )

    if success:
        logger.info(
            "Navigated back successfully",
            user_id=user.id,
        )
    else:
        logger.info(
            "Navigation history empty, showing main menu",
            user_id=user.id,
        )
        # Определяем меню в зависимости от роли пользователя
        if user.role == UserRole.SUPER_ADMIN:
            menu_markup = get_superadmin_panel_keyboard()
            menu_title = "👑 <b>Супер-админ панель</b>"
            menu_text = (
                f"{menu_title}\n\n"
                f"Добро пожаловать, <b>{user.full_name}</b>!\n"
                f"Роль: <code>{user.role}</code>\n\n"
                f"У вас полный доступ ко всем функциям бота.\n\n"
                f"Выберите действие:"
            )
        elif user.role == UserRole.ADMIN:
            menu_markup = get_admin_panel_keyboard()
            menu_title = "👨‍💼 <b>Админ-панель</b>"
            menu_text = (
                f"{menu_title}\n\n"
                f"Добро пожаловать, <b>{user.full_name}</b>!\n"
                f"Роль: <code>{user.role}</code>\n\n"
                f"Выберите действие:"
            )
        else:
            menu_markup = get_user_menu()
            menu_title = "🏠 <b>Главное меню</b>"
            menu_text = (
                f"{menu_title}\n\n"
                "История навигации пуста.\n"
                "Выберите действие из меню ниже."
            )

        # Показываем главное меню с клавиатурой
        # Проверяем, есть ли фото в сообщении
        from aiogram.exceptions import TelegramBadRequest
        if callback.message.photo:
            # Если есть фото, удаляем сообщение и отправляем новое
            try:
                await callback.message.delete()
                await callback.message.answer(
                    text=menu_text,
                    reply_markup=menu_markup,
                    parse_mode="HTML",
                )
            except TelegramBadRequest:
                # Если не удалось удалить, просто отправляем новое
                await callback.message.answer(
                    text=menu_text,
                    reply_markup=menu_markup,
                    parse_mode="HTML",
                )
        else:
            # Обычное редактирование текста
            await callback.message.edit_text(
                text=menu_text,
                reply_markup=menu_markup,
                parse_mode="HTML",
            )
