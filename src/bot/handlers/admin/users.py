"""Управление пользователями в админ-панели."""

import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.users import (
    get_bonus_operations_keyboard,
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


def get_back_to_profile_keyboard(user_id: int):
    """Создать клавиатуру возврата к профилю.

    Args:
        user_id: ID пользователя

    Returns:
        Inline клавиатура
    """
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К профилю",
            callback_data=f"users:view:{user_id}",
        )
    )
    return builder.as_markup()


class UserSearchStates(StatesGroup):
    """Состояния поиска пользователей."""

    WAITING_QUERY = State()


class UserBonusStates(StatesGroup):
    """Состояния редактирования бонусов."""

    WAITING_ADD_AMOUNT = State()
    WAITING_SUBTRACT_AMOUNT = State()
    WAITING_SET_AMOUNT = State()
    WAITING_PURCHASE_PRICE = State()
    WAITING_DISCOUNT_PERCENT = State()


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
        f"<b>Бонусы:</b>\n"
        f"└ Баланс: <b>{float(user.bonus_balance):.2f}</b> ₽\n\n"
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

            # Получаем описание товаров в заказе
            items_desc = f"{order.total_items} товар(ов)" if order.items else "Нет товаров"
            date = order.created_at.strftime("%d.%m.%Y")
            total = float(order.total_price)

            text += f"{i}. {status_emoji} {items_desc} - {total:.0f}₽ - {date}\n"

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


@router.callback_query(F.data.startswith("users:edit_bonus:"), IsAdmin())
async def start_edit_user_bonus(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать редактирование бонусов пользователя."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    text = (
        f"💰 <b>Управление бонусами</b>\n\n"
        f"<b>Пользователь:</b> {user.full_name}\n"
        f"<b>Текущий баланс:</b> {float(user.bonus_balance):.2f} ₽\n\n"
        f"Выберите операцию:"
    )

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=get_bonus_operations_keyboard(user.id),
    )


# ==================== ОПЕРАЦИИ С БОНУСАМИ ====================


@router.callback_query(F.data.startswith("bonus:add:"), IsAdmin())
async def bonus_add_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать начисление бонусов."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    await state.update_data(bonus_target_user_id=user_id)

    text = (
        f"➕ <b>Начисление бонусов</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Текущий баланс:</b> {float(target_user.bonus_balance):.2f} ₽\n\n"
        f"Введите сумму для начисления:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard(f"users:edit_bonus:{user_id}"),
        parse_mode="HTML",
    )
    await state.set_state(UserBonusStates.WAITING_ADD_AMOUNT)
    await callback.answer()


