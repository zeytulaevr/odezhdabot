"""Тесты для модуля formatters."""

from decimal import Decimal

import pytest

from src.utils.formatters import (
    escape_html,
    format_items_count,
    format_phone,
    format_price,
    pluralize,
    truncate_text,
)


class TestFormatPrice:
    """Тесты для форматирования цены."""

    def test_format_decimal_price(self) -> None:
        """Тест форматирования Decimal цены."""
        price = Decimal("1234.56")
        result = format_price(price)
        assert result == "1 234.56 ₽"

    def test_format_float_price(self) -> None:
        """Тест форматирования float цены."""
        price = 1234.56
        result = format_price(price)
        assert result == "1 234.56 ₽"


class TestTruncateText:
    """Тесты для обрезки текста."""

    def test_short_text(self) -> None:
        """Тест с коротким текстом."""
        text = "Hello"
        result = truncate_text(text, max_length=100)
        assert result == "Hello"

    def test_long_text(self) -> None:
        """Тест с длинным текстом."""
        text = "A" * 150
        result = truncate_text(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")


class TestEscapeHtml:
    """Тесты для экранирования HTML."""

    def test_escape_html(self) -> None:
        """Тест экранирования HTML символов."""
        text = '<script>alert("XSS")</script>'
        result = escape_html(text)
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&quot;" in result


class TestFormatPhone:
    """Тесты для форматирования номера телефона."""

    def test_format_russian_phone_11_digits(self) -> None:
        """Тест форматирования российского номера (11 цифр)."""
        phone = "79991234567"
        result = format_phone(phone)
        assert result == "+7 (999) 123-45-67"

    def test_format_russian_phone_with_plus(self) -> None:
        """Тест форматирования номера с плюсом."""
        phone = "+79991234567"
        result = format_phone(phone)
        assert result == "+7 (999) 123-45-67"


class TestPluralize:
    """Тесты для выбора формы слова."""

    def test_one_item(self) -> None:
        """Тест с одним элементом."""
        forms = ("товар", "товара", "товаров")
        result = pluralize(1, forms)
        assert result == "товар"

    def test_two_items(self) -> None:
        """Тест с двумя элементами."""
        forms = ("товар", "товара", "товаров")
        result = pluralize(2, forms)
        assert result == "товара"

    def test_five_items(self) -> None:
        """Тест с пятью элементами."""
        forms = ("товар", "товара", "товаров")
        result = pluralize(5, forms)
        assert result == "товаров"


class TestFormatItemsCount:
    """Тесты для форматирования количества товаров."""

    def test_format_items_count(self) -> None:
        """Тест форматирования количества товаров."""
        assert format_items_count(1) == "1 товар"
        assert format_items_count(2) == "2 товара"
        assert format_items_count(5) == "5 товаров"
