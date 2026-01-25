"""Клавиатуры для работы с заказами."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from src.database.models.order import Order
from src.database.models.product import Product


def get_color_selection_keyboard(product_id: int, colors: list[str]) -> InlineKeyboardMarkup:
    """Клавиатура выбора цвета товара.

    Args:
        product_id: ID товара
        colors: Список доступных цветов

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Цвета по 2 в ряд
    for i in range(0, len(colors), 2):
        row_buttons = []
        for color in colors[i:i+2]:
            row_buttons.append(
                InlineKeyboardButton(
                    text=color,
                    callback_data=f"order_color:{product_id}:{color}",
                )
            )
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    return builder.as_markup()


def get_size_selection_keyboard(product_id: int, sizes: list[str], fit: str | None = None, color: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора размера товара.

    Args:
        product_id: ID товара
        sizes: Список доступных размеров
        fit: Тип кроя (опционально)
        color: Выбранный цвет (опционально, для callback data)

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Размеры по 3 в ряд
    for i in range(0, len(sizes), 3):
        row_buttons = []
        for size in sizes[i:i+3]:
            # Добавляем цвет в callback data если он был выбран
            callback_data = f"order_size:{product_id}:{size}"
            if color:
                callback_data += f":{color}"

            row_buttons.append(
                InlineKeyboardButton(
                    text=size.upper(),
                    callback_data=callback_data,
                )
            )
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    return builder.as_markup()


def get_quantity_selection_keyboard(product_id: int, size: str, color: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора количества товара.

    Args:
        product_id: ID товара
        size: Выбранный размер
        color: Выбранный цвет (опционально)

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Кнопки с количеством (1-3)
    row = []
    for i in range(1, 4):
        # Формируем callback_data с учетом цвета
        callback_data = f"order_quantity:{product_id}:{size}:{i}"
        if color:
            callback_data += f":{color}"

        row.append(
            InlineKeyboardButton(
                text=f"{i} шт.",
                callback_data=callback_data,
            )
        )

    builder.row(*row)

    # Кнопка ручного ввода количества
    manual_callback_data = f"order_quantity_manual:{product_id}:{size}"
    if color:
        manual_callback_data += f":{color}"

    builder.row(
        InlineKeyboardButton(
            text="✏️ Ввести количество вручную",
            callback_data=manual_callback_data,
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    return builder.as_markup()


def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура запроса контакта.

    Returns:
        Reply клавиатура
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📞 Поделиться номером", request_contact=True)
    )
    builder.row(
        KeyboardButton(text="✏️ Ввести вручную")
    )
    builder.row(
        KeyboardButton(text="❌ Отменить")
    )

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_order_confirmation_keyboard(product_id: int, size: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заказа.

    Args:
        product_id: ID товара
        size: Выбранный размер

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить заказ",
            callback_data=f"order_confirm:{product_id}:{size}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="order_cancel",
        )
    )

    return builder.as_markup()


def get_order_completed_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после успешного оформления заказа.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🛒 Заказать еще",
            callback_data="catalog",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Мои заказы",
            callback_data="my_orders",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="back_to_menu",
        )
    )

    return builder.as_markup()


def get_my_orders_keyboard(has_orders: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра своих заказов.

    Args:
        has_orders: Есть ли заказы

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    if has_orders:
        # Кнопка обновить список
        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="my_orders_refresh",
            )
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu")
    )

    return builder.as_markup()


def get_order_detail_keyboard(order: Order) -> InlineKeyboardMarkup:
    """Клавиатура детального просмотра заказа.

    Args:
        order: Заказ

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Если заказ можно отменить
    if order.can_be_cancelled:
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить заказ",
                callback_data=f"order_user_cancel:{order.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к списку",
            callback_data="my_orders",
        )
    )

    return builder.as_markup()


# ========================================
# АДМИНСКИЕ КЛАВИАТУРЫ
# ========================================


def get_admin_orders_filters_keyboard(current_filter: str = "all") -> InlineKeyboardMarkup:
    """Клавиатура фильтров заказов для админа.

    Args:
        current_filter: Текущий активный фильтр

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    filters = [
        ("📋 Все", "all"),
        ("🆕 Новые", "new"),
        ("✔️ Подтверждённые", "confirmed"),
        ("💰 Оплачены", "paid"),
        ("📦 Отправлены", "shipped"),
        ("🚚 Доставлены", "delivered"),
        ("✅ Завершённые", "completed"),
        ("❌ Отменённые", "cancelled"),
    ]

    # Два фильтра в ряд
    for i in range(0, len(filters), 2):
        row_buttons = []
        for text, status in filters[i:i+2]:
            # Добавляем галочку к активному фильтру
            display_text = f"✓ {text}" if status == current_filter else text
            row_buttons.append(
                InlineKeyboardButton(
                    text=display_text,
                    callback_data=f"admin_orders_filter:{status}",
                )
            )
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_order_actions_keyboard(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    """Клавиатура действий с заказом для админа.

    Args:
        order_id: ID заказа
        current_status: Текущий статус заказа

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Возможные переходы статусов
    status_transitions = {
        "new": [("✔️ Подтвердить", "confirmed"), ("❌ Отменить", "cancelled")],
        "confirmed": [("💰 Оплачен", "paid"), ("❌ Отменить", "cancelled")],
        "paid": [("📦 Отправлен", "shipped")],
        "shipped": [("🚚 Доставлен", "delivered")],
        "delivered": [("✅ Завершён", "completed")],
    }

    # Кнопки смены статуса
    if current_status in status_transitions:
        for text, new_status in status_transitions[current_status]:
            builder.row(
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"admin_order_status:{order_id}:{new_status}",
                )
            )

    # Кнопки для редактирования и общения (если заказ не завершён и не отменён)
    if current_status not in ["completed", "cancelled"]:
        # Кнопка редактирования заказа (только для new и confirmed)
        if current_status in ["new", "confirmed"]:
            builder.row(
                InlineKeyboardButton(
                    text="✏️ Редактировать заказ",
                    callback_data=f"admin_order_edit:{order_id}",
                )
            )

        # Кнопка отправки реквизитов (только для confirmed)
        if current_status == "confirmed":
            builder.row(
                InlineKeyboardButton(
                    text="💳 Отправить реквизиты",
                    callback_data=f"admin_order_send_payment:{order_id}",
                )
            )

        # Кнопка чата с клиентом
        builder.row(
            InlineKeyboardButton(
                text="💬 Написать клиенту",
                callback_data=f"admin_order_chat:{order_id}",
            )
        )

    # Дополнительные действия
    builder.row(
        InlineKeyboardButton(
            text="📝 Добавить заметку",
            callback_data=f"admin_order_note:{order_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ К списку заказов",
            callback_data="admin_orders_filter:all",
        )
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin:menu")
    )

    return builder.as_markup()


def get_status_change_confirmation_keyboard(
    order_id: int,
    new_status: str,
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения смены статуса.

    Args:
        order_id: ID заказа
        new_status: Новый статус

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"admin_order_confirm_status:{order_id}:{new_status}",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin_order_view:{order_id}",
        ),
    )

    return builder.as_markup()
