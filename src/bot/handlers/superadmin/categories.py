"""Управление категориями."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.products import (
    get_categories_manage_keyboard,
    get_category_actions_keyboard,
    get_thread_link_method_keyboard,
    get_thread_color_keyboard,
)
from src.core.config import settings
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.category import CategoryRepository
from src.services.forum_service import ForumService
from src.utils.cancel_handler import cancel_action_and_return_to_menu, get_cancel_keyboard
from src.utils.navigation import edit_message_with_navigation

logger = get_logger(__name__)

router = Router(name="categories")


class CategoryStates(StatesGroup):
    """Состояния для работы с категориями."""

    ADD_NAME = State()
    RENAME_NAME = State()
    SET_THREAD_MANUAL = State()


@router.callback_query(F.data == "categories_manage", IsSuperAdmin())
async def categories_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Список категорий."""
    category_repo = CategoryRepository(session)
    categories = await category_repo.get_all()

    text = (
        f"📁 <b>Управление категориями</b>\n\n"
        f"Всего категорий: {len(categories)}\n\n"
        f"✅ - активна\n"
        f"🔗 - привязан thread_id"
    )

    keyboard = get_categories_manage_keyboard(categories)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data.startswith("cat_view:"), IsSuperAdmin())
async def view_category(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Просмотр категории."""
    category_id = int(callback.data.split(":")[1])

    category_repo = CategoryRepository(session)
    category = await category_repo.get(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    status = "✅ Активна" if category.is_active else "❌ Неактивна"
    thread_status = f"🔗 {category.thread_id}" if category.thread_id else "❌ Не привязан"

    text = (
        f"📁 <b>{category.name}</b>\n\n"
        f"ID: <code>{category.id}</code>\n"
        f"Статус: {status}\n"
        f"Thread ID: {thread_status}\n"
        f"Товаров: {category.products_count}"
    )

    keyboard = get_category_actions_keyboard(category.id)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data == "cat_add", IsSuperAdmin())
async def add_category_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать добавление категории."""
    await callback.answer()

    text = (
        "➕ <b>Добавление категории</b>\n\n"
        "Введите название категории"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard("cancel_category"),
        parse_mode="HTML"
    )
    await state.set_state(CategoryStates.ADD_NAME)


@router.message(IsSuperAdmin(), CategoryStates.ADD_NAME, F.text)
async def add_category_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Создать категорию."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Название слишком короткое")
        return

    category_repo = CategoryRepository(session)

    try:
        category = await category_repo.create(name=name)
        await session.commit()

        text = (
            f"✅ <b>Категория создана</b>\n\n"
            f"ID: <code>{category.id}</code>\n"
            f"Название: {category.name}\n\n"
            f"Не забудьте привязать thread_id из канала"
        )

        keyboard = get_category_actions_keyboard(category.id)

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.clear()

    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("cat_thread_menu:"), IsSuperAdmin())
async def thread_link_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Меню выбора способа привязки темы."""
    category_id = int(callback.data.split(":")[1])

    text = (
        "🔗 <b>Привязка к теме форума</b>\n\n"
        "Выберите способ привязки категории к теме:"
    )

    keyboard = get_thread_link_method_keyboard(category_id)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data.startswith("cat_thread_create:"), IsSuperAdmin())
async def create_thread_select_color(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Выбор цвета для новой темы."""
    category_id = int(callback.data.split(":")[1])

    text = (
        "🎨 <b>Выбор цвета иконки</b>\n\n"
        "Выберите цвет для иконки темы в форуме:"
    )

    keyboard = get_thread_color_keyboard(category_id)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )


