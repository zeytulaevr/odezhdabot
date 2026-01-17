"""Общие обработчики команд бота."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.bot.keyboards.reply import get_main_keyboard
from src.core.constants import Messages
from src.core.logging import get_logger

logger = get_logger(__name__)

# Создание роутера для общих команд
router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start.

    Args:
        message: Входящее сообщение
    """
    user = message.from_user
    logger.info("User started bot", user_id=user.id, username=user.username)

    await message.answer(
        text=Messages.START,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help.

    Args:
        message: Входящее сообщение
    """
    logger.info("User requested help", user_id=message.from_user.id)

    await message.answer(
        text=Messages.HELP,
        parse_mode="HTML",
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    """Обработчик команды /menu - показать главное меню.

    Args:
        message: Входящее сообщение
    """
    await message.answer(
        text="📱 Главное меню:",
        reply_markup=get_main_keyboard(),
    )
