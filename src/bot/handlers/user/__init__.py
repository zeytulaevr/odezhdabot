"""Хендлеры для пользователей."""

from aiogram import Router

from src.bot.handlers.user import bonuses, cart, catalog, my_orders, order_chat, order_dialog, start

# Главный роутер для пользователей
router = Router(name="user")

# Подключаем суб-роутеры в порядке приоритета
router.include_router(start.router)  # /start (включая deep link)
router.include_router(order_chat.router)  # Чат с админом по заказу (ПЕРВЫЙ для reply)
router.include_router(bonuses.router)  # Бонусная система (FSM handler first)
router.include_router(cart.router)  # Корзина покупок
router.include_router(order_dialog.router)  # FSM диалог заказа
router.include_router(catalog.router)  # Каталог товаров
router.include_router(my_orders.router)  # Мои заказы

__all__ = ["router"]
