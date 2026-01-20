"""Загрузка товаров из Excel/CSV файла."""

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.category import CategoryRepository
from src.services.product_service import ProductService
from src.utils.excel_parser import ExcelParser

logger = get_logger(__name__)

router = Router(name="product_upload")


class UploadFileStates(StatesGroup):
    """Состояния загрузки файла."""

    WAITING_FILE = State()


@router.callback_query(F.data == "prod_upload_file", IsSuperAdmin())
async def start_upload_file(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать загрузку файла."""
    await callback.answer()

    text = (
        "📤 <b>Загрузка товаров из файла</b>\n\n"
        "Отправьте Excel (.xlsx) или CSV файл\n\n"
        "<b>Формат файла:</b>\n"
        "• Название\n"
        "• Описание\n"
        "• Цена\n"
        "• Размеры (через запятую)\n"
        "• Категория\n"
        "• Фото (URL или пусто)\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(UploadFileStates.WAITING_FILE)


@router.message(IsSuperAdmin(), UploadFileStates.WAITING_FILE, F.document)
async def process_file(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Обработка загруженного файла."""
    document = message.document

    # Проверяем тип файла
    if not (
        document.file_name.endswith((".xlsx", ".xls", ".csv"))
    ):
        await message.answer(
            "❌ Неподдерживаемый формат файла\n"
            "Отправьте Excel (.xlsx) или CSV файл"
        )
        return

    await message.answer("⏳ Обработка файла...")

    try:
        # Скачиваем файл
        file = await message.bot.download(document)
        file_content = file.read()

        # Парсим файл
        if document.file_name.endswith(".csv"):
            result = ExcelParser.parse_csv(file_content)
        else:
            result = ExcelParser.parse_excel(file_content)

        if not result.products and result.errors:
            # Только ошибки, нет товаров
            error_text = "❌ <b>Ошибки в файле:</b>\n\n"
            for error in result.errors[:10]:
                error_text += f"Строка {error.row_number}, {error.field}: {error.error}\n"

            if len(result.errors) > 10:
                error_text += f"\n... и ещё {len(result.errors) - 10} ошибок"

            await message.answer(error_text, parse_mode="HTML")
            await state.clear()
            return

        # Получаем категории
        category_repo = CategoryRepository(session)
        categories = await category_repo.get_all()
        category_map = {cat.name.lower(): cat for cat in categories}

        # Добавляем товары
        product_service = ProductService(session)

        added_count = 0
        failed_count = 0
        errors_list = []

        status_msg = await message.answer(
            f"⏳ Добавление товаров: 0/{len(result.products)}"
        )

        for idx, product_row in enumerate(result.products, 1):
            try:
                # Ищем категорию
                category = category_map.get(product_row.category_name.lower())
                if not category:
                    errors_list.append(
                        f"Строка {product_row.row_number}: категория '{product_row.category_name}' не найдена"
                    )
                    failed_count += 1
                    continue

                # Создаём товар
                await product_service.add_product(
                    name=product_row.name,
                    price=product_row.price,
                    category_id=category.id,
                    sizes=product_row.sizes,
                    description=product_row.description,
                    photo_file_id=None,  # TODO: загрузить фото по URL
                )

                added_count += 1

                # Обновляем статус каждые 5 товаров
                if idx % 5 == 0:
                    await status_msg.edit_text(
                        f"⏳ Добавление товаров: {idx}/{len(result.products)}"
                    )

            except Exception as e:
                logger.error(f"Failed to add product from row {product_row.row_number}: {e}")
                errors_list.append(
                    f"Строка {product_row.row_number}: {str(e)}"
                )
                failed_count += 1

        # Итоговый отчет
        report = (
            f"✅ <b>Загрузка завершена</b>\n\n"
            f"✅ Добавлено: {added_count}\n"
            f"❌ Ошибок: {failed_count}\n"
        )

        if errors_list:
            report += "\n<b>Ошибки:</b>\n"
            for error in errors_list[:10]:
                report += f"• {error}\n"

            if len(errors_list) > 10:
                report += f"\n... и ещё {len(errors_list) - 10} ошибок"

        await status_msg.edit_text(report, parse_mode="HTML")
        await state.clear()

        logger.info(
            "Products uploaded from file",
            admin_id=user.id,
            added=added_count,
            failed=failed_count,
        )

    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при обработке файла:\n<code>{str(e)}</code>",
            parse_mode="HTML",
        )
        await state.clear()