@router.message(IsAdmin(), UserBonusStates.WAITING_ADD_AMOUNT, F.text)
async def bonus_add_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработка начисления бонусов."""
    data = await state.get_data()
    user_id = data.get("bonus_target_user_id")

    if not user_id:
        await message.answer(
            "❌ Ошибка: пользователь не найден",
            reply_markup=get_back_to_profile_keyboard(user_id) if user_id else None,
        )
        await state.clear()
        return

    # Сначала получаем пользователя для клавиатуры
    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return

    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nСумма должна быть положительной.",
                reply_markup=get_back_to_profile_keyboard(user_id),
                parse_mode="HTML",
            )
            return

        if amount > 1000000:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nСлишком большая сумма (максимум 1,000,000).",
                reply_markup=get_back_to_profile_keyboard(user_id),
                parse_mode="HTML",
            )
            return

    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\nНеверный формат числа.",
            reply_markup=get_back_to_profile_keyboard(user_id),
            parse_mode="HTML",
        )
        return

    old_balance = float(target_user.bonus_balance)
    new_balance = old_balance + amount
    target_user.bonus_balance = new_balance
    await session.commit()
    await state.clear()

    logger.info(
        "Bonuses added",
        target_user_id=target_user.id,
        amount=amount,
        old_balance=old_balance,
        new_balance=new_balance,
        admin_id=user.id,
    )

    text = (
        f"✅ <b>Бонусы начислены</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Начислено:</b> +{amount:.2f} ₽\n"
        f"<b>Было:</b> {old_balance:.2f} ₽\n"
        f"<b>Стало:</b> {new_balance:.2f} ₽"
    )

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К профилю",
            callback_data=f"users:view:{target_user.id}",
        )
    )

    await message.answer(text=text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("bonus:subtract:"), IsAdmin())
async def bonus_subtract_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать списание бонусов."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    await state.update_data(bonus_target_user_id=user_id)

    text = (
        f"➖ <b>Списание бонусов</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Текущий баланс:</b> {float(target_user.bonus_balance):.2f} ₽\n\n"
        f"Введите сумму для списания:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard(f"users:edit_bonus:{user_id}"),
        parse_mode="HTML",
    )
    await state.set_state(UserBonusStates.WAITING_SUBTRACT_AMOUNT)
    await callback.answer()


@router.message(IsAdmin(), UserBonusStates.WAITING_SUBTRACT_AMOUNT, F.text)
async def bonus_subtract_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработка списания бонусов."""
    data = await state.get_data()
    user_id = data.get("bonus_target_user_id")

    if not user_id:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return

    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nСумма должна быть положительной.",
                reply_markup=get_back_to_profile_keyboard(user_id),
                parse_mode="HTML",
            )
            return

    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\nНеверный формат числа.",
            reply_markup=get_back_to_profile_keyboard(user_id),
            parse_mode="HTML",
        )
        return

    old_balance = float(target_user.bonus_balance)

    if amount > old_balance:
        await message.answer(
            f"❌ <b>Ошибка</b>\n\n"
            f"Недостаточно бонусов!\n"
            f"На балансе: {old_balance:.2f} ₽\n"
            f"Попытка списать: {amount:.2f} ₽",
            reply_markup=get_back_to_profile_keyboard(user_id),
            parse_mode="HTML",
        )
        return

    new_balance = old_balance - amount
    target_user.bonus_balance = new_balance
    await session.commit()
    await state.clear()

    logger.info(
        "Bonuses subtracted",
        target_user_id=target_user.id,
        amount=amount,
        old_balance=old_balance,
        new_balance=new_balance,
        admin_id=user.id,
    )

    text = (
        f"✅ <b>Бонусы списаны</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Списано:</b> -{amount:.2f} ₽\n"
        f"<b>Было:</b> {old_balance:.2f} ₽\n"
        f"<b>Стало:</b> {new_balance:.2f} ₽"
    )

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К профилю",
            callback_data=f"users:view:{target_user.id}",
        )
    )

    await message.answer(text=text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("bonus:set:"), IsAdmin())
async def bonus_set_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать установку баланса."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    await state.update_data(bonus_target_user_id=user_id)

    text = (
        f"💰 <b>Установка баланса</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Текущий баланс:</b> {float(target_user.bonus_balance):.2f} ₽\n\n"
        f"Введите новый баланс:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard(f"users:edit_bonus:{user_id}"),
        parse_mode="HTML",
    )
    await state.set_state(UserBonusStates.WAITING_SET_AMOUNT)
    await callback.answer()


@router.message(IsAdmin(), UserBonusStates.WAITING_SET_AMOUNT, F.text)
async def bonus_set_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработка установки баланса."""
    data = await state.get_data()
    user_id = data.get("bonus_target_user_id")

    if not user_id:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
        return

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return

    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount < 0:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nСумма не может быть отрицательной.",
                reply_markup=get_back_to_profile_keyboard(user_id),
                parse_mode="HTML",
            )
            return

        if amount > 1000000:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nСлишком большая сумма (максимум 1,000,000).",
                reply_markup=get_back_to_profile_keyboard(user_id),
                parse_mode="HTML",
            )
            return

    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\nНеверный формат числа.",
            reply_markup=get_back_to_profile_keyboard(user_id),
            parse_mode="HTML",
        )
        return

    old_balance = float(target_user.bonus_balance)
    target_user.bonus_balance = amount
    await session.commit()
    await state.clear()

    logger.info(
        "Bonus balance set",
        target_user_id=target_user.id,
        old_balance=old_balance,
        new_balance=amount,
        admin_id=user.id,
    )

    text = (
        f"✅ <b>Баланс установлен</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Было:</b> {old_balance:.2f} ₽\n"
        f"<b>Стало:</b> {amount:.2f} ₽"
    )

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К профилю",
            callback_data=f"users:view:{target_user.id}",
        )
    )

    await message.answer(text=text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("bonus:discount:"), IsAdmin())
async def bonus_discount_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать списание со скидкой."""
    user_id = int(callback.data.split(":")[2])

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    await state.update_data(bonus_target_user_id=user_id)

    text = (
        f"🛍 <b>Списание со скидкой</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n"
        f"<b>Баланс бонусов:</b> {float(target_user.bonus_balance):.2f} ₽\n\n"
        f"Введите полную стоимость покупки:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard(f"users:edit_bonus:{user_id}"),
        parse_mode="HTML",
    )
    await state.set_state(UserBonusStates.WAITING_PURCHASE_PRICE)
    await callback.answer()


