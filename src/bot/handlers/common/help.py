"""Хендлер помощи для всех пользователей."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="help")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message, user: User | None = None) -> None:
    """Команда /help - показать справку.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД (может быть None)
    """
    logger.info("Help command", user_id=user.id if user else None)

    # Базовая справка для всех
    base_help = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        "<b>Для покупателей:</b>\n"
        "📦 Каталог - просмотр товаров\n"
        "🛍 Мои заказы - история заказов\n\n"
    )

    # Дополнительная информация в зависимости от роли
    if user and user.role == UserRole.ADMIN:
        admin_help = (
            "<b>Команды администратора:</b>\n"
            "/admin - Админ-панель\n"
            "📋 Заказы - управление заказами\n"
            "📊 Статистика - статистика бота\n"
            "👤 Пользователи - управление пользователями\n\n"
        )
        text = base_help + admin_help
    elif user and user.role == UserRole.SUPER_ADMIN:
        superadmin_help = (
            "<b>Команды супер-администратора:</b>\n"
            "/superadmin - Супер-админ панель\n"
            "📦 Товары - управление каталогом\n"
            "📢 Рассылка - создание рассылок\n"
            "🔧 Модерация - модерация контента\n"
            "⚙️ Настройки - настройки бота\n\n"
            "<b>+ все функции администратора</b>\n\n"
        )
        text = base_help + superadmin_help
    else:
        text = base_help

    # Контактная информация
    contact_info = (
        "<b>Нужна помощь?</b>\n"
        "Свяжитесь с поддержкой: @support\n"
        "Часы работы: Пн-Пт, 10:00-18:00"
    )

    text += contact_info

    await message.answer(text=text, parse_mode="HTML")
