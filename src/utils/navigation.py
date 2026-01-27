"""Утилиты для навигации и истории экранов."""

from dataclasses import dataclass, field
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


@dataclass
class NavigationItem:
    """Элемент истории навигации."""

    text: str  # Текст сообщения
    markup: InlineKeyboardMarkup | None = None  # Клавиатура
    parse_mode: str = "HTML"  # Режим парсинга
    photo_file_id: str | None = None  # ID фото (если сообщение с фото)
    callback_data: str | None = None  # callback_data, который привел к этому экрану
    message_data: dict[str, Any] = field(default_factory=dict)  # Дополнительные данные


class NavigationStack:
    """Управление стеком навигации в FSM state."""

    NAVIGATION_KEY = "navigation_history"
    MAX_STACK_SIZE = 20  # Максимальный размер стека

    @classmethod
    async def push(
        cls,
        state: FSMContext,
        text: str,
        markup: InlineKeyboardMarkup | None = None,
        parse_mode: str = "HTML",
        photo_file_id: str | None = None,
        callback_data: str | None = None,
        **extra_data: Any,
    ) -> None:
        """Добавить экран в историю навигации.

        Args:
            state: FSM контекст
            text: Текст сообщения
            markup: Inline клавиатура
            parse_mode: Режим парсинга (HTML/Markdown)
            photo_file_id: ID фото (если есть)
            callback_data: callback_data текущего экрана
            **extra_data: Дополнительные данные для восстановления
        """
        data = await state.get_data()
        history = data.get(cls.NAVIGATION_KEY, [])

        # Создаем элемент истории
        item = {
            "text": text,
            "markup": cls._serialize_markup(markup),
            "parse_mode": parse_mode,
            "photo_file_id": photo_file_id,
            "callback_data": callback_data,
            "message_data": extra_data,
        }

        # Добавляем в стек
        history.append(item)

        # Ограничиваем размер стека
        if len(history) > cls.MAX_STACK_SIZE:
            history = history[-cls.MAX_STACK_SIZE :]

        await state.update_data({cls.NAVIGATION_KEY: history})

    @classmethod
    async def pop(cls, state: FSMContext) -> NavigationItem | None:
        """Извлечь предыдущий экран из истории.

        Args:
            state: FSM контекст

        Returns:
            NavigationItem или None, если история пуста
        """
        data = await state.get_data()
        history = data.get(cls.NAVIGATION_KEY, [])

        if not history:
            return None

        # Извлекаем последний элемент из истории
        prev_item_data = history.pop()

        # Обновляем историю в state
        await state.update_data({cls.NAVIGATION_KEY: history})

        # Десериализуем и возвращаем
        return NavigationItem(
            text=prev_item_data["text"],
            markup=cls._deserialize_markup(prev_item_data.get("markup")),
            parse_mode=prev_item_data.get("parse_mode", "HTML"),
            photo_file_id=prev_item_data.get("photo_file_id"),
            callback_data=prev_item_data.get("callback_data"),
            message_data=prev_item_data.get("message_data", {}),
        )

    @classmethod
    async def clear(cls, state: FSMContext) -> None:
        """Очистить историю навигации.

        Args:
            state: FSM контекст
        """
        await state.update_data({cls.NAVIGATION_KEY: []})

    @classmethod
    async def get_history_size(cls, state: FSMContext) -> int:
        """Получить размер истории навигации.

        Args:
            state: FSM контекст

        Returns:
            Количество элементов в истории
        """
        data = await state.get_data()
        history = data.get(cls.NAVIGATION_KEY, [])
        return len(history)

    @classmethod
    def _serialize_markup(
        cls, markup: InlineKeyboardMarkup | None
    ) -> dict[str, Any] | None:
        """Сериализовать клавиатуру для хранения в state.

        Args:
            markup: Inline клавиатура

        Returns:
            Словарь с данными клавиатуры или None
        """
        if not markup:
            return None

        # Сериализуем клавиатуру в словарь
        return {
            "inline_keyboard": [
                [
                    {
                        "text": btn.text,
                        "callback_data": btn.callback_data,
                        "url": btn.url,
                    }
                    for btn in row
                ]
                for row in markup.inline_keyboard
            ]
        }

    @classmethod
    def _deserialize_markup(
        cls, data: dict[str, Any] | None
    ) -> InlineKeyboardMarkup | None:
        """Десериализовать клавиатуру из state.

        Args:
            data: Данные клавиатуры

        Returns:
            InlineKeyboardMarkup или None
        """
        if not data:
            return None

        from aiogram.types import InlineKeyboardButton

        try:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=btn["text"],
                            callback_data=btn.get("callback_data"),
                            url=btn.get("url"),
                        )
                        for btn in row
                    ]
                    for row in data["inline_keyboard"]
                ]
            )
            return keyboard
        except (KeyError, TypeError):
            return None


