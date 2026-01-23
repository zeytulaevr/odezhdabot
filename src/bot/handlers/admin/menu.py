"""Хендлеры для админ-панели."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.main_menu import get_admin_menu, get_admin_panel_keyboard
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.moderated_message import ModeratedMessageRepository

logger = get_logger(__name__)

router = Router(name="admin_menu")


@router.message(Command("admin"), IsAdmin())
@router.message(F.text == "📋 Админ-панель", IsAdmin())
async def cmd_admin(message: Message, user: User) -> None:
    """Команда /admin или кнопка "Админ-панель" - открыть админ-панель.

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
async def process_admin_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Обработка callback от админ-панели.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
    """
    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else None
    subaction = parts[2] if len(parts) > 2 else None

    # Заказы
    if action == "orders":
        if subaction in ["new", "processing", "completed"]:
            status_names = {
                "new": "новые",
                "processing": "в обработке",
                "completed": "завершённые",
            }
            await callback.answer()
            text = f"📋 <b>Заказы ({status_names[subaction]})</b>\n\nФункционал в разработке..."
            if callback.message:
                await callback.message.edit_text(text=text, parse_mode="HTML")
        else:
            await callback.answer()
            text = "📋 <b>Заказы</b>\n\nФункционал в разработке..."
            if callback.message:
                await callback.message.edit_text(text=text, parse_mode="HTML")
        return

    # Статистика модерации
    elif action == "stats":
        await callback.answer()

        mod_repo = ModeratedMessageRepository(session)
        stats = await mod_repo.get_spam_statistics(days=7)

        text = (
            f"📊 <b>Статистика модерации за 7 дней</b>\n\n"
            f"📨 Всего сообщений: <b>{stats['total']}</b>\n"
            f"✅ Одобрено: <b>{stats['approved']}</b>\n"
            f"❌ Отклонено: <b>{stats['rejected']}</b>\n"
            f"⏳ На проверке: <b>{stats['pending']}</b>\n\n"
            f"💡 Используйте /modqueue для просмотра очереди"
        )
        if callback.message:
            await callback.message.edit_text(text=text, parse_mode="HTML")
        return

    # Пользователи
    elif action == "users":
        await callback.answer()
        text = "👤 <b>Пользователи</b>\n\nФункционал в разработке..."
        if callback.message:
            await callback.message.edit_text(text=text, parse_mode="HTML")
        return

    # Помощь
    elif action == "help":
        await callback.answer()
        text = (
            "ℹ️ <b>Помощь</b>\n\n"
            "<b>Доступные команды:</b>\n"
            "• /admin - панель администратора\n"
            "• /modqueue - очередь модерации\n\n"
            "<b>Модерация:</b>\n"
            "• Проверяйте очередь модерации\n"
            "• Одобряйте или отклоняйте отзывы\n"
            "• Банте спамеров при необходимости"
        )
        if callback.message:
            await callback.message.edit_text(text=text, parse_mode="HTML")
        return

    else:
        await callback.answer()
        text = "⚠️ Неизвестное действие"
        if callback.message:
            await callback.message.edit_text(text=text, parse_mode="HTML")
