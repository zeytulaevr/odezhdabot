"""Клавиатуры для модерации."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_moderation_keyboard(moderated_message_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для модерации сообщения.

    Args:
        moderated_message_id: ID записи модерации в БД

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"mod_approve:{moderated_message_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"mod_reject:{moderated_message_id}",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить + Бан 1д",
            callback_data=f"mod_ban_1d:{moderated_message_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🚫 Удалить + Бан навсегда",
            callback_data=f"mod_ban_perm:{moderated_message_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Подробнее",
            callback_data=f"mod_details:{moderated_message_id}",
        )
    )

    return builder.as_markup()


def get_spam_pattern_keyboard(pattern_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура для управления спам-паттерном.

    Args:
        pattern_id: ID паттерна
        is_active: Активен ли паттерн

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Кнопка вкл/выкл
    toggle_text = "🔴 Отключить" if is_active else "🟢 Включить"
    builder.row(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=f"spam_toggle:{pattern_id}",
        )
    )

    # Кнопка удаления
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить паттерн",
            callback_data=f"spam_delete:{pattern_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="spam_list")
    )

    return builder.as_markup()


def get_spam_patterns_list_keyboard(
    patterns: list[tuple[int, str, str, bool]], page: int = 0
) -> InlineKeyboardMarkup:
    """Клавиатура со списком спам-паттернов.

    Args:
        patterns: Список кортежей (id, pattern, type, is_active)
        page: Номер страницы

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    for pattern_id, pattern_text, pattern_type, is_active in patterns:
        status = "🟢" if is_active else "🔴"
        type_emoji = {"keyword": "🔤", "regex": "🔧", "url": "🔗"}.get(
            pattern_type, "❓"
        )

        # Обрезаем длинный текст паттерна
        display_text = (
            pattern_text[:30] + "..." if len(pattern_text) > 30 else pattern_text
        )

        builder.row(
            InlineKeyboardButton(
                text=f"{status} {type_emoji} {display_text}",
                callback_data=f"spam_view:{pattern_id}",
            )
        )

    # Кнопка добавления нового паттерна
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить паттерн",
            callback_data="spam_add",
        )
    )

    # Навигация (если нужна пагинация)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"spam_page:{page-1}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"spam_page:{page}")
    )
    if len(patterns) >= 10:  # Если показаны все 10, может быть ещё страница
        nav_buttons.append(
            InlineKeyboardButton(text="▶️ Вперед", callback_data=f"spam_page:{page+1}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()


def get_moderation_queue_keyboard(has_more: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для очереди модерации.

    Args:
        has_more: Есть ли ещё сообщения

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить очередь",
            callback_data="modqueue_refresh",
        )
    )

    if has_more:
        builder.row(
            InlineKeyboardButton(
                text="▶️ Следующие 10",
                callback_data="modqueue_next",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="modqueue_stats",
        )
    )

    return builder.as_markup()


def get_spam_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа спам-паттерна.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔤 Ключевое слово",
            callback_data="spam_type:keyword",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔧 Регулярное выражение",
            callback_data="spam_type:regex",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔗 URL паттерн",
            callback_data="spam_type:url",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Отмена", callback_data="spam_list")
    )

    return builder.as_markup()


def get_confirm_delete_keyboard(pattern_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления паттерна.

    Args:
        pattern_id: ID паттерна

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"spam_delete_confirm:{pattern_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"spam_view:{pattern_id}",
        ),
    )

    return builder.as_markup()
