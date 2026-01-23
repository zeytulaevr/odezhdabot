"""Управление пользователями в админ-панели."""

import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.users import (
    get_user_ban_confirm_keyboard,
    get_user_profile_keyboard,
    get_users_list_keyboard,
    get_users_menu_keyboard,
)
from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.order import OrderRepository
from src.database.repositories.user import UserRepository
from src.utils.cancel_handler import cancel_action_and_return_to_menu, get_cancel_keyboard
from src.utils.navigation import edit_message_with_navigation

logger = get_logger(__name__)

router = Router(name="admin_users")

USERS_PER_PAGE = 10


class UserSearchStates(StatesGroup):
    """Состояния поиска пользователей."""

    WAITING_QUERY = State()


def format_role_name(role: str) -> str:
    """Форматирование названия роли."""
    role_names = {
        UserRole.SUPER_ADMIN.value: "👑 Супер-администратор",
        UserRole.ADMIN.value: "👤 Администратор",
        UserRole.MODERATOR.value: "🛡 Модератор",
        UserRole.USER.value: "👥 Пользователь",
        UserRole.BANNED.value: "🚫 Заблокирован",
    }
    return role_names.get(role, role)


@router.callback_query(F.data == "users:menu", IsAdmin())
async def show_users_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать меню управления пользователями."""
    text = (
        "👤 <b>Управление пользователями</b>\n\n"
        "Выберите действие:"
    )

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=get_users_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("users:list:"), IsAdmin())
async def show_users_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать список пользователей."""
    page = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)

    # Получаем общее количество пользователей
    total_users = await user_repo.count_users()
    total_pages = math.ceil(total_users / USERS_PER_PAGE)

    # Получаем пользователей для текущей страницы
    users = await user_repo.get_all_users(
        skip=page * USERS_PER_PAGE,
        limit=USERS_PER_PAGE,
        order_by="created_at",
    )

    if not users:
        text = "📭 <b>Пользователи не найдены</b>"
        keyboard = get_users_menu_keyboard()
    else:
        text = (
            f"👥 <b>Список пользователей</b>\n\n"
            f"Всего пользователей: <b>{total_users}</b>\n"
            f"Страница: {page + 1} из {total_pages}\n\n"
            f"Нажмите на пользователя для просмотра профиля"
        )
        keyboard = get_users_list_keyboard(users, page, total_pages)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data.startswith("users:view:"), IsAdmin())
async def show_user_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать профиль пользователя."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Получаем статистику по заказам
    order_repo = OrderRepository(session)
    orders = await order_repo.get_user_orders(user_id=user.id, limit=1000)
    orders_count = len(orders)

    # Подсчёт статусов заказов
    completed_orders = len([o for o in orders if o.status == "completed"])
    active_orders = len([o for o in orders if o.status in ["new", "processing", "paid", "shipped"]])

    # Форматирование данных
    status = "🚫 Заблокирован" if user.is_banned else "✅ Активен"
    username_str = f"@{user.username}" if user.username else "—"
    phone_str = user.phone if user.phone else "—"
    last_active = user.last_active_at.strftime("%d.%m.%Y %H:%M") if user.last_active_at else "—"
    registered = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "—"

    text = (
        f"👤 <b>Профиль пользователя</b>\n\n"
        f"<b>Основная информация:</b>\n"
        f"├ ID: <code>{user.telegram_id}</code>\n"
        f"├ Имя: <b>{user.full_name}</b>\n"
        f"├ Username: {username_str}\n"
        f"├ Телефон: {phone_str}\n"
        f"├ Роль: {format_role_name(user.role)}\n"
        f"└ Статус: {status}\n\n"
        f"<b>Активность:</b>\n"
        f"├ Дата регистрации: {registered}\n"
        f"└ Последняя активность: {last_active}\n\n"
        f"<b>Статистика заказов:</b>\n"
        f"├ Всего заказов: <b>{orders_count}</b>\n"
        f"├ Завершённых: <b>{completed_orders}</b>\n"
        f"└ Активных: <b>{active_orders}</b>"
    )

    keyboard = get_user_profile_keyboard(user)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data == "users:search", IsAdmin())
