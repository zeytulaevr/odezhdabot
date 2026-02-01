"""Сервис для управления товарами."""

from decimal import Decimal
from typing import Any

from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.database.models.category import Category
from src.database.models.product import Product
from src.database.repositories.category import CategoryRepository
from src.database.repositories.product import ProductRepository

logger = get_logger(__name__)


class ProductService:
    """Сервис для управления товарами."""

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия
        """
        self.session = session
        self.product_repo = ProductRepository(session)
        self.category_repo = CategoryRepository(session)

    async def add_product(
        self,
        name: str,
        price: Decimal | float,
        category_id: int,
        sizes: list[str],
        description: str | None = None,
        photo_file_id: str | None = None,
        colors: list[str] | None = None,
        fit: str | None = None,
        media: list[dict[str, Any]] | None = None,
        is_active: bool = True,
    ) -> Product:
        """Добавить новый товар.

        Args:
            name: Название товара
            price: Цена
            category_id: ID категории
            sizes: Список размеров
            description: Описание
            photo_file_id: Telegram file_id фото (deprecated, используйте media)
            colors: Список доступных цветов
            fit: Тип кроя
            media: Медиа файлы (до 10 фото/видео)
            is_active: Активен ли товар

        Returns:
            Созданный товар

        Raises:
            ValueError: Если категория не найдена
        """
        # Проверяем существование категории
        category = await self.category_repo.get(category_id)
        if not category:
            raise ValueError(f"Категория с ID {category_id} не найдена")

        # Конвертируем цену в Decimal
        if isinstance(price, float):
            price = Decimal(str(price))

        logger.info(
            "Creating product",
            name=name,
            price=str(price),
            category_id=category_id,
            colors_count=len(colors) if colors else 0,
            media_count=len(media) if media else 0,
        )

        product = await self.product_repo.create(
            name=name,
            price=price,
            category_id=category_id,
            sizes=sizes,
            description=description,
            photo_file_id=photo_file_id,
            colors=colors or [],
            fit=fit,
            media=media or [],
            is_active=is_active,
        )

        await self.session.commit()
        await self.session.refresh(product)

        logger.info("Product created", product_id=product.id)
        return product

    async def update_product(
        self, product_id: int, **kwargs: Any
    ) -> Product | None:
        """Обновить товар.

        Args:
            product_id: ID товара
            **kwargs: Поля для обновления

        Returns:
            Обновлённый товар или None
        """
        # Конвертируем цену если есть
        if "price" in kwargs and isinstance(kwargs["price"], float):
            kwargs["price"] = Decimal(str(kwargs["price"]))

        logger.info("Updating product", product_id=product_id, fields=list(kwargs.keys()))

        product = await self.product_repo.update(product_id, **kwargs)
        if product:
            await self.session.commit()
            await self.session.refresh(product)
            logger.info("Product updated", product_id=product_id)

        return product

    async def delete_product(self, product_id: int, soft: bool = True) -> bool:
        """Удалить товар.

        Args:
            product_id: ID товара
            soft: Мягкое удаление (деактивация)

        Returns:
            True если удалён
        """
        logger.info("Deleting product", product_id=product_id, soft=soft)

        if soft:
            # Мягкое удаление - просто деактивируем
            product = await self.update_product(product_id, is_active=False)
            return product is not None
        else:
            # Жёсткое удаление
            success = await self.product_repo.delete(product_id)
            if success:
                await self.session.commit()
            return success

    async def get_products(
        self,
        category_id: int | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Product]:
        """Получить список товаров с фильтрами.

        Args:
            category_id: Фильтр по категории
            is_active: Фильтр по активности
            skip: Сколько пропустить
            limit: Максимум товаров

        Returns:
            Список товаров
        """
        if category_id:
            products = await self.product_repo.get_by_category(
                category_id, is_active=is_active, skip=skip, limit=limit
            )
        elif is_active is not None:
            products = await self.product_repo.get_active() if is_active else []
        else:
            products = await self.product_repo.get_all(skip=skip, limit=limit)

        return products

    async def get_product(self, product_id: int) -> Product | None:
        """Получить товар по ID.

        Args:
            product_id: ID товара

        Returns:
            Товар или None
        """
        return await self.product_repo.get(product_id)

    async def publish_to_channel(
        self, product_id: int, bot: Bot, channel_id: int
    ) -> int | None:
        """Опубликовать товар в канал Telegram с кнопкой заказа.

        Args:
            product_id: ID товара
            bot: Экземпляр бота
            channel_id: ID канала

        Returns:
            ID опубликованного сообщения или None

        Raises:
            ValueError: Если товар не найден или нет медиа
        """
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from src.database.models.bot_settings import BotSettings

        product = await self.get_product(product_id)
        if not product:
            raise ValueError(f"Товар с ID {product_id} не найден")

        # Проверяем наличие медиа (новый способ) или фото (старый способ)
        has_media = product.has_media or product.photo_file_id
        if not has_media:
            raise ValueError(f"У товара {product_id} нет медиа")

        # Получаем настройки бота для контакта
        settings = await BotSettings.get_settings(self.session)

        # Формируем текст поста
        text = await self._format_product_post(product, settings)

        # Определяем thread_id из категории
        thread_id = product.category.thread_id if product.category else None

        # Создаем кнопку с deep link для заказа
        bot_info = await bot.get_me()
        deep_link = f"https://t.me/{bot_info.username}?start=order_{product_id}"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Заказать",
                        url=deep_link
                    )
                ]
            ]
        )

        logger.info(
            "Publishing product to channel",
            product_id=product_id,
            channel_id=channel_id,
            thread_id=thread_id,
            media_count=len(product.media_list),
        )

        try:
            # Если есть медиа в новом формате
            if product.has_media:
                media_list = product.media_list

                # Если только одно медиа - отправляем как одиночное сообщение
                if len(media_list) == 1:
                    media_item = media_list[0]
                    if media_item["type"] == "photo":
                        message = await bot.send_photo(
                            chat_id=channel_id,
                            photo=media_item["file_id"],
                            caption=text,
                            parse_mode="HTML",
                            message_thread_id=thread_id,
                            reply_markup=keyboard,
                        )
                    else:  # video
                        message = await bot.send_video(
                            chat_id=channel_id,
                            video=media_item["file_id"],
                            caption=text,
                            parse_mode="HTML",
                            message_thread_id=thread_id,
                            reply_markup=keyboard,
                        )
                else:
                    # Несколько медиа - отправляем как media group
                    media_group = []
                    for i, media_item in enumerate(media_list):
                        # Только первое медиа содержит текст
                        caption = text if i == 0 else None
                        parse_mode = "HTML" if i == 0 else None

                        if media_item["type"] == "photo":
                            media_group.append(
                                InputMediaPhoto(
                                    media=media_item["file_id"],
                                    caption=caption,
                                    parse_mode=parse_mode,
                                )
                            )
                        else:  # video
                            media_group.append(
                                InputMediaVideo(
                                    media=media_item["file_id"],
                                    caption=caption,
                                    parse_mode=parse_mode,
                                )
                            )

                    # Отправляем media group
                    messages = await bot.send_media_group(
                        chat_id=channel_id,
                        media=media_group,
                        message_thread_id=thread_id,
                    )

                    # Отправляем кнопку отдельным сообщением
                    button_message = await bot.send_message(
                        chat_id=channel_id,
                        text="👇",
                        message_thread_id=thread_id,
                        reply_markup=keyboard,
                    )

                    message = messages[0]  # Возвращаем первое сообщение из группы
            else:
                # Старый способ - только photo_file_id
                message = await bot.send_photo(
                    chat_id=channel_id,
                    photo=product.photo_file_id,
                    caption=text,
                    parse_mode="HTML",
                    message_thread_id=thread_id,
                    reply_markup=keyboard,
                )

            logger.info(
                "Product published to channel",
                product_id=product_id,
                message_id=message.message_id,
            )

            return message.message_id

        except Exception as e:
            logger.error(
                "Failed to publish product",
                product_id=product_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def _format_product_post(self, product: Product, settings) -> str:
        """Форматировать пост товара для канала.

        Args:
            product: Товар
            settings: Настройки бота (BotSettings)

        Returns:
            Отформатированный текст
        """
        # Заголовок с названием
        text = f"✨ <b>{product.name}</b> ✨\n\n"

        # Красивый разделитель
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Описание (если есть)
        if product.description:
            text += f"{product.description}\n\n"

        # Цена - выделяем ярко
        text += f"💰 <b>Цена: {product.formatted_price}</b>\n\n"

        # Размеры
        if product.sizes_list:
            sizes_formatted = ", ".join([f"<b>{s.upper()}</b>" for s in product.sizes_list])
            text += f"📏 <b>Размеры:</b> {sizes_formatted}"
            # Добавляем тип кроя если есть
            if product.fit:
                text += f" <i>({product.fit})</i>"
            text += "\n"

        # Цвета
        if product.colors_list:
            colors_formatted = ", ".join([f"<i>{c}</i>" for c in product.colors_list])
            text += f"🎨 <b>Цвета:</b> {colors_formatted}\n"

        text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"

        # Призыв к действию с контактом из настроек
        contact = settings.alternative_contact_username if settings and settings.alternative_contact_username else "@username"
        # Убираем @ если он уже есть
        if contact and not contact.startswith("@"):
            contact = f"@{contact}"

        text += f"🛒 <b>Оформить заказ:</b>\n"
        text += f"• Напишите {contact}\n"
        text += f"• Или нажмите кнопку ниже 👇"

        return text

    async def activate_product(self, product_id: int) -> Product | None:
        """Активировать товар.

        Args:
            product_id: ID товара

        Returns:
            Обновлённый товар или None
        """
        return await self.update_product(product_id, is_active=True)

    async def deactivate_product(self, product_id: int) -> Product | None:
        """Деактивировать товар.

        Args:
            product_id: ID товара

        Returns:
            Обновлённый товар или None
        """
        return await self.update_product(product_id, is_active=False)

    async def get_products_count(
        self, category_id: int | None = None, is_active: bool | None = None
    ) -> int:
        """Получить количество товаров.

        Args:
            category_id: Фильтр по категории
            is_active: Фильтр по активности

        Returns:
            Количество товаров
        """
        products = await self.get_products(
            category_id=category_id, is_active=is_active, limit=10000
        )
        return len(products)
