"""Клавиатуры для системы рассылок."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_broadcast_main_menu() -> InlineKeyboardMarkup:
    """Главное меню рассылок.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✉️ Создать рассылку",
            callback_data="broadcast_create",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 История рассылок",
            callback_data="broadcast_history",
        ),
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="broadcast_stats",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back",
        )
    )

    return builder.as_markup()


def get_broadcast_filters_keyboard(
    selected_filters: dict[str, bool | int | str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура выбора фильтров сегментации.

    Args:
        selected_filters: Уже выбранные фильтры

    Returns:
        Inline клавиатура
    """
    selected_filters = selected_filters or {}
    builder = InlineKeyboardBuilder()

    # Все пользователи
    all_selected = selected_filters.get("all", False)
    builder.row(
        InlineKeyboardButton(
            text=f"{'✅' if all_selected else '⬜'} Все пользователи",
            callback_data="broadcast_filter_toggle:all",
        )
    )

    # Только если не выбрано "все"
    if not all_selected:
        # Активные пользователи
        active_selected = "active_days" in selected_filters
        builder.row(
            InlineKeyboardButton(
                text=f"{'✅' if active_selected else '⬜'} Активные (30 дней)",
                callback_data="broadcast_filter_toggle:active_30",
            )
        )

        # Есть заказы
        has_orders = selected_filters.get("has_orders", False)
        builder.row(
            InlineKeyboardButton(
                text=f"{'✅' if has_orders else '⬜'} Есть заказы",
                callback_data="broadcast_filter_toggle:has_orders",
            )
        )

        # Нет заказов
        no_orders = selected_filters.get("no_orders", False)
        builder.row(
            InlineKeyboardButton(
                text=f"{'✅' if no_orders else '⬜'} Нет заказов",
                callback_data="broadcast_filter_toggle:no_orders",
            )
        )

        # Минимум заказов
        min_orders = "min_orders" in selected_filters
        builder.row(
            InlineKeyboardButton(
                text=f"{'✅' if min_orders else '⬜'} Минимум 3 заказа",
                callback_data="broadcast_filter_toggle:min_orders_3",
            )
        )

    # Кнопки управления
    builder.row(
        InlineKeyboardButton(
            text="🔄 Сбросить",
            callback_data="broadcast_filter_reset",
        ),
        InlineKeyboardButton(
            text="➡️ Продолжить",
            callback_data="broadcast_filter_done",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="broadcast_cancel",
        )
    )

    return builder.as_markup()


def get_broadcast_preview_keyboard(broadcast_id: int | None = None) -> InlineKeyboardMarkup:
    """Клавиатура предпросмотра рассылки.

    Args:
        broadcast_id: ID черновика рассылки (если есть)

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Отправить",
            callback_data=f"broadcast_confirm_send:{broadcast_id}" if broadcast_id else "broadcast_confirm_send",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить текст",
            callback_data="broadcast_edit_text",
        ),
        InlineKeyboardButton(
            text="🎯 Изменить фильтры",
            callback_data="broadcast_edit_filters",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="broadcast_cancel",
        )
    )

    return builder.as_markup()


def get_broadcast_confirmation_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    """Клавиатура финального подтверждения отправки.

    Args:
        broadcast_id: ID рассылки

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, отправить",
            callback_data=f"broadcast_send:{broadcast_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="❌ Нет, отменить",
            callback_data="broadcast_cancel",
        )
    )

    return builder.as_markup()


def get_broadcast_history_keyboard(
    broadcasts: list,
    offset: int = 0,
) -> InlineKeyboardMarkup:
    """Клавиатура истории рассылок.

    Args:
        broadcasts: Список рассылок
        offset: Смещение для пагинации

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Кнопки рассылок
    for broadcast in broadcasts[:10]:
        status_emoji = {
            "pending": "⏳",
            "in_progress": "▶️",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫",
        }.get(broadcast.status, "❓")

        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} #{broadcast.id} - {broadcast.created_at.strftime('%d.%m %H:%M')}",
                callback_data=f"broadcast_view:{broadcast.id}",
            )
        )

    # Пагинация
    pagination_buttons = []
    if offset > 0:
        pagination_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"broadcast_history:{offset - 10}",
            )
        )
    if len(broadcasts) > 10:
        pagination_buttons.append(
            InlineKeyboardButton(
                text="➡️ Вперед",
                callback_data=f"broadcast_history:{offset + 10}",
            )
        )

    if pagination_buttons:
        builder.row(*pagination_buttons)

    # Возврат
    builder.row(
        InlineKeyboardButton(
            text="◀️ К меню рассылок",
            callback_data="broadcast_menu",
        )
    )

    return builder.as_markup()


def get_broadcast_detail_keyboard(
    broadcast_id: int,
    status: str,
) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра рассылки.

    Args:
        broadcast_id: ID рассылки
        status: Статус рассылки

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Повторить рассылку (если завершена)
    if status in ["completed", "failed", "cancelled"]:
        builder.row(
            InlineKeyboardButton(
                text="🔄 Повторить рассылку",
                callback_data=f"broadcast_repeat:{broadcast_id}",
            )
        )

    # Отменить (если в процессе или ожидает)
    if status in ["pending", "in_progress"]:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Отменить рассылку",
                callback_data=f"broadcast_cancel_confirm:{broadcast_id}",
            )
        )

    # Назад к истории
    builder.row(
        InlineKeyboardButton(
            text="◀️ К истории",
            callback_data="broadcast_history",
        )
    )

    return builder.as_markup()


def get_broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены создания рассылки.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, отменить",
            callback_data="broadcast_cancel_confirm",
        ),
        InlineKeyboardButton(
            text="❌ Нет, продолжить",
            callback_data="broadcast_cancel_no",
        ),
    )

    return builder.as_markup()


def get_broadcast_media_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура пропуска добавления медиа.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⏭ Пропустить",
            callback_data="broadcast_media_skip",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="broadcast_cancel",
        )
    )

    return builder.as_markup()
