"""Управление администраторами (только для супер-админов)."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.user import UserRepository
from src.utils.cancel_handler import cancel_action_and_return_to_menu, get_cancel_keyboard

logger = get_logger(__name__)

router = Router(name="manage_admins")


class AddAdminStates(StatesGroup):
    """Состояния добавления администратора."""

    WAITING_USER_INFO = State()
    WAITING_ROLE = State()


def get_admin_list_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления списком админов."""
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admins:add")],
        [InlineKeyboardButton(text="🔄 Обновить список", callback_data="admins:list")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="superadmin:settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с действиями для конкретного админа."""
    buttons = [
        [InlineKeyboardButton(text="🔧 Изменить роль", callback_data=f"admins:change_role:{user_id}")],
        [InlineKeyboardButton(text="❌ Удалить админа", callback_data=f"admins:remove:{user_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admins:list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_role_selection_keyboard(user_id: int, is_adding_new: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для выбора роли.

    Args:
        user_id: ID пользователя
        is_adding_new: Если True, добавляем кнопку отмены, иначе кнопку назад
    """
    buttons = [
        [InlineKeyboardButton(text="👤 Администратор", callback_data=f"admins:set_role:{user_id}:admin")],
        [InlineKeyboardButton(text="🛡 Модератор", callback_data=f"admins:set_role:{user_id}:moderator")],
    ]

    if is_adding_new:
        buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_add_admin")])
    else:
        buttons.append([InlineKeyboardButton(text="◀️ Отмена", callback_data=f"admins:view:{user_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard(user_id: int, action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"admins:confirm:{action}:{user_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"admins:view:{user_id}"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_role_name(role: str) -> str:
    """Форматирование названия роли."""
    role_names = {
        UserRole.SUPER_ADMIN.value: "👑 Супер-администратор",
        UserRole.ADMIN.value: "👤 Администратор",
        UserRole.MODERATOR.value: "🛡 Модератор",
        UserRole.USER.value: "👥 Пользователь",
        UserRole.BANNED.value: "🚫 Заблокирован",
    }
    return role_names.get(role, role)


@router.message(Command("admins"), IsSuperAdmin())
async def cmd_admins(message: Message, session: AsyncSession) -> None:
    """Команда /admins - управление администраторами."""
    user_repo = UserRepository(session)
    admins = await user_repo.get_all_admins()

    text = "👥 <b>Управление администраторами</b>\n\n"

    if not admins:
        text += "Список администраторов пуст.\n\n"
        await message.answer(
            text=text,
            reply_markup=get_admin_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        text += f"Всего администраторов: {len(admins)}\n\n"
        text += "Нажмите на администратора для управления:"

        # Создаем клавиатуру со списком админов
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()

        for admin in admins:
            role_emoji = "👑" if admin.is_super_admin else "👤" if admin.role == UserRole.ADMIN.value else "🛡"
            username_str = f"@{admin.username}" if admin.username else ""
            button_text = f"{role_emoji} {admin.full_name} {username_str}"
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"admins:view:{admin.id}"
                )
            )

        # Добавляем кнопки управления
        builder.row(
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="admins:add")
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Обновить список", callback_data="admins:list")
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="superadmin:settings")
        )

        await message.answer(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admins:list", IsSuperAdmin())
async def show_admins_list(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать список администраторов."""
    await callback.answer()

    user_repo = UserRepository(session)
    admins = await user_repo.get_all_admins()

    text = "👥 <b>Управление администраторами</b>\n\n"

    if not admins:
        text += "Список администраторов пуст.\n\n"
        await callback.message.edit_text(
            text=text,
            reply_markup=get_admin_list_keyboard(),
            parse_mode="HTML",
        )
    else:
        text += f"Всего администраторов: {len(admins)}\n\n"
        text += "Нажмите на администратора для управления:"

        # Создаем клавиатуру со списком админов
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()

        for admin in admins:
            role_emoji = "👑" if admin.is_super_admin else "👤" if admin.role == UserRole.ADMIN.value else "🛡"
            username_str = f"@{admin.username}" if admin.username else ""
            button_text = f"{role_emoji} {admin.full_name} {username_str}"
            builder.row(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"admins:view:{admin.id}"
                )
            )

        # Добавляем кнопки управления
        builder.row(
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="admins:add")
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Обновить список", callback_data="admins:list")
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Назад", callback_data="superadmin:settings")
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admins:add", IsSuperAdmin())
async def start_add_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление администратора."""
    await callback.answer()

    text = (
        "➕ <b>Добавление администратора</b>\n\n"
        "Отправьте одно из:\n"
        "• Telegram ID пользователя (числовой)\n"
        "• Username пользователя (@username)\n"
        "• Перешлите сообщение от пользователя"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard("cancel_add_admin"),
        parse_mode="HTML"
    )
    await state.set_state(AddAdminStates.WAITING_USER_INFO)


@router.message(IsSuperAdmin(), AddAdminStates.WAITING_USER_INFO, ~F.text.startswith("/"))
async def process_user_info(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка информации о пользователе для добавления в админы."""
    # Игнорируем кнопки reply-клавиатуры - сбрасываем состояние, чтобы другие хендлеры обработали
    reply_buttons = ["👑 Супер-админ панель", "👤 Админ-панель", "📋 Заказы", "📦 Каталог", "🏠 Главное меню"]
    if message.text and message.text in reply_buttons:
        await state.clear()
        return

    user_repo = UserRepository(session)
    target_user = None

    # Если сообщение переслано, берем информацию о пересланном пользователе
    if message.forward_from:
        target_user = await user_repo.get_by_telegram_id(message.forward_from.id)
        if not target_user:
            await message.answer(
                f"❌ Пользователь <b>{message.forward_from.full_name}</b> "
                f"(ID: <code>{message.forward_from.id}</code>) не найден в базе данных.\n"
                f"Пользователь должен сначала запустить бота.",
                parse_mode="HTML",
            )
            return

    # Если введен текст
    elif message.text:
        text = message.text.strip()

        # Попытка парсинга как ID
        if text.isdigit():
            telegram_id = int(text)
            target_user = await user_repo.get_by_telegram_id(telegram_id)

        # Попытка парсинга как username
        elif text.startswith("@"):
            username = text[1:]  # Убираем @
            target_user = await user_repo.get_by_username(username)
        else:
            target_user = await user_repo.get_by_username(text)

        if not target_user:
            await message.answer(
                "❌ Пользователь не найден в базе данных.\n"
                "Пользователь должен сначала запустить бота.",
                parse_mode="HTML",
            )
            return

    else:
        await message.answer(
            "❌ Неверный формат. Отправьте ID, username или перешлите сообщение от пользователя."
        )
        return

    # Проверка, что пользователь не супер-админ
    if target_user.is_super_admin:
        await message.answer(
            f"⚠️ <b>{target_user.full_name}</b> уже является супер-администратором.\n"
            f"Супер-администраторы назначаются через .env файл.",
            parse_mode="HTML",
        )
        await state.clear()
        return

    # Проверка, что пользователь уже не админ/модератор
    if target_user.role in [UserRole.ADMIN.value, UserRole.MODERATOR.value]:
        role_name = format_role_name(target_user.role)
        await message.answer(
            f"⚠️ <b>{target_user.full_name}</b> уже имеет роль: {role_name}",
            parse_mode="HTML",
        )
        await state.clear()
        return

    # Сохраняем ID пользователя и показываем выбор роли
    await state.update_data(target_user_id=target_user.id)

    username_str = f"@{target_user.username}" if target_user.username else "без username"
    text = (
        f"✅ Пользователь найден:\n\n"
        f"<b>{target_user.full_name}</b>\n"
        f"ID: <code>{target_user.telegram_id}</code>\n"
        f"Username: {username_str}\n\n"
        f"Выберите роль для назначения:"
    )

    await message.answer(
        text=text,
        reply_markup=get_role_selection_keyboard(target_user.id, is_adding_new=True),
        parse_mode="HTML",
    )
    await state.set_state(AddAdminStates.WAITING_ROLE)


@router.callback_query(
    IsSuperAdmin(),
    AddAdminStates.WAITING_ROLE,
    F.data.startswith("admins:set_role:")
)
async def set_admin_role(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Назначить роль пользователю."""
    await callback.answer()

    parts = callback.data.split(":")
    target_user_id = int(parts[2])
    new_role = parts[3]

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(target_user_id)

    if not target_user:
        await callback.message.edit_text("❌ Пользователь не найден")
        await state.clear()
        return

    # Назначаем роль
    role_value = UserRole.ADMIN.value if new_role == "admin" else UserRole.MODERATOR.value
    target_user.role = role_value
    await session.commit()
    await session.refresh(target_user)

    username_str = f"@{target_user.username}" if target_user.username else "без username"
    text = (
        f"✅ <b>Роль успешно назначена!</b>\n\n"
        f"Пользователь: <b>{target_user.full_name}</b>\n"
        f"ID: <code>{target_user.telegram_id}</code>\n"
        f"Username: {username_str}\n"
        f"Новая роль: {format_role_name(role_value)}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_list_keyboard(),
        parse_mode="HTML",
    )

    await state.clear()

    logger.info(
        "Admin role assigned",
        target_user_id=target_user.id,
        new_role=role_value,
        by_user_id=user.id,
    )


@router.callback_query(F.data.startswith("admins:view:"), IsSuperAdmin())
async def view_admin_details(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать детали администратора."""
    await callback.answer()

    user_id = int(callback.data.split(":")[2])
    user_repo = UserRepository(session)
    admin = await user_repo.get_by_id(user_id)

    if not admin:
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    username_str = f"@{admin.username}" if admin.username else "без username"
    text = (
        f"👤 <b>Информация об администраторе</b>\n\n"
        f"<b>{admin.full_name}</b>\n"
        f"ID: <code>{admin.telegram_id}</code>\n"
        f"Username: {username_str}\n"
        f"Роль: {format_role_name(admin.role)}\n\n"
        f"Выберите действие:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_actions_keyboard(user_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admins:change_role:"), IsSuperAdmin())
async def change_admin_role(callback: CallbackQuery, session: AsyncSession) -> None:
    """Изменить роль администратора."""
    await callback.answer()

    user_id = int(callback.data.split(":")[2])
    user_repo = UserRepository(session)
    admin = await user_repo.get_by_id(user_id)

    if not admin:
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    if admin.is_super_admin:
        await callback.answer(
            "⚠️ Нельзя изменить роль супер-администратора",
            show_alert=True,
        )
        return

    text = (
        f"🔧 <b>Изменение роли</b>\n\n"
        f"Пользователь: <b>{admin.full_name}</b>\n"
        f"Текущая роль: {format_role_name(admin.role)}\n\n"
        f"Выберите новую роль:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_role_selection_keyboard(user_id),
        parse_mode="HTML",
    )


@router.callback_query(
    IsSuperAdmin(),
    F.data.startswith("admins:set_role:"),
)
async def change_existing_admin_role(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Изменить роль существующего администратора (без FSM)."""
    # Проверяем, что мы НЕ в состоянии добавления нового админа
    current_state = await state.get_state()
    if current_state == AddAdminStates.WAITING_ROLE:
        # Если в FSM состоянии, пропускаем - обработает другой handler
        return
    await callback.answer()

    parts = callback.data.split(":")
    target_user_id = int(parts[2])
    new_role = parts[3]

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(target_user_id)

    if not target_user:
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    if target_user.is_super_admin:
        await callback.answer(
            "⚠️ Нельзя изменить роль супер-администратора",
            show_alert=True,
        )
        return

    # Назначаем роль
    old_role = target_user.role
    role_value = UserRole.ADMIN.value if new_role == "admin" else UserRole.MODERATOR.value
    target_user.role = role_value
    await session.commit()
    await session.refresh(target_user)

    username_str = f"@{target_user.username}" if target_user.username else "без username"
    text = (
        f"✅ <b>Роль успешно изменена!</b>\n\n"
        f"Пользователь: <b>{target_user.full_name}</b>\n"
        f"ID: <code>{target_user.telegram_id}</code>\n"
        f"Username: {username_str}\n\n"
        f"Старая роль: {format_role_name(old_role)}\n"
        f"Новая роль: {format_role_name(role_value)}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_actions_keyboard(target_user_id),
        parse_mode="HTML",
    )

    logger.info(
        "Admin role changed",
        target_user_id=target_user.id,
        old_role=old_role,
        new_role=role_value,
        by_user_id=user.id,
    )


@router.callback_query(F.data.startswith("admins:remove:"), IsSuperAdmin())
async def confirm_remove_admin(callback: CallbackQuery, session: AsyncSession) -> None:
    """Подтверждение удаления администратора."""
    await callback.answer()

    user_id = int(callback.data.split(":")[2])
    user_repo = UserRepository(session)
    admin = await user_repo.get_by_id(user_id)

    if not admin:
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    if admin.is_super_admin:
        await callback.answer(
            "⚠️ Нельзя удалить супер-администратора",
            show_alert=True,
        )
        return

    text = (
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить права администратора у:\n\n"
        f"<b>{admin.full_name}</b>\n"
        f"ID: <code>{admin.telegram_id}</code>\n"
        f"Текущая роль: {format_role_name(admin.role)}\n\n"
        f"Пользователь станет обычным пользователем."
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_confirm_keyboard(user_id, "remove"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admins:confirm:remove:"), IsSuperAdmin())
async def remove_admin(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Удалить администратора (понизить до обычного пользователя)."""
    await callback.answer()

    user_id = int(callback.data.split(":")[3])
    user_repo = UserRepository(session)
    admin = await user_repo.get_by_id(user_id)

    if not admin:
        await callback.message.edit_text("❌ Пользователь не найден")
        return

    if admin.is_super_admin:
        await callback.answer(
            "⚠️ Нельзя удалить супер-администратора",
            show_alert=True,
        )
        return

    # Понижаем до обычного пользователя
    admin.role = UserRole.USER.value
    await session.commit()
    await session.refresh(admin)

    text = (
        f"✅ <b>Права администратора удалены</b>\n\n"
        f"Пользователь <b>{admin.full_name}</b> (ID: <code>{admin.telegram_id}</code>) "
        f"теперь имеет роль: {format_role_name(UserRole.USER.value)}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_list_keyboard(),
        parse_mode="HTML",
    )

    logger.info(
        "Admin role removed",
        target_user_id=admin.id,
        by_user_id=user.id,
    )


@router.callback_query(F.data == "cancel_add_admin", AddAdminStates.WAITING_USER_INFO)
@router.callback_query(F.data == "cancel_add_admin", AddAdminStates.WAITING_ROLE)
async def cancel_add_admin_callback(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Отмена добавления администратора через inline кнопку."""
    await cancel_action_and_return_to_menu(
        callback=callback,
        state=state,
        user=user,
        cancel_message="❌ Добавление администратора отменено",
    )
