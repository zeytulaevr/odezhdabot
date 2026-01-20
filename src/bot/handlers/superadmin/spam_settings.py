"""Управление спам-паттернами (только для супер-админов)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.moderation import (
    get_confirm_delete_keyboard,
    get_spam_pattern_keyboard,
    get_spam_patterns_list_keyboard,
    get_spam_type_keyboard,
)
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.spam_pattern import SpamPatternRepository
from src.services.moderation_service import ModerationService

logger = get_logger(__name__)

router = Router(name="spam_settings")


class SpamPatternStates(StatesGroup):
    """Состояния для добавления спам-паттерна."""

    waiting_for_type = State()
    waiting_for_pattern = State()


@router.message(Command("spam"), IsSuperAdmin())
async def cmd_spam_patterns(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Показать список спам-паттернов.

    Args:
        message: Входящее сообщение
        user: Супер-админ
        session: Сессия БД
    """
    logger.info("Spam patterns list requested", admin_id=user.id)

    spam_repo = SpamPatternRepository(session)
    patterns = await spam_repo.get_active_patterns()

    if not patterns:
        text = (
            "📋 <b>Спам-паттерны</b>\n\n"
            "Список паттернов пуст.\n"
            "Используйте кнопку ниже для добавления."
        )
        # Пустая клавиатура с кнопкой добавления
        keyboard = get_spam_patterns_list_keyboard([])
    else:
        text = (
            f"📋 <b>Спам-паттерны</b>\n\n"
            f"Активных паттернов: <b>{len(patterns)}</b>\n\n"
            f"Нажмите на паттерн для просмотра и редактирования."
        )

        # Формируем список для клавиатуры
        pattern_list = [
            (p.id, p.pattern, p.pattern_type, p.is_active) for p in patterns
        ]
        keyboard = get_spam_patterns_list_keyboard(pattern_list)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("spam_view:"), IsSuperAdmin())
