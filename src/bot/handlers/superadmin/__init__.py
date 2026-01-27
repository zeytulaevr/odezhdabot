"""Хендлеры для супер-администратора."""

from aiogram import Router

from src.bot.handlers.superadmin import categories, manage_admins, menu, settings, spam_settings, stats
from src.bot.handlers.superadmin.broadcast import router as broadcast_router
from src.bot.handlers.superadmin.products import router as products_router

# Главный роутер для супер-админов
router = Router(name="superadmin")

# Подключаем суб-роутеры
# FSM обработчики первыми
router.include_router(settings.router)  # Settings FSM handlers first
router.include_router(broadcast_router)
router.include_router(manage_admins.router)
router.include_router(stats.router)
router.include_router(menu.router)
router.include_router(spam_settings.router)
router.include_router(products_router)
router.include_router(categories.router)

__all__ = ["router"]
