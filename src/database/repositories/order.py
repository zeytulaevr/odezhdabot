"""Репозиторий для работы с заказами."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import OrderStatus, PaymentStatus
from src.database.models.order import Order, OrderItem
from src.database.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Репозиторий для работы с заказами."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория заказов."""
        super().__init__(Order, session)

    async def get_user_orders(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """Получить заказы пользователя.

        Args:
            user_id: ID пользователя
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список заказов пользователя
        """
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: OrderStatus, skip: int = 0, limit: int = 100
    ) -> list[Order]:
        """Получить заказы по статусу.

        Args:
            status: Статус заказа
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            Список заказов с указанным статусом
        """
        stmt = select(Order).where(Order.status == status.value).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_order(
        self,
        user_id: int,
        items: list[dict],
        delivery_address: str,
        recipient_name: str,
        recipient_phone: str,
        comment: str | None = None,
    ) -> Order:
        """Создать новый заказ с товарами.

        Args:
            user_id: ID пользователя
            items: Список товаров [{product_id, product_name, product_price, quantity}]
            delivery_address: Адрес доставки
            recipient_name: Имя получателя
            recipient_phone: Телефон получателя
            comment: Комментарий к заказу

        Returns:
            Созданный заказ
        """
        # Расчёт общей суммы
        total_amount = Decimal("0")
        for item in items:
            total_amount += Decimal(str(item["product_price"])) * item["quantity"]

        # Создание заказа
        order = Order(
            user_id=user_id,
            total_amount=total_amount,
            delivery_address=delivery_address,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            comment=comment,
            status=OrderStatus.PENDING.value,
            payment_status=PaymentStatus.PENDING.value,
        )
        self.session.add(order)
        await self.session.flush()

        # Создание элементов заказа
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["product_id"],
                product_name=item["product_name"],
                product_price=Decimal(str(item["product_price"])),
                quantity=item["quantity"],
            )
            self.session.add(order_item)

        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def update_status(
        self, order_id: int, status: OrderStatus
    ) -> Order | None:
        """Обновить статус заказа.

        Args:
            order_id: ID заказа
            status: Новый статус

        Returns:
            Обновлённый заказ или None
        """
        return await self.update(order_id, status=status.value)

    async def update_payment_status(
        self, order_id: int, payment_status: PaymentStatus, payment_id: str | None = None
    ) -> Order | None:
        """Обновить статус оплаты заказа.

        Args:
            order_id: ID заказа
            payment_status: Новый статус оплаты
            payment_id: ID платежа в платёжной системе

        Returns:
            Обновлённый заказ или None
        """
        update_data = {"payment_status": payment_status.value}
        if payment_id:
            update_data["payment_id"] = payment_id

        return await self.update(order_id, **update_data)

    async def cancel_order(self, order_id: int) -> Order | None:
        """Отменить заказ.

        Args:
            order_id: ID заказа

        Returns:
            Обновлённый заказ или None
        """
        return await self.update(
            order_id,
            status=OrderStatus.CANCELLED.value,
            payment_status=PaymentStatus.CANCELLED.value,
        )