async def callback_view_pattern(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Просмотр конкретного паттерна.

    Args:
        callback: Callback query
        user: Супер-админ
        session: Сессия БД
    """
    pattern_id = int(callback.data.split(":")[1])

    spam_repo = SpamPatternRepository(session)
    pattern = await spam_repo.get(pattern_id)

    if not pattern:
        await callback.answer("❌ Паттерн не найден", show_alert=True)
        return

    status = "🟢 Активен" if pattern.is_active else "🔴 Отключен"
    type_name = {
        "keyword": "🔤 Ключевое слово",
        "regex": "🔧 Регулярное выражение",
        "url": "🔗 URL паттерн",
    }.get(pattern.pattern_type, "❓ Неизвестный тип")

    text = (
        f"📋 <b>Спам-паттерн #{pattern.id}</b>\n\n"
        f"Тип: {type_name}\n"
        f"Статус: {status}\n"
        f"Создан: {pattern.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Паттерн:</b>\n"
        f"<code>{pattern.pattern}</code>"
    )

    keyboard = get_spam_pattern_keyboard(pattern.id, pattern.is_active)

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("spam_toggle:"), IsSuperAdmin())
async def callback_toggle_pattern(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Включить/выключить паттерн.

    Args:
        callback: Callback query
        user: Супер-админ
        session: Сессия БД
    """
    pattern_id = int(callback.data.split(":")[1])

    spam_repo = SpamPatternRepository(session)
    pattern = await spam_repo.toggle_active(pattern_id)

    if not pattern:
        await callback.answer("❌ Паттерн не найден", show_alert=True)
        return

    # Сбрасываем кеш паттернов в сервисе модерации
    moderation_service = ModerationService(session)
    moderation_service.invalidate_patterns_cache()

    status_text = "включен" if pattern.is_active else "отключен"
    await callback.answer(f"✅ Паттерн {status_text}", show_alert=True)

    # Обновляем сообщение
    await callback_view_pattern(callback, user, session)


@router.callback_query(F.data.startswith("spam_delete:"), IsSuperAdmin())
async def callback_delete_pattern(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Подтверждение удаления паттерна.

    Args:
        callback: Callback query
        user: Супер-админ
        session: Сессия БД
    """
    pattern_id = int(callback.data.split(":")[1])

    text = "⚠️ <b>Подтверждение удаления</b>\n\nВы уверены, что хотите удалить этот паттерн?"

    keyboard = get_confirm_delete_keyboard(pattern_id)

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("spam_delete_confirm:"), IsSuperAdmin())
async def callback_delete_pattern_confirm(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Удалить паттерн (подтверждено).

    Args:
        callback: Callback query
        user: Супер-админ
        session: Сессия БД
    """
    pattern_id = int(callback.data.split(":")[1])

    spam_repo = SpamPatternRepository(session)
    success = await spam_repo.delete(pattern_id)

    if success:
        # Сбрасываем кеш
        moderation_service = ModerationService(session)
        moderation_service.invalidate_patterns_cache()

        await callback.answer("✅ Паттерн удалён", show_alert=True)

        # Возвращаемся к списку
        if callback.message:
            await callback.message.delete()
            # Показываем обновлённый список
            await cmd_spam_patterns(callback.message, user, session)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(F.data == "spam_add", IsSuperAdmin())
async def callback_add_pattern(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать добавление нового паттерна.

    Args:
        callback: Callback query
        state: FSM состояние
    """
    text = (
        "➕ <b>Добавление спам-паттерна</b>\n\n" "Выберите тип паттерна:"
    )

    keyboard = get_spam_type_keyboard()

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(SpamPatternStates.waiting_for_type)


@router.callback_query(
    F.data.startswith("spam_type:"),
    IsSuperAdmin(),
    SpamPatternStates.waiting_for_type,
)
async def callback_pattern_type_selected(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Тип паттерна выбран.

    Args:
        callback: Callback query
        state: FSM состояние
    """
    pattern_type = callback.data.split(":")[1]

    await state.update_data(pattern_type=pattern_type)

    type_name = {
        "keyword": "ключевое слово",
        "regex": "регулярное выражение",
        "url": "URL паттерн",
    }.get(pattern_type, "паттерн")

    text = (
        f"📝 <b>Введите {type_name}</b>\n\n"
        f"Отправьте сообщение с паттерном, который нужно добавить.\n\n"
        f"Для отмены отправьте /cancel"
    )

    await callback.answer()
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(SpamPatternStates.waiting_for_pattern)


@router.message(IsSuperAdmin(), SpamPatternStates.waiting_for_pattern)
async def process_pattern_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка введённого паттерна.

    Args:
        message: Сообщение с паттерном
        state: FSM состояние
        session: Сессия БД
    """
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление паттерна отменено.")
        return

    data = await state.get_data()
    pattern_type = data.get("pattern_type")
    pattern_text = message.text

    # Валидация regex паттерна
    if pattern_type == "regex":
        import re

        try:
            re.compile(pattern_text)
        except re.error as e:
            await message.answer(
                f"❌ Некорректное регулярное выражение:\n<code>{e}</code>\n\n"
                f"Попробуйте ещё раз или отправьте /cancel",
                parse_mode="HTML",
            )
            return

    # Сохраняем паттерн
    spam_repo = SpamPatternRepository(session)

    try:
        pattern = await spam_repo.create(
            pattern=pattern_text,
            pattern_type=pattern_type,
            is_active=True,
        )

        # Сбрасываем кеш
        moderation_service = ModerationService(session)
        moderation_service.invalidate_patterns_cache()

        await message.answer(
            f"✅ <b>Паттерн добавлен</b>\n\n"
            f"ID: <code>{pattern.id}</code>\n"
            f"Тип: <code>{pattern_type}</code>\n"
            f"Паттерн: <code>{pattern_text}</code>",
            parse_mode="HTML",
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Failed to create spam pattern: {e}")
        await message.answer(
            f"❌ Ошибка при сохранении паттерна:\n<code>{e}</code>",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "spam_list", IsSuperAdmin())
@router.callback_query(F.data.startswith("spam_page:"), IsSuperAdmin())
async def callback_spam_list(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Вернуться к списку паттернов или перейти на другую страницу.

    Args:
        callback: Callback query
        user: Супер-админ
        session: Сессия БД
    """
    await callback.answer()
    if callback.message:
        await callback.message.delete()
        await cmd_spam_patterns(callback.message, user, session)