async def save_current_screen(
    message: Message | CallbackQuery,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    photo_file_id: str | None = None,
    **extra_data: Any,
) -> None:
    """Сохранить текущий экран в истории навигации.

    Удобная функция-хелпер для сохранения экрана.

    Args:
        message: Message или CallbackQuery
        state: FSM контекст
        text: Текст сообщения
        markup: Inline клавиатура
        parse_mode: Режим парсинга
        photo_file_id: ID фото
        **extra_data: Дополнительные данные
    """
    callback_data = None
    if isinstance(message, CallbackQuery):
        callback_data = message.data

    await NavigationStack.push(
        state=state,
        text=text,
        markup=markup,
        parse_mode=parse_mode,
        photo_file_id=photo_file_id,
        callback_data=callback_data,
        **extra_data,
    )


async def go_back(
    callback: CallbackQuery, state: FSMContext, default_text: str = "🏠 Главное меню"
) -> bool:
    """Вернуться на предыдущий экран.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        default_text: Текст по умолчанию, если история пуста

    Returns:
        True если удалось вернуться, False если история пуста
    """
    from aiogram.exceptions import TelegramBadRequest

    prev_screen = await NavigationStack.pop(state)

    if not prev_screen:
        # История пуста, возвращаем на главное меню
        await callback.answer("История пуста")
        try:
            await callback.message.edit_text(
                text=default_text,
                parse_mode="HTML",
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        return False

    # Восстанавливаем предыдущий экран
    try:
        if prev_screen.photo_file_id:
            # Сообщение с фото - удаляем текущее и отправляем новое
            await callback.message.delete()
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=prev_screen.photo_file_id,
                caption=prev_screen.text,
                reply_markup=prev_screen.markup,
                parse_mode=prev_screen.parse_mode,
            )
        else:
            # Обычное текстовое сообщение
            await callback.message.edit_text(
                text=prev_screen.text,
                reply_markup=prev_screen.markup,
                parse_mode=prev_screen.parse_mode,
            )
        await callback.answer()
        return True
    except TelegramBadRequest as e:
        # Если сообщение не изменилось, просто игнорируем ошибку
        if "message is not modified" not in str(e).lower():
            await callback.answer(f"Ошибка навигации: {e}", show_alert=True)
            return False
        await callback.answer()
        return True
    except Exception as e:
        # Если не удалось восстановить экран, показываем текущий
        await callback.answer(f"Ошибка навигации: {e}", show_alert=True)
        return False


async def edit_message_with_navigation(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    save_to_history: bool = True,
    **extra_data: Any,
) -> None:
    """Редактировать сообщение и сохранить в истории навигации.

    Удобная функция для обновления сообщения при callback'ах
    с автоматическим сохранением в истории навигации.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        text: Текст сообщения
        markup: Inline клавиатура
        parse_mode: Режим парсинга
        save_to_history: Сохранять ли в истории (по умолчанию True)
        **extra_data: Дополнительные данные
    """
    from aiogram.exceptions import TelegramBadRequest

    # Получаем текущий экран ДО изменения
    current_text = callback.message.text or callback.message.caption or ""
    current_markup = callback.message.reply_markup

    # Проверяем, отличается ли новый контент от текущего
    if current_text == text and current_markup == markup:
        await callback.answer()
        return

    # Сохраняем ТЕКУЩИЙ экран в историю (с которого уходим)
    if save_to_history and current_text:
        await NavigationStack.push(
            state=state,
            text=current_text,
            markup=current_markup,
            parse_mode=parse_mode,
            callback_data=callback.data,
            **extra_data,
        )

    # Затем редактируем сообщение на НОВЫЙ экран
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        # Если сообщение не изменилось, просто игнорируем ошибку
        if "message is not modified" not in str(e).lower():
            raise

    await callback.answer()


async def send_message_with_navigation(
    message: Message,
    state: FSMContext,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    save_to_history: bool = True,
    **extra_data: Any,
) -> Message:
    """Отправить сообщение и сохранить в истории навигации.

    Args:
        message: Message
        state: FSM контекст
        text: Текст сообщения
        markup: Inline клавиатура
        parse_mode: Режим парсинга
        save_to_history: Сохранять ли в истории
        **extra_data: Дополнительные данные

    Returns:
        Отправленное сообщение
    """
    # Сначала сохраняем в историю
    if save_to_history:
        await NavigationStack.push(
            state=state,
            text=text,
            markup=markup,
            parse_mode=parse_mode,
            **extra_data,
        )

    # Отправляем сообщение
    return await message.answer(
        text=text,
        reply_markup=markup,
        parse_mode=parse_mode,
    )


async def send_photo_with_navigation(
    message: Message,
    state: FSMContext,
    photo: str,
    caption: str,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
    save_to_history: bool = True,
    **extra_data: Any,
) -> Message:
    """Отправить фото с текстом и сохранить в истории навигации.

    Args:
        message: Message
        state: FSM контекст
        photo: file_id фото
        caption: Текст под фото
        markup: Inline клавиатура
        parse_mode: Режим парсинга
        save_to_history: Сохранять ли в истории
        **extra_data: Дополнительные данные

    Returns:
        Отправленное сообщение
    """
    # Сначала сохраняем в историю
    if save_to_history:
        await NavigationStack.push(
            state=state,
            text=caption,
            markup=markup,
            parse_mode=parse_mode,
            photo_file_id=photo,
            **extra_data,
        )

    # Отправляем фото
    return await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=markup,
        parse_mode=parse_mode,
    )
