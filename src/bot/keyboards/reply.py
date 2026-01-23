"""Reply клавиатуры бота."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from src.core.constants import Buttons


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Получить клавиатуру для администратора.

    Returns:
        Клавиатура с кнопкой для открытия админ-панели
    """
    builder = ReplyKeyboardBuilder()

    # Кнопка для открытия админ-панели (замена /admin)
    builder.row(
        KeyboardButton(text="📋 Админ-панель"),
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Нажмите кнопку для открытия панели",
    )


def get_superadmin_keyboard() -> ReplyKeyboardMarkup:
    """Получить клавиатуру для супер-администратора.

    Returns:
        Клавиатура с кнопкой для открытия супер-админ панели
    """
    builder = ReplyKeyboardBuilder()

    # Кнопка для открытия супер-админ панели (замена /superadmin)
    builder.row(
        KeyboardButton(text="👑 Супер-админ панель"),
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Нажмите кнопку для открытия панели",
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удалить reply клавиатуру.

    Returns:
        Объект для удаления клавиатуры
    """
    return ReplyKeyboardRemove()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Получить главную клавиатуру (устаревшая функция).

    Returns:
        Клавиатура с основными разделами
    """
    builder = ReplyKeyboardBuilder()

    # Первый ряд
    builder.row(
        KeyboardButton(text=Buttons.CATALOG),
        KeyboardButton(text=Buttons.CART),
    )

    # Второй ряд
    builder.row(
        KeyboardButton(text=Buttons.ORDERS),
        KeyboardButton(text=Buttons.PROFILE),
    )

    # Третий ряд
    builder.row(
        KeyboardButton(text=Buttons.SUPPORT),
        KeyboardButton(text=Buttons.HELP),
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел...",
    )


def get_contact_keyboard() -> ReplyKeyboardMarkup:
    """Получить клавиатуру для запроса контакта.

    Returns:
        Клавиатура с кнопкой отправки контакта
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📱 Отправить номер телефона", request_contact=True),
    )
    builder.row(
        KeyboardButton(text=Buttons.CANCEL),
    )

    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Получить клавиатуру для запроса местоположения.

    Returns:
        Клавиатура с кнопкой отправки местоположения
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📍 Отправить местоположение", request_location=True),
    )
    builder.row(
        KeyboardButton(text=Buttons.CANCEL),
    )

    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """Получить клавиатуру подтверждения.

    Returns:
        Клавиатура с кнопками подтверждения и отмены
    """
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text=Buttons.CONFIRM),
        KeyboardButton(text=Buttons.CANCEL),
    )

    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True,
    )
