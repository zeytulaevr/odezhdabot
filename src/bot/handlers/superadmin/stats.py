"""Обработчики статистики для супер-админов."""

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.core.logging import get_logger
from src.services.monitoring_service import MonitoringService
from src.utils.navigation import edit_message_with_navigation

logger = get_logger(__name__)

router = Router(name="superadmin_stats")


def get_stats_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню статистики."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 Общая статистика",
            callback_data="stats_general",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📅 За сегодня",
            callback_data="stats_today",
        ),
        InlineKeyboardButton(
            text="📅 За неделю",
            callback_data="stats_week",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="📅 За месяц",
            callback_data="stats_month",
        ),
        InlineKeyboardButton(
            text="💚 Health Check",
            callback_data="stats_health",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back",
        )
    )

    return builder.as_markup()


def format_general_stats(stats: dict) -> str:
    """Форматировать общую статистику.

    Args:
        stats: Словарь со статистикой

    Returns:
        Отформатированная строка
    """
    users = stats.get("users", {})
    orders = stats.get("orders", {})
    products = stats.get("products", {})
    broadcasts = stats.get("broadcasts", {})
    reviews = stats.get("reviews", {})

    text = "📊 <b>Общая статистика системы</b>\n\n"

    # Пользователи
    text += "👥 <b>Пользователи:</b>\n"
    text += f"• Всего: {users.get('total', 0)}\n"
    text += f"• Активны (24ч): {users.get('active_24h', 0)}\n"
    text += f"• Активны (7д): {users.get('active_7d', 0)}\n"
    text += f"• Новых (24ч): {users.get('new_24h', 0)}\n"
    text += f"• Новых (7д): {users.get('new_7d', 0)}\n"

    # Роли
    by_role = users.get("by_role", {})
    if by_role:
        text += f"\nПо ролям:\n"
        for role, count in by_role.items():
            text += f"  - {role}: {count}\n"

    text += f"\n• Заблокировано: {users.get('banned', 0)}\n"

    # Заказы
    text += "\n📦 <b>Заказы:</b>\n"
    text += f"• Всего: {orders.get('total', 0)}\n"
    text += f"• Новых (24ч): {orders.get('new_24h', 0)}\n"
    text += f"• Новых (7д): {orders.get('new_7d', 0)}\n"
    text += f"• Конверсия: {orders.get('conversion_rate', 0)}%\n"

    # По статусам
    by_status = orders.get("by_status", {})
    if by_status:
        text += f"\nПо статусам:\n"
        status_names = {
            "new": "Новые",
            "processing": "В обработке",
            "paid": "Оплачены",
            "shipped": "Отправлены",
            "completed": "Выполнены",
            "cancelled": "Отменены",
        }
        for status, count in by_status.items():
            name = status_names.get(status, status)
            text += f"  - {name}: {count}\n"

    # Товары
    text += "\n🛍 <b>Товары:</b>\n"
    text += f"• Всего: {products.get('total', 0)}\n"
    text += f"• Активных: {products.get('active', 0)}\n"
    text += f"• Неактивных: {products.get('inactive', 0)}\n"
    text += f"• Без категории: {products.get('no_category', 0)}\n"

    # Рассылки
    text += "\n📢 <b>Рассылки:</b>\n"
    text += f"• Всего: {broadcasts.get('total', 0)}\n"
    text += f"• Отправлено сообщений: {broadcasts.get('total_sent', 0)}\n"
    text += f"• Доставлено: {broadcasts.get('total_success', 0)}\n"
    text += f"• Ошибок: {broadcasts.get('total_failed', 0)}\n"
    text += f"• Success rate: {broadcasts.get('success_rate', 0)}%\n"

    # Отзывы
    text += "\n⭐ <b>Отзывы:</b>\n"
    text += f"• Всего: {reviews.get('total', 0)}\n"
    text += f"• Одобрено: {reviews.get('approved', 0)}\n"
    text += f"• Отклонено: {reviews.get('rejected', 0)}\n"
    text += f"• На модерации: {reviews.get('pending', 0)}\n"

    # Timestamp
    text += f"\n🕒 Обновлено: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

    return text


