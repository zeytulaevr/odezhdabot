"""Сервис для управления товарами."""

from decimal import Decimal
from typing import Any

from aiogram import Bot
from aiogram.types import InputMediaPhoto
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
        is_active: bool = True,
    ) -> Product:
        """Добавить новый товар.

        Args:
            name: Название товара
            price: Цена
            category_id: ID категории
            sizes: Список размеров
            description: Описание
            photo_file_id: Telegram file_id фото
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
        )

        product = await self.product_repo.create(
            name=name,
            price=price,
            category_id=category_id,
            sizes=sizes,
            description=description,
            photo_file_id=photo_file_id,
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
        """Опубликовать товар в канал Telegram.

        Args:
            product_id: ID товара
            bot: Экземпляр бота
            channel_id: ID канала

        Returns:
            ID опубликованного сообщения или None

        Raises:
            ValueError: Если товар не найден или нет фото
        """
        product = await self.get_product(product_id)
        if not product:
            raise ValueError(f"Товар с ID {product_id} не найден")

        if not product.photo_file_id:
            raise ValueError(f"У товара {product_id} нет фото")

        # Формируем текст поста
        text = self._format_product_post(product)

        # Определяем thread_id из категории
        thread_id = product.category.thread_id if product.category else None

        logger.info(
            "Publishing product to channel",
            product_id=product_id,
            channel_id=channel_id,
            thread_id=thread_id,
        )

        try:
            # Отправляем фото с текстом
            message = await bot.send_photo(
                chat_id=channel_id,
                photo=product.photo_file_id,
                caption=text,
                parse_mode="HTML",
                message_thread_id=thread_id,
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

    def _format_product_post(self, product: Product) -> str:
        """Форматировать пост товара для канала.

        Args:
            product: Товар

        Returns:
            Отформатированный текст
        """
        # Название и цена
        text = f"<b>{product.name}</b>\n"
        text += f"💰 Цена: <b>{product.formatted_price}</b>\n\n"

        # Описание
        if product.description:
            text += f"{product.description}\n\n"

        # Размеры
        if product.sizes_list:
            text += f"📏 Размеры: {', '.join(product.sizes_list)}\n\n"

        # Призыв к действию
        text += "🛒 Для заказа напишите @username или нажмите кнопку ниже"

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
