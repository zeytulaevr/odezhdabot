"""Управление категориями."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.products import get_categories_manage_keyboard, get_category_actions_keyboard
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.category import CategoryRepository

logger = get_logger(__name__)

router = Router(name="categories")


class CategoryStates(StatesGroup):
    """Состояния для работы с категориями."""

    ADD_NAME = State()
    RENAME_NAME = State()
    SET_THREAD = State()


@router.callback_query(F.data == "categories_manage", IsSuperAdmin())
async def categories_list(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Список категорий."""
    await callback.answer()

    category_repo = CategoryRepository(session)
    categories = await category_repo.get_all()

    text = (
        f"📁 <b>Управление категориями</b>\n\n"
        f"Всего категорий: {len(categories)}\n\n"
        f"✅ - активна\n"
        f"🔗 - привязан thread_id"
    )

    keyboard = get_categories_manage_keyboard(categories)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("cat_view:"), IsSuperAdmin())
async def view_category(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Просмотр категории."""
    category_id = int(callback.data.split(":")[1])

    await callback.answer()

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

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "cat_add", IsSuperAdmin())
async def add_category_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать добавление категории."""
    await callback.answer()

    text = (
        "➕ <b>Добавление категории</b>\n\n"
        "Введите название категории\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="HTML")
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


@router.callback_query(F.data.startswith("cat_thread:"), IsSuperAdmin())
async def set_thread_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать привязку thread_id."""
    category_id = int(callback.data.split(":")[1])

    await callback.answer()
    await state.update_data(category_id=category_id)

    text = (
        "🔗 <b>Привязка thread_id</b>\n\n"
        "Введите thread_id ветки из канала\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(CategoryStates.SET_THREAD)


@router.message(IsSuperAdmin(), CategoryStates.SET_THREAD, F.text)
async def set_thread_id(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Установить thread_id."""
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
        text = f"✅ Thread ID привязан: {thread_id}"

        keyboard = get_category_actions_keyboard(category.id)
        await message.answer(text, reply_markup=keyboard)
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
        "Введите новое название категории\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="HTML")
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
        await categories_list(callback, session)
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)
