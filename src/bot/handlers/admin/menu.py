"""Хендлеры для админ-панели."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.main_menu import get_admin_menu, get_admin_panel_keyboard
from src.core.logging import get_logger
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="admin_menu")


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message, user: User) -> None:
    """Команда /admin - открыть админ-панель.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Admin panel opened", user_id=user.id, role=user.role)

    text = (
        f"👨‍💼 <b>Админ-панель</b>\n\n"
        f"Добро пожаловать, <b>{user.full_name}</b>!\n"
        f"Роль: <code>{user.role}</code>\n\n"
        f"Выберите действие:"
    )

    await message.answer(
        text=text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📋 Заказы", IsAdmin())
async def show_orders_menu(message: Message, user: User) -> None:
    """Показать меню заказов.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Orders menu opened", user_id=user.id)

    text = (
        "📋 <b>Управление заказами</b>\n\n"
        "Выберите статус заказов для просмотра:"
    )

    await message.answer(
        text=text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📊 Статистика", IsAdmin())
async def show_statistics(message: Message, user: User) -> None:
    """Показать статистику.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Statistics opened", user_id=user.id)

    # TODO: Реализовать подсчёт статистики
    text = (
        "📊 <b>Статистика</b>\n\n"
        "📦 Всего заказов: <code>0</code>\n"
        "🆕 Новых: <code>0</code>\n"
        "🔄 В обработке: <code>0</code>\n"
        "✅ Завершённых: <code>0</code>\n\n"
        "👥 Всего пользователей: <code>0</code>\n"
        "🟢 Активных: <code>0</code>\n"
        "🔴 Забаненных: <code>0</code>"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.message(F.text == "👤 Пользователи", IsAdmin())
async def show_users_menu(message: Message, user: User) -> None:
    """Показать меню пользователей.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Users menu opened", user_id=user.id)

    text = (
        "👤 <b>Управление пользователями</b>\n\n"
        "Здесь вы можете:\n"
        "• Просмотреть список пользователей\n"
        "• Заблокировать/разблокировать пользователя\n"
        "• Посмотреть информацию о пользователе"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:"), IsAdmin())
async def process_admin_callback(callback: CallbackQuery, user: User) -> None:
    """Обработка callback от админ-панели.

    Args:
        callback: Callback query
        user: Пользователь из БД
    """
    await callback.answer()

    action = callback.data.split(":")[1] if ":" in callback.data else None

    if action == "orders":
        text = "📋 <b>Заказы</b>\n\nФункционал в разработке..."
    elif action == "stats":
        text = "📊 <b>Статистика</b>\n\nФункционал в разработке..."
    elif action == "users":
        text = "👤 <b>Пользователи</b>\n\nФункционал в разработке..."
    else:
        text = "⚠️ Неизвестное действие"

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML")