@router.callback_query(F.data.startswith("cat_thread_color:"), IsSuperAdmin())
async def create_thread_with_color(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Создать новую тему в форуме с выбранным цветом."""
    parts = callback.data.split(":")
    category_id = int(parts[1])
    color = parts[2]

    # Проверяем настройку channel_id
    if not settings.channel_id:
        await callback.answer(
            "❌ Канал не настроен. Добавьте CHANNEL_ID в .env файл",
            show_alert=True,
        )
        return

    # Получаем категорию
    category_repo = CategoryRepository(session)
    category = await category_repo.get(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    await callback.answer("⏳ Создаю тему в форуме...")

    # Создаем тему
    thread_id = await ForumService.create_forum_topic(
        bot=callback.bot,
        chat_id=settings.channel_id,
        name=category.name,
        icon_color=color,
    )

    if thread_id:
        # Сохраняем thread_id в категорию
        await category_repo.update(category_id, thread_id=thread_id)
        await session.commit()

        text = (
            f"✅ <b>Тема создана!</b>\n\n"
            f"📁 Категория: {category.name}\n"
            f"🔗 Thread ID: <code>{thread_id}</code>\n"
            f"🎨 Цвет: {color}\n\n"
            f"Тема создана в форуме и привязана к категории."
        )

        keyboard = get_category_actions_keyboard(category_id)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

        logger.info(
            "Forum topic created and linked to category",
            category_id=category_id,
            thread_id=thread_id,
            color=color,
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка создания темы</b>\n\n"
            "Проверьте:\n"
            "• Бот добавлен в канал как администратор\n"
            "• В канале включены темы (Topics)\n"
            "• CHANNEL_ID указан правильно",
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("cat_thread_manual:"), IsSuperAdmin())
async def set_thread_manual_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать ручной ввод thread_id."""
    category_id = int(callback.data.split(":")[1])

    await callback.answer()
    await state.update_data(category_id=category_id)

    text = (
        "🔢 <b>Ручной ввод thread_id</b>\n\n"
        "Введите thread_id темы из форума\n\n"
        "Как узнать thread_id:\n"
        "1. Откройте тему в Telegram\n"
        "2. Используйте @userinfobot\n"
        "3. Или скопируйте из URL темы"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard("cancel_category"),
        parse_mode="HTML"
    )
    await state.set_state(CategoryStates.SET_THREAD_MANUAL)


@router.message(IsSuperAdmin(), CategoryStates.SET_THREAD_MANUAL, F.text)
async def set_thread_id_manual(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Установить thread_id вручную."""
    try:
        thread_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число")
        return

    data = await state.get_data()
    category_id = data["category_id"]

    category_repo = CategoryRepository(session)
    category = await category_repo.update(category_id, thread_id=thread_id)

    if category:
        await session.commit()
        text = (
            f"✅ <b>Thread ID привязан</b>\n\n"
            f"📁 Категория: {category.name}\n"
            f"🔗 Thread ID: <code>{thread_id}</code>"
        )

        keyboard = get_category_actions_keyboard(category.id)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка обновления")

    await state.clear()


@router.callback_query(F.data.startswith("cat_rename:"), IsSuperAdmin())
async def rename_category_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать переименование категории."""
    category_id = int(callback.data.split(":")[1])

    await callback.answer()
    await state.update_data(category_id=category_id)

    text = (
        "✏️ <b>Переименование категории</b>\n\n"
        "Введите новое название категории"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard("cancel_category"),
        parse_mode="HTML"
    )
    await state.set_state(CategoryStates.RENAME_NAME)


@router.message(IsSuperAdmin(), CategoryStates.RENAME_NAME, F.text)
async def rename_category_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Переименовать категорию."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Название слишком короткое")
        return

    data = await state.get_data()
    category_id = data["category_id"]

    category_repo = CategoryRepository(session)
    category = await category_repo.update(category_id, name=name)

    if category:
        await session.commit()
        text = f"✅ Категория переименована: {name}"

        keyboard = get_category_actions_keyboard(category.id)
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("❌ Ошибка обновления")

    await state.clear()


@router.callback_query(F.data.startswith("cat_delete:"), IsSuperAdmin())
async def delete_category(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Удалить категорию."""
    category_id = int(callback.data.split(":")[1])

    category_repo = CategoryRepository(session)
    category = await category_repo.get(category_id)

    if category and category.products_count > 0:
        await callback.answer(
            "❌ Нельзя удалить категорию с товарами",
            show_alert=True,
        )
        return

    success = await category_repo.delete(category_id)

    if success:
        await session.commit()
        await callback.answer("✅ Категория удалена", show_alert=True)
        await categories_list(callback, session, state)
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)


@router.callback_query(F.data == "cancel_category", CategoryStates.ADD_NAME)
@router.callback_query(F.data == "cancel_category", CategoryStates.RENAME_NAME)
@router.callback_query(F.data == "cancel_category", CategoryStates.SET_THREAD_MANUAL)
async def cancel_category_callback(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Отмена действия с категорией через inline кнопку."""
    await cancel_action_and_return_to_menu(
        callback=callback,
        state=state,
        user=user,
        cancel_message="❌ Действие с категорией отменено",
    )
