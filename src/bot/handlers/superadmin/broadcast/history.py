"""История и статистика рассылок."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.broadcast import (
    get_broadcast_detail_keyboard,
    get_broadcast_history_keyboard,
    get_broadcast_main_menu,
)
from src.core.logging import get_logger
from src.services.broadcast_service import BroadcastService

logger = get_logger(__name__)

router = Router(name="broadcast_history")


@router.callback_query(F.data == "broadcast_menu", IsSuperAdmin())
@router.callback_query(F.data == "superadmin:broadcast", IsSuperAdmin())
async def show_broadcast_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать главное меню рассылок.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()

    text = (
        "📢 <b>Система массовых рассылок</b>\n\n"
        "Создавайте и управляйте рассылками с сегментацией пользователей.\n\n"
        "Доступные действия:\n"
        "• Создать новую рассылку\n"
        "• Просмотреть историю\n"
        "• Посмотреть статистику"
    )

    keyboard = get_broadcast_main_menu()

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_history"), IsSuperAdmin())
async def show_broadcast_history(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать историю рассылок.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await state.clear()

    # Получаем offset из callback_data
    parts = callback.data.split(":")
    offset = int(parts[1]) if len(parts) > 1 else 0

    service = BroadcastService(session)
    broadcasts = await service.get_all_broadcasts(limit=11, offset=offset)

    if not broadcasts:
        text = (
            "📋 <b>История рассылок</b>\n\n"
            "Рассылки еще не создавались.\n\n"
            "Создайте первую рассылку через главное меню."
        )
        keyboard = get_broadcast_main_menu()
    else:
        text = (
            "📋 <b>История рассылок</b>\n\n"
            "Выберите рассылку для просмотра деталей:\n\n"
            "Легенда:\n"
            "⏳ - Ожидает отправки\n"
            "▶️ - Отправляется\n"
            "✅ - Завершена\n"
            "❌ - Ошибка\n"
            "🚫 - Отменена"
        )
        keyboard = get_broadcast_history_keyboard(broadcasts, offset)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_view:"), IsSuperAdmin())
async def view_broadcast_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Просмотр деталей рассылки.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    broadcast_id = int(callback.data.split(":")[1])

    service = BroadcastService(session)
    broadcast = await service.get_broadcast(broadcast_id)

    if not broadcast:
        await callback.answer("❌ Рассылка не найдена", show_alert=True)
        return

    # Форматируем детали
    status_names = {
        "pending": "⏳ Ожидает отправки",
        "in_progress": "▶️ Отправляется",
        "completed": "✅ Завершена",
        "failed": "❌ Ошибка",
        "cancelled": "🚫 Отменена",
    }

    status_text = status_names.get(broadcast.status, broadcast.status)

    text = (
        f"📋 <b>Рассылка #{broadcast.id}</b>\n\n"
        f"<b>Статус:</b> {status_text}\n"
        f"<b>Создана:</b> {broadcast.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    if broadcast.completed_at:
        text += f"<b>Завершена:</b> {broadcast.completed_at.strftime('%d.%m.%Y %H:%M')}\n"

    text += f"\n<b>Тип:</b> "
    if broadcast.has_media:
        text += f"Текст + {broadcast.media_type}\n"
    else:
        text += "Только текст\n"

    text += (
        f"\n<b>Статистика:</b>\n"
        f"• Получателей: {broadcast.total_target}\n"
        f"• Отправлено: {broadcast.sent_count}\n"
        f"• Успешно: {broadcast.success_count}\n"
        f"• Ошибки: {broadcast.failed_count}\n"
    )

    if broadcast.is_completed and broadcast.total_target > 0:
        success_rate = broadcast.success_rate
        text += f"• Процент успеха: {success_rate:.1f}%\n"

    # Фильтры
    if broadcast.filters:
        text += f"\n<b>Фильтры:</b>\n"
        filters = broadcast.filters
        if filters.get("all"):
            text += "• Все пользователи\n"
        if "active_days" in filters:
            text += f"• Активные (последние {filters['active_days']} дней)\n"
        if filters.get("has_orders"):
            text += "• Есть заказы\n"
        if filters.get("no_orders"):
            text += "• Нет заказов\n"
        if "min_orders" in filters:
            text += f"• Минимум {filters['min_orders']} заказов\n"

    # Текст рассылки (первые 200 символов)
    preview_text = broadcast.text[:200]
    if len(broadcast.text) > 200:
        preview_text += "..."

    text += f"\n<b>Текст:</b>\n{preview_text}\n"

    # Ошибки (если есть)
    if broadcast.error_log and broadcast.error_log.get("errors"):
        error_count = len(broadcast.error_log["errors"])
        text += f"\n<b>⚠️ Логов ошибок:</b> {error_count}\n"

    keyboard = get_broadcast_detail_keyboard(broadcast.id, broadcast.status)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_repeat:"), IsSuperAdmin())
async def repeat_broadcast(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Повторить рассылку.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    broadcast_id = int(callback.data.split(":")[1])

    service = BroadcastService(session)
    old_broadcast = await service.get_broadcast(broadcast_id)

    if not old_broadcast:
        await callback.answer("❌ Рассылка не найдена", show_alert=True)
        return

    # Копируем данные в FSM для создания новой рассылки
    await state.update_data(
        text=old_broadcast.text,
        media_type=old_broadcast.media_type,
        media_file_id=old_broadcast.media_file_id,
        filters=old_broadcast.filters or {},
    )

    # Импортируем функцию из create.py
    from src.bot.handlers.superadmin.broadcast.create import finish_broadcast_filters

    # Показываем предпросмотр
    await finish_broadcast_filters(callback, state, session)

    await callback.answer("🔄 Рассылка скопирована, проверьте предпросмотр")


@router.callback_query(F.data.startswith("broadcast_cancel_confirm:"), IsSuperAdmin())
async def cancel_broadcast_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Подтвердить отмену рассылки.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    broadcast_id = int(callback.data.split(":")[1])

    service = BroadcastService(session)
    broadcast = await service.cancel_broadcast(broadcast_id)

    if not broadcast:
        await callback.answer("❌ Рассылка не найдена", show_alert=True)
        return

    await session.commit()

    await callback.message.edit_text(
        text=f"🚫 Рассылка #{broadcast_id} отменена",
        parse_mode="HTML",
    )

    await callback.answer("✅ Рассылка отменена")

    logger.info(
        "Broadcast cancelled",
        broadcast_id=broadcast_id,
        admin_id=callback.from_user.id,
    )


@router.callback_query(F.data == "broadcast_stats", IsSuperAdmin())
async def show_broadcast_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать общую статистику по рассылкам.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    await state.clear()

    service = BroadcastService(session)
    stats = await service.get_broadcast_stats()

    text = (
        "📊 <b>Статистика рассылок</b>\n\n"
        f"<b>Всего рассылок:</b> {stats['total']}\n\n"
        f"<b>По статусам:</b>\n"
        f"⏳ Ожидают: {stats['pending']}\n"
        f"▶️ В процессе: {stats['in_progress']}\n"
        f"✅ Завершены: {stats['completed']}\n"
        f"❌ Ошибки: {stats['failed']}\n"
        f"🚫 Отменены: {stats['cancelled']}\n\n"
        f"<b>Общая статистика отправок:</b>\n"
        f"• Всего отправлено: {stats['total_sent']}\n"
        f"• Успешно доставлено: {stats['total_success']}\n"
        f"• Ошибки: {stats['total_failed']}\n"
    )

    if stats['total_sent'] > 0:
        success_rate = (stats['total_success'] / stats['total_sent']) * 100
        text += f"• Процент успеха: {success_rate:.1f}%\n"

    keyboard = get_broadcast_main_menu()

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()
