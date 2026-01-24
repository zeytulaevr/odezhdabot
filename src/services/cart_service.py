"""Сервис для работы с корзиной покупок."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.cart import Cart, CartItem

logger = get_logger(__name__)


class CartService:
    """Сервис для управления корзиной покупок."""

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия
        """
        self.session = session

    async def get_or_create_cart(self, user_id: int) -> Cart:
        """Получить или создать корзину для пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Корзина пользователя
        """
        # Проверяем существующую корзину
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()

        if cart:
            return cart

        # Создаем новую корзину
        cart = Cart(user_id=user_id)
        self.session.add(cart)
        await self.session.flush()
        await self.session.refresh(cart)

        logger.info("Cart created", user_id=user_id, cart_id=cart.id)
        return cart

    async def add_item(
        self,
        user_id: int,
        product_id: int,
        size: str,
        quantity: int = 1,
        color: str | None = None,
    ) -> CartItem:
        """Добавить товар в корзину или обновить количество.

        Args:
            user_id: ID пользователя
            product_id: ID товара
            size: Размер товара
            quantity: Количество
            color: Цвет товара (опционально)

        Returns:
            Товар в корзине
        """
        cart = await self.get_or_create_cart(user_id)

        # Проверяем, есть ли уже такой товар в корзине
        result = await self.session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
                CartItem.size == size,
                CartItem.color == color if color else CartItem.color.is_(None),
            )
        )
        existing_item = result.scalar_one_or_none()

        if existing_item:
            # Обновляем количество
            existing_item.quantity += quantity
            await self.session.flush()
            await self.session.refresh(existing_item)
            logger.info(
                "Cart item quantity updated",
                user_id=user_id,
                cart_item_id=existing_item.id,
                new_quantity=existing_item.quantity,
            )
            return existing_item

        # Создаем новую позицию
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product_id,
            size=size,
            color=color,
            quantity=quantity,
        )
        self.session.add(cart_item)
        await self.session.flush()
        await self.session.refresh(cart_item)

        logger.info(
            "Cart item added",
            user_id=user_id,
            cart_item_id=cart_item.id,
            product_id=product_id,
            quantity=quantity,
        )
        return cart_item

    async def remove_item(self, user_id: int, cart_item_id: int) -> bool:
        """Удалить товар из корзины.

        Args:
            user_id: ID пользователя
            cart_item_id: ID товара в корзине

        Returns:
            True если удалено успешно
        """
        cart = await self.get_or_create_cart(user_id)

        result = await self.session.execute(
            select(CartItem).where(
                CartItem.id == cart_item_id,
                CartItem.cart_id == cart.id,
            )
        )
        cart_item = result.scalar_one_or_none()

        if not cart_item:
            return False

        await self.session.delete(cart_item)
        await self.session.flush()

        logger.info(
            "Cart item removed",
            user_id=user_id,
            cart_item_id=cart_item_id,
        )
        return True

    async def update_quantity(
        self, user_id: int, cart_item_id: int, quantity: int
    ) -> CartItem | None:
        """Обновить количество товара в корзине.

        Args:
            user_id: ID пользователя
            cart_item_id: ID товара в корзине
            quantity: Новое количество

        Returns:
            Обновленный товар или None
        """
        if quantity < 1:
            # Если количество меньше 1, удаляем товар
            await self.remove_item(user_id, cart_item_id)
            return None

        cart = await self.get_or_create_cart(user_id)

        result = await self.session.execute(
            select(CartItem).where(
                CartItem.id == cart_item_id,
                CartItem.cart_id == cart.id,
            )
        )
        cart_item = result.scalar_one_or_none()

        if not cart_item:
            return None

        cart_item.quantity = quantity
        await self.session.flush()
        await self.session.refresh(cart_item)

        logger.info(
            "Cart item quantity updated",
            user_id=user_id,
            cart_item_id=cart_item_id,
            new_quantity=quantity,
        )
        return cart_item

    async def clear_cart(self, user_id: int) -> bool:
        """Очистить корзину пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            True если очищено успешно
        """
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()

        if not cart:
            return False

        # Удаляем все товары из корзины
        for item in cart.items:
            await self.session.delete(item)

        await self.session.flush()

        logger.info("Cart cleared", user_id=user_id, cart_id=cart.id)
        return True

    async def get_cart(self, user_id: int) -> Cart | None:
        """Получить корзину пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Корзина или None
        """
        result = await self.session.execute(
            select(Cart).where(Cart.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_cart_items(self, user_id: int) -> list[CartItem]:
        """Получить все товары из корзины пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список товаров в корзине
        """
        cart = await self.get_cart(user_id)
        if not cart:
            return []
        return cart.items

    async def get_cart_total_items(self, user_id: int) -> int:
        """Получить общее количество товаров в корзине.

        Args:
            user_id: ID пользователя

        Returns:
            Общее количество товаров
        """
        cart = await self.get_cart(user_id)
        if not cart:
            return 0
        return cart.total_items
