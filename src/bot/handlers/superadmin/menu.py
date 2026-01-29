"""Хендлеры для супер-админ панели."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.main_menu import get_superadmin_menu, get_superadmin_panel_keyboard
from src.bot.keyboards.products import get_products_menu_keyboard, get_categories_manage_keyboard
from src.core.constants import CallbackPrefix
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.category import CategoryRepository
from src.utils.navigation import edit_message_with_navigation, NavigationStack

logger = get_logger(__name__)

router = Router(name="superadmin_menu")


def get_back_to_superadmin_keyboard() -> InlineKeyboardBuilder:
    """Создать клавиатуру с кнопкой 'Назад в супер-админ панель'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=CallbackPrefix.BACK),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu"),
    )
    return builder


@router.message(Command("superadmin"), IsSuperAdmin())
@router.message(F.text == "👑 Супер-админ панель", IsSuperAdmin())
async def cmd_superadmin(message: Message, user: User, state: FSMContext) -> None:
    """Команда /superadmin или кнопка "Супер-админ панель" - открыть супер-админ панель.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
        state: FSM контекст
    """
    logger.info("Super admin panel opened", user_id=user.id, role=user.role)

    # Очищаем историю навигации при входе в панель супер-админа
    await NavigationStack.clear(state)

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


@router.callback_query(F.data == "separator")
async def separator_handler(callback: CallbackQuery) -> None:
    """Handler for separator buttons (non-interactive)."""
    await callback.answer()


@router.callback_query(F.data.startswith("superadmin:"), IsAdmin())
async def process_superadmin_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка callback от супер-админ панели.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
        state: FSM контекст
    """
    from aiogram.exceptions import TelegramBadRequest

    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else None
    subaction = parts[2] if len(parts) > 2 else None

    # Возврат в главное меню супер-админа
    if action == "menu":
        await callback.answer()
        text = (
            f"👨‍💼 <b>Супер-админ панель</b>\n\n"
            f"Добро пожаловать, <b>{user.full_name}</b>!\n"
            f"Роль: <code>{user.role}</code>\n\n"
            f"У вас полный доступ ко всем функциям бота.\n\n"
            f"Выберите действие:"
        )
        if callback.message:
            # Проверяем, есть ли фото в сообщении
            if callback.message.photo:
                # Если есть фото, удаляем сообщение и отправляем новое
                try:
                    await callback.message.delete()
                    await callback.message.answer(
                        text=text,
                        reply_markup=get_superadmin_panel_keyboard(),
                        parse_mode="HTML",
                    )
                except TelegramBadRequest:
                    # Если не удалось удалить, просто отправляем новое
                    await callback.message.answer(
                        text=text,
                        reply_markup=get_superadmin_panel_keyboard(),
                        parse_mode="HTML",
                    )
            else:
                # Обычное редактирование текста
                await callback.message.edit_text(
                    text=text,
                    reply_markup=get_superadmin_panel_keyboard(),
                    parse_mode="HTML",
                )
        return

    # Товары
    if action == "products":
        if subaction == "add":
            # Переход к диалогу добавления товара
            # Меняем callback.data чтобы вызвался правильный обработчик
            callback.data = "prod_add_dialog"
            from src.bot.handlers.superadmin.products.add_dialog import start_add_product
            await start_add_product(callback, state)
            return
        else:
            # Меню управления товарами
            text = (
                "🛍 <b>Управление товарами</b>\n\n"
                "Выберите действие:"
            )
            keyboard = get_products_menu_keyboard()
            if callback.message:
                await edit_message_with_navigation(
                    callback=callback,
                    state=state,
                    text=text,
                    markup=keyboard,
                )
            return

    # Категории
    elif action == "categories":
        category_repo = CategoryRepository(session)
        categories = await category_repo.get_all()

        text = (
            f"📁 <b>Управление категориями</b>\n\n"
            f"Всего категорий: {len(categories)}\n\n"
            f"✅ - активна\n"
            f"🔗 - привязан thread_id"
        )
        keyboard = get_categories_manage_keyboard(categories)
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard,
            )
        return

    # Модерация
    elif action == "reviews" or action == "moderation":
        text = (
            "🔧 <b>Модерация</b>\n\n"
            "Доступные команды:\n"
            "• /modqueue - очередь модерации\n"
            "• /spam - управление спам-паттернами"
        )
        keyboard = get_back_to_superadmin_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard.as_markup(),
            )
        return

    # Управление админами
    elif action == "admins":
        # Перенаправление на меню управления админами
        from src.bot.handlers.superadmin.manage_admins import show_admins_list
        await show_admins_list(callback, session)
        return

    # Остальные действия
    elif action == "orders":
        # Показываем фильтры заказов
        from src.bot.keyboards.orders import get_admin_orders_filters_keyboard
        text = (
            "📋 <b>Управление заказами</b>\n\n"
            "Выберите статус заказов для просмотра:"
        )
        keyboard = get_admin_orders_filters_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard,
            )
        return
    elif action == "broadcast":
        # Перенаправление на меню рассылок
        from src.bot.handlers.superadmin.broadcast.history import show_broadcast_menu as broadcast_main
        await broadcast_main(callback, state)
        return
    elif action == "users":
        # Показываем меню управления пользователями
        from src.bot.keyboards.users import get_users_menu_keyboard
        text = (
            "👤 <b>Управление пользователями</b>\n\n"
            "Выберите действие:"
        )
        keyboard = get_users_menu_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard,
            )
        return
    elif action == "settings":
        # Настройки - показываем меню настроек
        from src.bot.keyboards.settings import get_settings_menu_keyboard

        text = (
            "⚙️ <b>Настройки бота</b>\n\n"
            "Выберите раздел для настройки:"
        )
        keyboard = get_settings_menu_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard,
            )
        return
    elif action == "stats":
        # Перенаправление на статистику
        from src.bot.handlers.superadmin.stats import cmd_stats
        # Создаем фейковое сообщение для вызова команды
        callback.message.text = "/stats"
        await cmd_stats(callback.message, user)
        await callback.answer()
        return
    elif action == "help":
        text = (
            "ℹ️ <b>Помощь</b>\n\n"
            "<b>Доступные команды:</b>\n"
            "• /superadmin - панель супер-админа\n"
            "• /products - управление товарами\n"
            "• /modqueue - очередь модерации\n"
            "• /spam - управление спам-паттернами\n\n"
            "<b>Управление товарами:</b>\n"
            "• Добавление через диалог\n"
            "• Загрузка из Excel/CSV файла\n"
            "• Редактирование и удаление\n"
            "• Публикация в канал\n\n"
            "<b>Модерация:</b>\n"
            "• Автоматическая проверка спама\n"
            "• Ручная модерация отзывов\n"
            "• Настройка спам-фильтров"
        )
        keyboard = get_back_to_superadmin_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard.as_markup(),
            )
        return
    else:
        text = "⚠️ Неизвестное действие"
        keyboard = get_back_to_superadmin_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard.as_markup(),
            )
        return
