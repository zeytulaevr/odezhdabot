"""Хендлеры для управления настройками бота."""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.settings import (
    get_bonus_settings_keyboard,
    get_cancel_keyboard,
    get_catalog_settings_keyboard,
    get_message_input_keyboard,
    get_notification_settings_keyboard,
    get_order_settings_keyboard,
    get_payment_settings_keyboard,
    get_settings_menu_keyboard,
)
from src.bot.states.settings import SettingsStates
from src.core.logging import get_logger
from src.database.models.bot_settings import BotSettings
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="settings")


# Обработчик отмены для всех FSM состояний
@router.callback_query(F.data == "settings:cancel", IsSuperAdmin())
async def handle_cancel_button(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработка кнопки отмены во время ввода."""
    await state.clear()
    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите раздел для настройки:"
    )
    keyboard = get_settings_menu_keyboard()
    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    await callback.answer("❌ Отменено")


@router.callback_query(F.data.startswith("settings:"), IsSuperAdmin())
async def process_settings_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка callback от меню настроек.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
        state: FSM контекст
    """
    parts = callback.data.split(":")
    section = parts[1] if len(parts) > 1 else None
    subsection = parts[2] if len(parts) > 2 else None

    # Получаем текущие настройки
    settings = await BotSettings.get_settings(session)

    # Главное меню настроек
    if section == "menu" or (section and not subsection):
        if section == "menu":
            # Возврат в главное меню настроек
            text = (
                "⚙️ <b>Настройки бота</b>\n\n"
                "Выберите раздел для настройки:"
            )
            keyboard = get_settings_menu_keyboard()
        elif section == "bonus":
            # Настройки бонусной системы
            text = (
                "🎁 <b>Бонусная система</b>\n\n"
                f"📊 Процент начисления: <code>{settings.bonus_purchase_percent}%</code>\n"
                f"💰 Макс. % оплаты бонусами: <code>{settings.bonus_max_payment_percent}%</code>\n"
                f"🛒 Мин. сумма для начисления: <code>{settings.bonus_min_order_amount} ₽</code>\n"
                f"✅ Статус: <b>{'Включена' if settings.bonus_enabled else 'Выключена'}</b>\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_bonus_settings_keyboard()
        elif section == "payment":
            # Настройки платежей
            payment_details = settings.payment_details or "<i>Не указаны</i>"
            payment_instructions = settings.payment_instructions or "<i>Не указаны</i>"
            alternative_contact = settings.alternative_contact_username or "<i>Не указан</i>"

            text = (
                "💳 <b>Настройки платежей</b>\n\n"
                f"<b>Реквизиты:</b>\n{payment_details}\n\n"
                f"<b>Инструкции:</b>\n{payment_instructions}\n\n"
                f"<b>Альтернативный контакт:</b> {alternative_contact}\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_payment_settings_keyboard()
        elif section == "orders":
            # Настройки заказов
            text = (
                "📦 <b>Настройки заказов</b>\n\n"
                f"💵 Мин. сумма заказа: <code>{settings.min_order_amount} ₽</code>\n"
                f"📦 Макс. товаров в заказе: <code>{settings.max_items_per_order}</code>\n"
                f"🔢 Макс. количество одного товара: <code>{settings.max_quantity_per_item}</code>\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_order_settings_keyboard()
        elif section == "notifications":
            # Настройки уведомлений
            welcome = settings.welcome_message or "<i>Не задано</i>"
            help_msg = settings.help_message or "<i>Не задано</i>"
            large_order = settings.large_order_message or "<i>Не задано</i>"

            text = (
                "📬 <b>Настройки уведомлений</b>\n\n"
                f"<b>Приветствие:</b>\n{welcome[:100]}...\n\n"
                f"<b>Помощь:</b>\n{help_msg[:100]}...\n\n"
                f"<b>Большой заказ:</b>\n{large_order[:100]}...\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_notification_settings_keyboard()
        elif section == "catalog":
            # Настройки каталога
            text = (
                "📚 <b>Настройки каталога</b>\n\n"
                f"📄 Товаров на странице: <code>{settings.products_per_page}</code>\n"
                f"🖼 Товары без фото: <b>{'Показывать' if settings.show_products_without_photos else 'Скрывать'}</b>\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_catalog_settings_keyboard()
        else:
            await callback.answer("⚠️ Неизвестный раздел")
            return

        if callback.message:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        await callback.answer()
        return

    # Завершение ввода сообщения с медиа
    if section == "message_done":
        # Получаем данные из state
        data = await state.get_data()
        message_text = data.get("message_text")
        message_media = data.get("message_media")
        settings_section = data.get("settings_section")
        message_type = data.get("message_type")

        if not message_text:
            await callback.answer("⚠️ Сначала отправьте текст сообщения", show_alert=True)
            return

        # Сохраняем в БД
        settings = await BotSettings.get_settings(session)

        if message_type == "welcome":
            settings.welcome_message = message_text
            settings.welcome_message_media = message_media
            success_msg = "✅ Приветственное сообщение обновлено"
        elif message_type == "help":
            settings.help_message = message_text
            settings.help_message_media = message_media
            success_msg = "✅ Сообщение помощи обновлено"
        elif message_type == "large_order":
            settings.large_order_message = message_text
            settings.large_order_message_media = message_media
            success_msg = "✅ Сообщение о большом заказе обновлено"

        await session.commit()
        await state.clear()

        # Показываем меню уведомлений
        text = f"{success_msg}\n\nВыберите другой параметр для изменения:"
        keyboard = get_notification_settings_keyboard()

        if callback.message:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        await callback.answer(success_msg)
        return

    # Обработка конкретных настроек
    await state.update_data(settings_section=section)

    # Бонусная система
    if section == "bonus":
        if subsection == "purchase_percent":
            await state.set_state(SettingsStates.ENTER_BONUS_PURCHASE_PERCENT)
            text = (
                "📊 <b>Процент начисления бонусов за покупку</b>\n\n"
                f"Текущее значение: <code>{settings.bonus_purchase_percent}%</code>\n\n"
                "Введите новый процент (например, 5 или 10.5):\n"
                "От 0 до 100"
            )
        elif subsection == "max_payment_percent":
            await state.set_state(SettingsStates.ENTER_BONUS_MAX_PAYMENT_PERCENT)
            text = (
                "💰 <b>Максимальный процент оплаты бонусами</b>\n\n"
                f"Текущее значение: <code>{settings.bonus_max_payment_percent}%</code>\n\n"
                "Введите новый процент (например, 50 или 75):\n"
                "От 0 до 100"
            )
        elif subsection == "min_order_amount":
            await state.set_state(SettingsStates.ENTER_BONUS_MIN_ORDER_AMOUNT)
            text = (
                "🛒 <b>Минимальная сумма заказа для начисления бонусов</b>\n\n"
                f"Текущее значение: <code>{settings.bonus_min_order_amount} ₽</code>\n\n"
                "Введите новую сумму (например, 500 или 1000):"
            )
        elif subsection == "toggle_enabled":
            # Переключаем состояние
            settings.bonus_enabled = not settings.bonus_enabled
            await session.commit()

            status = "включена" if settings.bonus_enabled else "выключена"
            await callback.answer(f"✅ Бонусная система {status}")

            # Обновляем меню
            text = (
                "🎁 <b>Бонусная система</b>\n\n"
                f"📊 Процент начисления: <code>{settings.bonus_purchase_percent}%</code>\n"
                f"💰 Макс. % оплаты бонусами: <code>{settings.bonus_max_payment_percent}%</code>\n"
                f"🛒 Мин. сумма для начисления: <code>{settings.bonus_min_order_amount} ₽</code>\n"
                f"✅ Статус: <b>{'Включена' if settings.bonus_enabled else 'Выключена'}</b>\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_bonus_settings_keyboard()
            if callback.message:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            return

    # Платежи
    elif section == "payment":
        if subsection == "details":
            await state.set_state(SettingsStates.ENTER_PAYMENT_DETAILS)
            current = settings.payment_details or "Не указаны"
            text = (
                "💳 <b>Реквизиты для оплаты</b>\n\n"
                f"Текущие реквизиты:\n<code>{current}</code>\n\n"
                "Введите новые реквизиты (номер карты, счёт и т.д.):"
            )
        elif subsection == "instructions":
            await state.set_state(SettingsStates.ENTER_PAYMENT_INSTRUCTIONS)
            current = settings.payment_instructions or "Не указаны"
            text = (
                "📝 <b>Инструкции по оплате</b>\n\n"
                f"Текущие инструкции:\n<code>{current}</code>\n\n"
                "Введите новые инструкции для клиента:"
            )
        elif subsection == "alternative_contact":
            await state.set_state(SettingsStates.ENTER_ALTERNATIVE_CONTACT)
            current = settings.alternative_contact_username or "Не указан"
            text = (
                "👤 <b>Альтернативный контакт для заказов</b>\n\n"
                f"Текущий контакт: <code>{current}</code>\n\n"
                "Введите новый username (например, @username):"
            )

    # Заказы
    elif section == "orders":
        if subsection == "min_amount":
            await state.set_state(SettingsStates.ENTER_MIN_ORDER_AMOUNT)
            text = (
                "💵 <b>Минимальная сумма заказа</b>\n\n"
                f"Текущее значение: <code>{settings.min_order_amount} ₽</code>\n\n"
                "Введите новую минимальную сумму:"
            )
        elif subsection == "max_items":
            await state.set_state(SettingsStates.ENTER_MAX_ITEMS_PER_ORDER)
            text = (
                "📦 <b>Максимальное количество товаров в заказе</b>\n\n"
                f"Текущее значение: <code>{settings.max_items_per_order}</code>\n\n"
                "Введите новое максимальное количество:"
            )
        elif subsection == "max_quantity":
            await state.set_state(SettingsStates.ENTER_MAX_QUANTITY_PER_ITEM)
            text = (
                "🔢 <b>Максимальное количество одного товара</b>\n\n"
                f"Текущее значение: <code>{settings.max_quantity_per_item}</code>\n\n"
                "Введите новое максимальное количество:"
            )

    # Уведомления
    elif section == "notifications":
        if subsection == "welcome":
            await state.set_state(SettingsStates.ENTER_WELCOME_MESSAGE)
            await state.update_data(message_type="welcome")
            current = settings.welcome_message or "Не задано"
            has_media = "Да" if settings.welcome_message_media else "Нет"
            text = (
                "👋 <b>Приветственное сообщение</b>\n\n"
                f"📝 Текущий текст:\n<code>{current}</code>\n"
                f"🖼 Медиа: {has_media}\n\n"
                "📤 Отправьте новый текст сообщения\n"
                "📷 Можете прикрепить фото или видео\n\n"
                "Когда закончите, нажмите <b>✅ Готово</b>"
            )
        elif subsection == "help":
            await state.set_state(SettingsStates.ENTER_HELP_MESSAGE)
            await state.update_data(message_type="help")
            current = settings.help_message or "Не задано"
            has_media = "Да" if settings.help_message_media else "Нет"
            text = (
                "ℹ️ <b>Сообщение помощи</b>\n\n"
                f"📝 Текущий текст:\n<code>{current}</code>\n"
                f"🖼 Медиа: {has_media}\n\n"
                "📤 Отправьте новый текст сообщения\n"
                "📷 Можете прикрепить фото или видео\n\n"
                "Когда закончите, нажмите <b>✅ Готово</b>"
            )
        elif subsection == "large_order":
            await state.set_state(SettingsStates.ENTER_LARGE_ORDER_MESSAGE)
            await state.update_data(message_type="large_order")
            current = settings.large_order_message or "Не задано"
            has_media = "Да" if settings.large_order_message_media else "Нет"
            text = (
                "📦 <b>Сообщение о большом заказе</b>\n\n"
                f"📝 Текущий текст:\n<code>{current}</code>\n"
                f"🖼 Медиа: {has_media}\n\n"
                "📤 Отправьте новый текст сообщения\n"
                "📷 Можете прикрепить фото или видео\n\n"
                "Показывается при попытке заказать 10+ штук\n"
                "Когда закончите, нажмите <b>✅ Готово</b>"
            )

    # Каталог
    elif section == "catalog":
        if subsection == "per_page":
            await state.set_state(SettingsStates.ENTER_PRODUCTS_PER_PAGE)
            text = (
                "📄 <b>Количество товаров на странице</b>\n\n"
                f"Текущее значение: <code>{settings.products_per_page}</code>\n\n"
                "Введите новое количество (от 5 до 50):"
            )
        elif subsection == "toggle_without_photos":
            # Переключаем состояние
            settings.show_products_without_photos = not settings.show_products_without_photos
            await session.commit()

            status = "показывать" if settings.show_products_without_photos else "скрывать"
            await callback.answer(f"✅ Товары без фото: {status}")

            # Обновляем меню
            text = (
                "📚 <b>Настройки каталога</b>\n\n"
                f"📄 Товаров на странице: <code>{settings.products_per_page}</code>\n"
                f"🖼 Товары без фото: <b>{'Показывать' if settings.show_products_without_photos else 'Скрывать'}</b>\n\n"
                "Выберите параметр для изменения:"
            )
            keyboard = get_catalog_settings_keyboard()
            if callback.message:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            return

    # Отправляем сообщение с запросом ввода
    # Для уведомлений используем специальную клавиатуру с кнопкой "Готово"
    if section == "notifications":
        keyboard = get_message_input_keyboard()
    else:
        keyboard = get_cancel_keyboard()

    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    await callback.answer()


# Обработчики ввода значений

@router.message(SettingsStates.ENTER_BONUS_PURCHASE_PERCENT, IsSuperAdmin())
async def process_bonus_purchase_percent(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода процента начисления бонусов."""
    try:
        value = Decimal(message.text.strip().replace(",", "."))
        if value < 0 or value > 100:
            await message.answer("❌ Процент должен быть от 0 до 100")
            return

        settings = await BotSettings.get_settings(session)
        settings.bonus_purchase_percent = value
        await session.commit()

        await message.answer(
            f"✅ Процент начисления бонусов изменён на {value}%",
            reply_markup=get_bonus_settings_keyboard(),
        )
        await state.clear()

    except (ValueError, InvalidOperation):
        await message.answer("❌ Введите корректное число")


@router.message(SettingsStates.ENTER_BONUS_MAX_PAYMENT_PERCENT, IsSuperAdmin())
async def process_bonus_max_payment_percent(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода макс. процента оплаты бонусами."""
    try:
        value = Decimal(message.text.strip().replace(",", "."))
        if value < 0 or value > 100:
            await message.answer("❌ Процент должен быть от 0 до 100")
            return

        settings = await BotSettings.get_settings(session)
        settings.bonus_max_payment_percent = value
        await session.commit()

        await message.answer(
            f"✅ Макс. процент оплаты бонусами изменён на {value}%",
            reply_markup=get_bonus_settings_keyboard(),
        )
        await state.clear()

    except (ValueError, InvalidOperation):
        await message.answer("❌ Введите корректное число")


@router.message(SettingsStates.ENTER_BONUS_MIN_ORDER_AMOUNT, IsSuperAdmin())
async def process_bonus_min_order_amount(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода мин. суммы для начисления бонусов."""
    try:
        value = Decimal(message.text.strip().replace(",", "."))
        if value < 0:
            await message.answer("❌ Сумма не может быть отрицательной")
            return

        settings = await BotSettings.get_settings(session)
        settings.bonus_min_order_amount = value
        await session.commit()

        await message.answer(
            f"✅ Мин. сумма для начисления бонусов изменена на {value} ₽",
            reply_markup=get_bonus_settings_keyboard(),
        )
        await state.clear()

    except (ValueError, InvalidOperation):
        await message.answer("❌ Введите корректное число")


@router.message(SettingsStates.ENTER_PAYMENT_DETAILS, IsSuperAdmin())
async def process_payment_details(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода реквизитов для оплаты."""
    value = message.text.strip()

    settings = await BotSettings.get_settings(session)
    settings.payment_details = value
    await session.commit()

    await message.answer(
        "✅ Реквизиты для оплаты обновлены",
        reply_markup=get_payment_settings_keyboard(),
    )
    await state.clear()


@router.message(SettingsStates.ENTER_PAYMENT_INSTRUCTIONS, IsSuperAdmin())
async def process_payment_instructions(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода инструкций по оплате."""
    value = message.text.strip()

    settings = await BotSettings.get_settings(session)
    settings.payment_instructions = value
    await session.commit()

    await message.answer(
        "✅ Инструкции по оплате обновлены",
        reply_markup=get_payment_settings_keyboard(),
    )
    await state.clear()


@router.message(SettingsStates.ENTER_ALTERNATIVE_CONTACT, IsSuperAdmin())
async def process_alternative_contact(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода альтернативного контакта."""
    value = message.text.strip()

    # Добавляем @ если его нет
    if value and not value.startswith("@"):
        value = f"@{value}"

    settings = await BotSettings.get_settings(session)
    settings.alternative_contact_username = value
    await session.commit()

    await message.answer(
        f"✅ Альтернативный контакт обновлён: {value}",
        reply_markup=get_payment_settings_keyboard(),
    )
    await state.clear()


@router.message(SettingsStates.ENTER_MIN_ORDER_AMOUNT, IsSuperAdmin())
async def process_min_order_amount(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода мин. суммы заказа."""
    try:
        value = Decimal(message.text.strip().replace(",", "."))
        if value < 0:
            await message.answer("❌ Сумма не может быть отрицательной")
            return

        settings = await BotSettings.get_settings(session)
        settings.min_order_amount = value
        await session.commit()

        await message.answer(
            f"✅ Мин. сумма заказа изменена на {value} ₽",
            reply_markup=get_order_settings_keyboard(),
        )
        await state.clear()

    except (ValueError, InvalidOperation):
        await message.answer("❌ Введите корректное число")


@router.message(SettingsStates.ENTER_MAX_ITEMS_PER_ORDER, IsSuperAdmin())
async def process_max_items_per_order(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода макс. товаров в заказе."""
    try:
        value = int(message.text.strip())
        if value < 1 or value > 100:
            await message.answer("❌ Количество должно быть от 1 до 100")
            return

        settings = await BotSettings.get_settings(session)
        settings.max_items_per_order = value
        await session.commit()

        await message.answer(
            f"✅ Макс. товаров в заказе изменено на {value}",
            reply_markup=get_order_settings_keyboard(),
        )
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите целое число")


@router.message(SettingsStates.ENTER_MAX_QUANTITY_PER_ITEM, IsSuperAdmin())
async def process_max_quantity_per_item(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода макс. количества одного товара."""
    try:
        value = int(message.text.strip())
        if value < 1 or value > 99:
            await message.answer("❌ Количество должно быть от 1 до 99")
            return

        settings = await BotSettings.get_settings(session)
        settings.max_quantity_per_item = value
        await session.commit()

        await message.answer(
            f"✅ Макс. количество одного товара изменено на {value}",
            reply_markup=get_order_settings_keyboard(),
        )
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите целое число")


@router.message(SettingsStates.ENTER_WELCOME_MESSAGE, IsSuperAdmin())
async def process_welcome_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода приветственного сообщения."""
    # Сохраняем текст в state
    if message.text:
        await state.update_data(message_text=message.text.strip())
        await message.answer(
            "✅ Текст сохранен\n\n"
            "Можете отправить фото/видео или нажмите <b>✅ Готово</b>",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )

    # Сохраняем медиа в state
    elif message.photo:
        file_id = message.photo[-1].file_id
        await state.update_data(message_media=file_id)
        # Если есть caption, сохраняем как текст
        if message.caption:
            await state.update_data(message_text=message.caption.strip())
        await message.answer(
            "✅ Фото сохранено\n\n"
            "Нажмите <b>✅ Готово</b> для завершения",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )

    elif message.video:
        file_id = message.video.file_id
        await state.update_data(message_media=file_id)
        # Если есть caption, сохраняем как текст
        if message.caption:
            await state.update_data(message_text=message.caption.strip())
        await message.answer(
            "✅ Видео сохранено\n\n"
            "Нажмите <b>✅ Готово</b> для завершения",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )


@router.message(SettingsStates.ENTER_HELP_MESSAGE, IsSuperAdmin())
async def process_help_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода сообщения помощи."""
    # Сохраняем текст в state
    if message.text:
        await state.update_data(message_text=message.text.strip())
        await message.answer(
            "✅ Текст сохранен\n\n"
            "Можете отправить фото/видео или нажмите <b>✅ Готово</b>",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )

    # Сохраняем медиа в state
    elif message.photo:
        file_id = message.photo[-1].file_id
        await state.update_data(message_media=file_id)
        # Если есть caption, сохраняем как текст
        if message.caption:
            await state.update_data(message_text=message.caption.strip())
        await message.answer(
            "✅ Фото сохранено\n\n"
            "Нажмите <b>✅ Готово</b> для завершения",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )

    elif message.video:
        file_id = message.video.file_id
        await state.update_data(message_media=file_id)
        # Если есть caption, сохраняем как текст
        if message.caption:
            await state.update_data(message_text=message.caption.strip())
        await message.answer(
            "✅ Видео сохранено\n\n"
            "Нажмите <b>✅ Готово</b> для завершения",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )


@router.message(SettingsStates.ENTER_LARGE_ORDER_MESSAGE, IsSuperAdmin())
async def process_large_order_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода сообщения о большом заказе."""
    # Сохраняем текст в state
    if message.text:
        await state.update_data(message_text=message.text.strip())
        await message.answer(
            "✅ Текст сохранен\n\n"
            "Можете отправить фото/видео или нажмите <b>✅ Готово</b>",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )

    # Сохраняем медиа в state
    elif message.photo:
        file_id = message.photo[-1].file_id
        await state.update_data(message_media=file_id)
        # Если есть caption, сохраняем как текст
        if message.caption:
            await state.update_data(message_text=message.caption.strip())
        await message.answer(
            "✅ Фото сохранено\n\n"
            "Нажмите <b>✅ Готово</b> для завершения",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )

    elif message.video:
        file_id = message.video.file_id
        await state.update_data(message_media=file_id)
        # Если есть caption, сохраняем как текст
        if message.caption:
            await state.update_data(message_text=message.caption.strip())
        await message.answer(
            "✅ Видео сохранено\n\n"
            "Нажмите <b>✅ Готово</b> для завершения",
            parse_mode="HTML",
            reply_markup=get_message_input_keyboard(),
        )


@router.message(SettingsStates.ENTER_PRODUCTS_PER_PAGE, IsSuperAdmin())
async def process_products_per_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода количества товаров на странице."""
    try:
        value = int(message.text.strip())
        if value < 5 or value > 50:
            await message.answer("❌ Количество должно быть от 5 до 50")
            return

        settings = await BotSettings.get_settings(session)
        settings.products_per_page = value
        await session.commit()

        await message.answer(
            f"✅ Количество товаров на странице изменено на {value}",
            reply_markup=get_catalog_settings_keyboard(),
        )
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите целое число")
