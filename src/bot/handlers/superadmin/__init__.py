"""Хендлеры для супер-администратора."""

from aiogram import Router

from src.bot.handlers.superadmin import categories, menu, spam_settings
from src.bot.handlers.superadmin.products import router as products_router

# Главный роутер для супер-админов
router = Router(name="superadmin")

# Подключаем суб-роутеры
router.include_router(menu.router)
router.include_router(spam_settings.router)
router.include_router(products_router)
router.include_router(categories.router)

__all__ = ["router"]