@router.message(IsAdmin(), UserBonusStates.WAITING_PURCHASE_PRICE, F.text)
async def bonus_discount_price(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка стоимости покупки."""
    data = await state.get_data()
    user_id = data.get("bonus_target_user_id")

    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nСтоимость должна быть положительной.",
                reply_markup=get_back_to_profile_keyboard(user_id) if user_id else None,
                parse_mode="HTML",
            )
            return

    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\nНеверный формат числа.",
            reply_markup=get_back_to_profile_keyboard(user_id) if user_id else None,
            parse_mode="HTML",
        )
        return

    await state.update_data(purchase_price=price)

    text = (
        f"🛍 <b>Списание со скидкой</b>\n\n"
        f"<b>Стоимость покупки:</b> {price:.2f} ₽\n\n"
        f"Введите процент скидки (например: 10 для 10%):"
    )

    await message.answer(text=text, parse_mode="HTML")
    await state.set_state(UserBonusStates.WAITING_DISCOUNT_PERCENT)


@router.message(IsAdmin(), UserBonusStates.WAITING_DISCOUNT_PERCENT, F.text)
async def bonus_discount_process(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработка процента скидки и списание бонусов."""
    data = await state.get_data()
    user_id = data.get("bonus_target_user_id")
    price = data.get("purchase_price")

    if not user_id or not price:
        await message.answer(
            "❌ Ошибка: данные не найдены",
            reply_markup=get_back_to_profile_keyboard(user_id) if user_id else None,
        )
        await state.clear()
        return

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)

    if not target_user:
        await message.answer(
            "❌ Пользователь не найден",
            reply_markup=get_back_to_profile_keyboard(user_id) if user_id else None,
        )
        await state.clear()
        return

    try:
        discount_percent = float(message.text.strip().replace(",", "."))
        if discount_percent <= 0 or discount_percent > 100:
            await message.answer(
                "❌ <b>Ошибка</b>\n\nПроцент должен быть от 0 до 100.",
                reply_markup=get_back_to_profile_keyboard(user_id),
                parse_mode="HTML",
            )
            return

    except ValueError:
        await message.answer(
            "❌ <b>Ошибка</b>\n\nНеверный формат числа.",
            reply_markup=get_back_to_profile_keyboard(user_id),
            parse_mode="HTML",
        )
        return

    # Расчет
    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount
    old_balance = float(target_user.bonus_balance)

    if discount_amount > old_balance:
        await message.answer(
            f"❌ <b>Недостаточно бонусов!</b>\n\n"
            f"<b>Стоимость:</b> {price:.2f} ₽\n"
            f"<b>Скидка {discount_percent}%:</b> {discount_amount:.2f} ₽\n"
            f"<b>На балансе:</b> {old_balance:.2f} ₽\n\n"
            f"Не хватает: {(discount_amount - old_balance):.2f} ₽",
            reply_markup=get_back_to_profile_keyboard(user_id),
            parse_mode="HTML",
        )
        await state.clear()
        return

    new_balance = old_balance - discount_amount
    target_user.bonus_balance = new_balance
    await session.commit()
    await state.clear()

    logger.info(
        "Bonuses used for discount purchase",
        target_user_id=target_user.id,
        purchase_price=price,
        discount_percent=discount_percent,
        discount_amount=discount_amount,
        final_price=final_price,
        old_balance=old_balance,
        new_balance=new_balance,
        admin_id=user.id,
    )

    text = (
        f"✅ <b>Покупка оформлена</b>\n\n"
        f"<b>Пользователь:</b> {target_user.full_name}\n\n"
        f"💰 <b>Расчет:</b>\n"
        f"├ Полная стоимость: {price:.2f} ₽\n"
        f"├ Скидка ({discount_percent}%): -{discount_amount:.2f} ₽\n"
        f"└ К оплате: <b>{final_price:.2f} ₽</b>\n\n"
        f"🎁 <b>Бонусы:</b>\n"
        f"├ Было: {old_balance:.2f} ₽\n"
        f"├ Списано: -{discount_amount:.2f} ₽\n"
        f"└ Осталось: <b>{new_balance:.2f} ₽</b>"
    )

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К профилю",
            callback_data=f"users:view:{target_user.id}",
        )
    )

    await message.answer(text=text, reply_markup=builder.as_markup(), parse_mode="HTML")
