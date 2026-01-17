"""Утилиты для форматирования текста и данных."""

from datetime import datetime
from decimal import Decimal

from src.core.constants import DATETIME_FORMAT, DATE_FORMAT, TIME_FORMAT


def format_price(price: Decimal | float) -> str:
    """Форматирование цены с валютой.

    Args:
        price: Цена для форматирования

    Returns:
        Отформатированная строка с ценой
    """
    if isinstance(price, float):
        price = Decimal(str(price))

    return f"{price:,.2f} ₽".replace(",", " ")


def format_datetime(dt: datetime, format_str: str = DATETIME_FORMAT) -> str:
    """Форматирование даты и времени.

    Args:
        dt: Дата и время
        format_str: Формат строки

    Returns:
        Отформатированная строка
    """
    return dt.strftime(format_str)


def format_date(dt: datetime) -> str:
    """Форматирование даты.

    Args:
        dt: Дата

    Returns:
        Отформатированная дата
    """
    return format_datetime(dt, DATE_FORMAT)


def format_time(dt: datetime) -> str:
    """Форматирование времени.

    Args:
        dt: Время

    Returns:
        Отформатированное время
    """
    return format_datetime(dt, TIME_FORMAT)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезка текста до максимальной длины.

    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста

    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)].rstrip() + suffix


def escape_html(text: str) -> str:
    """Экранирование HTML символов.

    Args:
        text: Исходный текст

    Returns:
        Текст с экранированными HTML символами
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def format_phone(phone: str) -> str:
    """Форматирование номера телефона.

    Args:
        phone: Номер телефона

    Returns:
        Отформатированный номер
    """
    # Убираем все нецифровые символы
    digits = "".join(filter(str.isdigit, phone))

    # Форматирование для российского номера
    if len(digits) == 11 and digits.startswith("7"):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}"

    # Возврат как есть, если не подходит
    return phone


def pluralize(count: int, forms: tuple[str, str, str]) -> str:
    """Выбор правильной формы слова в зависимости от числа.

    Args:
        count: Количество
        forms: Кортеж из трёх форм (1, 2, 5)
            Например: ("товар", "товара", "товаров")

    Returns:
        Правильная форма слова
    """
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return forms[1]
    else:
        return forms[2]


def format_items_count(count: int) -> str:
    """Форматирование количества товаров.

    Args:
        count: Количество товаров

    Returns:
        Строка с количеством и правильной формой слова
    """
    form = pluralize(count, ("товар", "товара", "товаров"))
    return f"{count} {form}"


def format_order_number(order_id: int) -> str:
    """Форматирование номера заказа.

    Args:
        order_id: ID заказа

    Returns:
        Отформатированный номер заказа
    """
    return f"#{order_id:06d}"
