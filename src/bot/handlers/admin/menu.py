"""Хендлеры для админ-панели."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.main_menu import get_admin_menu, get_admin_panel_keyboard
from src.core.constants import CallbackPrefix
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.moderated_message import ModeratedMessageRepository
from src.utils.navigation import NavigationStack, edit_message_with_navigation

logger = get_logger(__name__)

router = Router(name="admin_menu")


def get_back_to_admin_keyboard() -> InlineKeyboardBuilder:
    """Создать клавиатуру с кнопкой 'Назад в админ-панель'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=CallbackPrefix.BACK),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu"),
    )
    return builder


@router.message(Command("admin"), IsAdmin())
@router.message(F.text == "📋 Админ-панель", IsAdmin())
async def cmd_admin(message: Message, user: User, state: FSMContext) -> None:
    """Команда /admin или кнопка "Админ-панель" - открыть админ-панель.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
        state: FSM контекст
    """
    logger.info("Admin panel opened", user_id=user.id, role=user.role)

    # Очищаем историю навигации при входе в админ-панель
    await NavigationStack.clear(state)

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

    from src.bot.keyboards.orders import get_admin_orders_filters_keyboard

    text = (
        "📋 <b>Управление заказами</b>\n\n"
        "Выберите статус заказов для просмотра:"
    )

    await message.answer(
        text=text,
        reply_markup=get_admin_orders_filters_keyboard(),
        parse_mode="HTML",
    )


@router.message(F.text == "📊 Статистика", IsAdmin())
async def show_statistics(message: Message, user: User, session: AsyncSession) -> None:
    """Показать статистику.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
        session: Сессия БД
    """
    logger.info("Statistics opened", user_id=user.id)

    from src.database.repositories.order import OrderRepository
    from src.database.repositories.user import UserRepository

    # Получаем статистику
    order_repo = OrderRepository(session)
    user_repo = UserRepository(session)

    # Статистика заказов
    all_orders = await order_repo.get_all_orders(limit=10000)
    new_orders = [o for o in all_orders if o.status == "new"]
    processing_orders = [o for o in all_orders if o.status in ["processing", "paid", "shipped"]]
    completed_orders = [o for o in all_orders if o.status == "completed"]

    # Статистика пользователей
    total_users = await user_repo.count_users()
    all_users = await user_repo.get_all_users(limit=10000)
    active_users = [u for u in all_users if not u.is_banned]
    banned_users = [u for u in all_users if u.is_banned]

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"📦 Всего заказов: <code>{len(all_orders)}</code>\n"
        f"🆕 Новых: <code>{len(new_orders)}</code>\n"
        f"🔄 В обработке: <code>{len(processing_orders)}</code>\n"
        f"✅ Завершённых: <code>{len(completed_orders)}</code>\n\n"
        f"👥 Всего пользователей: <code>{total_users}</code>\n"
        f"🟢 Активных: <code>{len(active_users)}</code>\n"
        f"🔴 Забаненных: <code>{len(banned_users)}</code>"
    )

    await message.answer(text=text, parse_mode="HTML")


@router.message(F.text == "👤 Пользователи", IsAdmin())
async def show_users_menu_reply(message: Message, user: User) -> None:
    """Показать меню пользователей из reply клавиатуры.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    logger.info("Users menu opened", user_id=user.id)

    from src.bot.keyboards.users import get_users_menu_keyboard

    text = (
        "👤 <b>Управление пользователями</b>\n\n"
        "Выберите действие:"
    )

    await message.answer(
        text=text,
        reply_markup=get_users_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:"), IsAdmin())
async def process_admin_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка callback от админ-панели.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
        state: FSM контекст
    """
    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else None
    subaction = parts[2] if len(parts) > 2 else None

    # Возврат в главное меню админки
    if action == "menu":
        await callback.answer()
        text = (
            f"👨‍💼 <b>Админ-панель</b>\n\n"
            f"Добро пожаловать, <b>{user.full_name}</b>!\n"
            f"Роль: <code>{user.role}</code>\n\n"
            f"Выберите действие:"
        )
        if callback.message:
            await callback.message.edit_text(
                text=text,
                reply_markup=get_admin_panel_keyboard(),
                parse_mode="HTML",
            )
        return

    # Товары - показываем меню управления товарами
    if action == "products":
        from src.bot.keyboards.products import get_products_menu_keyboard
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

    # Заказы - показываем фильтры заказов
    elif action == "orders":
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

    # Статистика модерации
    elif action == "stats":
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
        keyboard = get_back_to_admin_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard.as_markup(),
            )
        return

    # Пользователи - показываем меню управления пользователями
    elif action == "users":
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

    # Помощь
    elif action == "help":
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
        keyboard = get_back_to_admin_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard.as_markup(),
            )
        return

    else:
        await callback.answer()
        text = "⚠️ Неизвестное действие"
        keyboard = get_back_to_admin_keyboard()
        if callback.message:
            await edit_message_with_navigation(
                callback=callback,
                state=state,
                text=text,
                markup=keyboard.as_markup(),
            )
