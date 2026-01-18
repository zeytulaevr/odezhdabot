"""Хендлеры для супер-администратора."""

from aiogram import Router

from src.bot.handlers.superadmin import menu, spam_settings

# Главный роутер для супер-админов
router = Router(name="superadmin")

# Подключаем суб-роутеры
router.include_router(menu.router)
router.include_router(spam_settings.router)

__all__ = ["router"]
