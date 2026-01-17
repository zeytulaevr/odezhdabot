"""Хендлер команды /start для обычных пользователей."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.bot.keyboards.main_menu import get_user_menu
from src.core.logging import get_logger
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="user_start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User | None = None) -> None:
    """Обработчик команды /start для пользователей.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    if not user:
        logger.error("User not found in start handler")
        await message.answer("❌ Ошибка авторизации. Попробуйте позже.")
        return

    logger.info("User started bot", user_id=user.id, telegram_id=user.telegram_id)

    # Приветственное сообщение
    greeting = (
        f"👋 <b>Добро пожаловать, {user.full_name}!</b>\n\n"
        "🛍 <b>Магазин одежды</b>\n\n"
        "Здесь вы можете:\n"
        "📦 Просмотреть каталог товаров\n"
        "🛍 Оформить и отслеживать заказы\n"
        "💬 Получить помощь и поддержку\n\n"
        "Выберите нужный раздел в меню ниже ⬇️"
    )

    await message.answer(
        text=greeting,
        reply_markup=get_user_menu(),
        parse_mode="HTML",
    )