def format_period_stats(stats: dict, period_name: str) -> str:
    """Форматировать статистику за период.

    Args:
        stats: Словарь со статистикой
        period_name: Название периода

    Returns:
        Отформатированная строка
    """
    period = stats.get("period", {})
    users = stats.get("users", {})
    orders = stats.get("orders", {})
    products = stats.get("products", {})
    broadcasts = stats.get("broadcasts", {})

    text = f"📅 <b>Статистика за {period_name}</b>\n\n"
    text += f"Период: {period.get('start', '')} - {period.get('end', '')}\n"
    text += f"Дней: {period.get('days', 0)}\n\n"

    # Пользователи
    text += "👥 <b>Пользователи:</b>\n"
    text += f"• Новых: {users.get('new', 0)}\n"
    text += f"• Активных: {users.get('active', 0)}\n\n"

    # Заказы
    text += "📦 <b>Заказы:</b>\n"
    text += f"• Новых: {orders.get('new', 0)}\n"
    text += f"• Выполнено: {orders.get('completed', 0)}\n"

    # По статусам
    by_status = orders.get("by_status", {})
    if by_status:
        text += f"\nПо статусам:\n"
        status_names = {
            "new": "Новые",
            "processing": "В обработке",
            "paid": "Оплачены",
            "shipped": "Отправлены",
            "completed": "Выполнены",
            "cancelled": "Отменены",
        }
        for status, count in by_status.items():
            name = status_names.get(status, status)
            text += f"  - {name}: {count}\n"

    # Товары
    text += "\n🛍 <b>Товары:</b>\n"
    text += f"• Новых: {products.get('new', 0)}\n\n"

    # Рассылки
    text += "📢 <b>Рассылки:</b>\n"
    text += f"• Новых: {broadcasts.get('new', 0)}\n"
    text += f"• Отправлено: {broadcasts.get('sent', 0)}\n"
    text += f"• Доставлено: {broadcasts.get('success', 0)}\n"

    return text


@router.callback_query(F.data == "superadmin:stats", IsSuperAdmin())
async def show_stats_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать меню статистики.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    text = (
        "📊 <b>Статистика и мониторинг</b>\n\n"
        "Выберите раздел для просмотра:"
    )

    keyboard = get_stats_menu_keyboard()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data == "stats_general", IsSuperAdmin())
async def show_general_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать общую статистику.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await callback.answer("Собираю статистику...")

    monitoring = MonitoringService(session)
    stats = await monitoring.get_system_stats()

    text = format_general_stats(stats)
    keyboard = get_stats_menu_keyboard()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )

    logger.info("General stats viewed", user_id=callback.from_user.id)


@router.callback_query(F.data == "stats_today", IsSuperAdmin())
async def show_today_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать статистику за сегодня.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await callback.answer("Собираю статистику...")

    # За сегодня (с 00:00)
    now = datetime.utcnow()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    monitoring = MonitoringService(session)
    stats = await monitoring.get_period_stats(start_date, end_date)

    text = format_period_stats(stats, "сегодня")
    keyboard = get_stats_menu_keyboard()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data == "stats_week", IsSuperAdmin())
async def show_week_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать статистику за неделю.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await callback.answer("Собираю статистику...")

    # За последние 7 дней
    now = datetime.utcnow()
    start_date = now - timedelta(days=7)
    end_date = now

    monitoring = MonitoringService(session)
    stats = await monitoring.get_period_stats(start_date, end_date)

    text = format_period_stats(stats, "неделю")
    keyboard = get_stats_menu_keyboard()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data == "stats_month", IsSuperAdmin())
async def show_month_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать статистику за месяц.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await callback.answer("Собираю статистику...")

    # За последние 30 дней
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)
    end_date = now

    monitoring = MonitoringService(session)
    stats = await monitoring.get_period_stats(start_date, end_date)

    text = format_period_stats(stats, "месяц")
    keyboard = get_stats_menu_keyboard()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data == "stats_health", IsSuperAdmin())
async def show_health_check(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать health check системы.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await callback.answer("Проверяю состояние системы...")

    monitoring = MonitoringService(session)
    health = await monitoring.get_health_check()

    status = health.get("status", "unknown")
    status_emoji = "✅" if status == "healthy" else "❌"

    text = f"{status_emoji} <b>Health Check</b>\n\n"
    text += f"Статус: <b>{status.upper()}</b>\n"
    text += f"Время: {health.get('timestamp', '')}\n\n"

    components = health.get("components", {})
    text += "<b>Компоненты:</b>\n"

    for component, info in components.items():
        comp_status = info.get("status", "unknown")
        comp_emoji = "✅" if comp_status == "healthy" else "❌"
        text += f"{comp_emoji} {component}: {comp_status}\n"

        if "error" in info:
            text += f"  Error: {info['error']}\n"

    keyboard = get_stats_menu_keyboard()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )

    logger.info(
        "Health check viewed",
        user_id=callback.from_user.id,
        status=status,
    )
