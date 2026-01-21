"""Общие хендлеры для всех пользователей."""

from aiogram import Router

from src.bot.handlers.common import help, navigation

# Главный роутер для общих хендлеров
router = Router(name="common")

# Подключаем суб-роутеры
router.include_router(navigation.router)  # Навигация (кнопка Назад) - приоритет
router.include_router(help.router)

__all__ = ["router"]
