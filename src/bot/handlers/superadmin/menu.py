"""Хендлеры для супер-админ панели."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.main_menu import get_superadmin_menu, get_superadmin_panel_keyboard
from src.core.logging import get_logger
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="superadmin_menu")


@router.message(Command("superadmin"), IsSuperAdmin())
async def cmd_superadmin(message: Message, user: User) -> None:
    """Команда /superadmin - открыть супер-админ панель.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Super admin panel opened", user_id=user.id, role=user.role)

    text = (
        f"👨‍💼 <b>Супер-админ панель</b>\n\n"
        f"Добро пожаловать, <b>{user.full_name}</b>!\n"
        f"Роль: <code>{user.role}</code>\n\n"
        f"У вас полный доступ ко всем функциям бота.\n\n"
        f"Выберите действие:"
    )

    await message.answer(
        text=text,
        reply_markup=get_superadmin_panel_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📦 Товары", IsSuperAdmin())
async def show_products_menu(message: Message, user: User) -> None:
    """Показать меню управления товарами.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Products menu opened", user_id=user.id)

    text = (
        "📦 <b>Управление товарами</b>\n\n"
        "Здесь вы можете:\n"
        "• Добавить новый товар\n"
        "• Редактировать информацию о товаре\n"
        "• Удалить товар\n"
        "• Управлять категориями"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.message(F.text == "📢 Рассылка", IsSuperAdmin())
async def show_broadcast_menu(message: Message, user: User) -> None:
    """Показать меню рассылок.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Broadcast menu opened", user_id=user.id)

    text = (
        "📢 <b>Рассылки</b>\n\n"
        "Создайте рассылку для пользователей:\n"
        "• Всем пользователям\n"
        "• По фильтрам (роль, активность)\n"
        "• История рассылок"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.message(F.text == "🔧 Модерация", IsSuperAdmin())
async def show_moderation_menu(message: Message, user: User) -> None:
    """Показать меню модерации.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Moderation menu opened", user_id=user.id)

    text = (
        "🔧 <b>Модерация</b>\n\n"
        "Доступные функции:\n"
        "• Модерация отзывов\n"
        "• Управление спам-фильтрами\n"
        "• Просмотр логов администраторов"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.message(F.text == "⚙️ Настройки", IsSuperAdmin())
async def show_settings_menu(message: Message, user: User) -> None:
    """Показать меню настроек.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Settings menu opened", user_id=user.id)

    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        "Доступные настройки:\n"
        "• Управление администраторами\n"
        "• Настройка канала и тредов\n"
        "• Резервное копирование БД\n"
        "• Параметры бота"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.callback_query(F.data.startswith("superadmin:"), IsSuperAdmin())
async def process_superadmin_callback(callback: CallbackQuery, user: User) -> None:
    """Обработка callback от супер-админ панели.

    Args:
        callback: Callback query
        user: Пользователь из БД
    """
    await callback.answer()

    action = callback.data.split(":")[1] if ":" in callback.data else None

    if action == "products":
        text = "📦 <b>Товары</b>\n\nФункционал в разработке..."
    elif action == "broadcast":
        text = "📢 <b>Рассылка</b>\n\nФункционал в разработке..."
    elif action == "moderation":
        text = "🔧 <b>Модерация</b>\n\nФункционал в разработке..."
    elif action == "settings":
        text = "⚙️ <b>Настройки</b>\n\nФункционал в разработке..."
    else:
        text = "⚠️ Неизвестное действие"

    if callback.message:
        await callback.message.edit_text(text=text, parse_mode="HTML")
