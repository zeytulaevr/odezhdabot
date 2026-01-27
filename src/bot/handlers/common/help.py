"""Хендлер помощи для всех пользователей."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.main_menu import get_back_button
from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.bot_settings import BotSettings
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


@router.callback_query(F.data.in_(["user:help", "admin:help", "superadmin:help"]))
async def handle_help_button(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Обработчик inline кнопок помощи.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
    """
    logger.info("Help button pressed", user_id=user.id, callback_data=callback.data)

    # Получаем настройки бота для custom help message
    settings = await BotSettings.get_settings(session)
    custom_help = settings.help_message
    custom_help_media = settings.help_message_media

    # Если есть custom help message, используем его
    if custom_help:
        # Если есть медиа, отправляем с медиа
        if custom_help_media:
            try:
                # Пытаемся определить тип медиа и отправить соответственно
                await callback.message.delete()
                await callback.bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=custom_help_media,
                    caption=custom_help,
                    reply_markup=get_back_button("back_to_menu"),
                    parse_mode="HTML",
                )
                await callback.answer()
                return
            except Exception as e:
                logger.warning(f"Failed to send help message with media: {e}")
                # Если не получилось отправить как фото, пробуем как видео
                try:
                    await callback.message.delete()
                    await callback.bot.send_video(
                        chat_id=callback.message.chat.id,
                        video=custom_help_media,
                        caption=custom_help,
                        reply_markup=get_back_button("back_to_menu"),
                        parse_mode="HTML",
                    )
                    await callback.answer()
                    return
                except Exception as e2:
                    logger.error(f"Failed to send help message as video: {e2}")
                    # Если не получилось, отправляем только текст

        # Отправляем только текст
        if callback.message:
            await callback.message.edit_text(
                text=custom_help,
                reply_markup=get_back_button("back_to_menu"),
                parse_mode="HTML",
            )
        await callback.answer()
        return

    # Используем дефолтное сообщение помощи
    base_help = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        "<b>Для покупателей:</b>\n"
        "📦 Каталог - просмотр товаров\n"
        "🛍 Мои заказы - история заказов\n"
        "🛒 Корзина - ваша корзина покупок\n\n"
    )

    # Дополнительная информация в зависимости от роли
    if user.role == UserRole.ADMIN:
        admin_help = (
            "<b>Команды администратора:</b>\n"
            "/admin - Админ-панель\n"
            "📋 Заказы - управление заказами\n"
            "📊 Статистика - статистика бота\n"
            "👤 Пользователи - управление пользователями\n\n"
        )
        text = base_help + admin_help
    elif user.role == UserRole.SUPER_ADMIN:
        superadmin_help = (
            "<b>Команды супер-администратора:</b>\n"
            "/superadmin - Супер-админ панель\n"
            "📦 Товары - управление каталогом\n"
            "📢 Рассылка - создание рассылок\n"
            "🔧 Модерация - модерация контента\n"
            "⚙️ Настройки - настройки бота\n"
            "👥 Админы - управление администраторами\n\n"
            "<b>+ все функции администратора</b>\n\n"
        )
        text = base_help + superadmin_help
    else:
        text = base_help

    # Контактная информация
    contact_info = (
        "<b>Нужна помощь?</b>\n"
        "Свяжитесь с поддержкой через меню"
    )

    text += contact_info

    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_back_button("back_to_menu"),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def handle_back_to_menu(
    callback: CallbackQuery,
    user: User,
) -> None:
    """Обработчик кнопки 'Назад в меню' из помощи.

    Args:
        callback: Callback query
        user: Пользователь из БД
    """
    from src.bot.keyboards.main_menu import (
        get_admin_panel_keyboard,
        get_superadmin_panel_keyboard,
        get_user_menu,
    )

    # Определяем меню в зависимости от роли
    if user.role == UserRole.SUPER_ADMIN:
        menu_markup = get_superadmin_panel_keyboard()
        menu_text = (
            "👑 <b>Супер-админ панель</b>\n\n"
            f"Добро пожаловать, <b>{user.full_name}</b>!\n"
            f"Роль: <code>{user.role}</code>\n\n"
            "У вас полный доступ ко всем функциям бота.\n\n"
            "Выберите действие:"
        )
    elif user.role == UserRole.ADMIN:
        menu_markup = get_admin_panel_keyboard()
        menu_text = (
            "👨‍💼 <b>Админ-панель</b>\n\n"
            f"Добро пожаловать, <b>{user.full_name}</b>!\n"
            f"Роль: <code>{user.role}</code>\n\n"
            "Выберите действие:"
        )
    else:
        menu_markup = get_user_menu()
        menu_text = "Выберите раздел:"

    if callback.message:
        await callback.message.edit_text(
            text=menu_text,
            reply_markup=menu_markup,
            parse_mode="HTML",
        )
    await callback.answer()