async def start_user_search(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать поиск пользователя."""
    text = (
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите:\n"
        "• Имя пользователя\n"
        "• Username (с @ или без)\n"
        "• Telegram ID\n\n"
        "Поиск работает по частичному совпадению"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard("cancel_user_search"),
        parse_mode="HTML",
    )
    await state.set_state(UserSearchStates.WAITING_QUERY)
    await callback.answer()


@router.message(IsAdmin(), UserSearchStates.WAITING_QUERY, F.text)
async def process_user_search(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка поискового запроса."""
    query = message.text.strip()

    # Убираем @ если есть
    if query.startswith("@"):
        query = query[1:]

    user_repo = UserRepository(session)
    users = await user_repo.search_users(query, limit=20)

    await state.clear()

    if not users:
        text = (
            f"🔍 <b>Результаты поиска: \"{query}\"</b>\n\n"
            f"❌ Пользователи не найдены"
        )
        keyboard = get_users_menu_keyboard()
    else:
        text = (
            f"🔍 <b>Результаты поиска: \"{query}\"</b>\n\n"
            f"Найдено: <b>{len(users)}</b> пользователей\n\n"
            f"Нажмите на пользователя для просмотра профиля"
        )
        keyboard = get_users_list_keyboard(users, page=0, total_pages=1)

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cancel_user_search", IsAdmin())
async def cancel_user_search_callback(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Отмена поиска пользователя."""
    await cancel_action_and_return_to_menu(
        callback=callback,
        state=state,
        user=user,
        cancel_message="❌ Поиск отменён",
    )


@router.callback_query(F.data.startswith("users:ban:"), IsAdmin())
async def confirm_ban_user(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Подтверждение блокировки пользователя."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    if user.is_super_admin:
        await callback.answer(
            "⚠️ Нельзя заблокировать супер-администратора",
            show_alert=True,
        )
        return

    text = (
        f"⚠️ <b>Подтверждение блокировки</b>\n\n"
        f"Вы уверены, что хотите заблокировать пользователя?\n\n"
        f"<b>{user.full_name}</b>\n"
        f"ID: <code>{user.telegram_id}</code>\n\n"
        f"Пользователь не сможет использовать бота."
    )

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=get_user_ban_confirm_keyboard(user.id),
    )


@router.callback_query(F.data.startswith("users:ban_confirm:"), IsAdmin())
async def ban_user(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    admin_user: User,
) -> None:
    """Заблокировать пользователя."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    user = await user_repo.ban_user(user_id)

    if not user:
        await callback.answer("❌ Ошибка блокировки", show_alert=True)
        return

    await session.commit()
    await callback.answer("✅ Пользователь заблокирован", show_alert=True)

    logger.info(
        "User banned",
        user_id=user.id,
        banned_by=admin_user.id,
    )

    # Показываем обновлённый профиль
    callback.data = f"users:view:{user.id}"
    await show_user_profile(callback, session, state)


@router.callback_query(F.data.startswith("users:unban:"), IsAdmin())
async def unban_user(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    admin_user: User,
) -> None:
    """Разблокировать пользователя."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    user = await user_repo.unban_user(user_id)

    if not user:
        await callback.answer("❌ Ошибка разблокировки", show_alert=True)
        return

    await session.commit()
    await callback.answer("✅ Пользователь разблокирован", show_alert=True)

    logger.info(
        "User unbanned",
        user_id=user.id,
        unbanned_by=admin_user.id,
    )

    # Показываем обновлённый профиль
    callback.data = f"users:view:{user.id}"
    await show_user_profile(callback, session, state)


@router.callback_query(F.data.startswith("users:orders:"), IsAdmin())
async def show_user_orders(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать заказы пользователя."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    order_repo = OrderRepository(session)
    orders = await order_repo.get_user_orders(user_id=user.id, limit=50)

    if not orders:
        text = (
            f"🛍 <b>Заказы пользователя</b>\n\n"
            f"<b>{user.full_name}</b>\n"
            f"ID: <code>{user.telegram_id}</code>\n\n"
            f"❌ У пользователя нет заказов"
        )
    else:
        text = (
            f"🛍 <b>Заказы пользователя</b>\n\n"
            f"<b>{user.full_name}</b>\n"
            f"ID: <code>{user.telegram_id}</code>\n\n"
            f"Всего заказов: <b>{len(orders)}</b>\n\n"
        )

        # Показываем последние 10 заказов
        for i, order in enumerate(orders[:10], 1):
            status_emoji = {
                "new": "🆕",
                "processing": "⏳",
                "paid": "💰",
                "shipped": "📦",
                "completed": "✅",
                "cancelled": "❌",
            }.get(order.status, "❓")

            product_name = order.product.name if order.product else "Неизвестный товар"
            date = order.created_at.strftime("%d.%m.%Y")

            text += f"{i}. {status_emoji} {product_name} - {date}\n"

        if len(orders) > 10:
            text += f"\n... и ещё {len(orders) - 10} заказов"

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К профилю",
            callback_data=f"users:view:{user.id}",
        )
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu")
    )

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=builder.as_markup(),
    )
