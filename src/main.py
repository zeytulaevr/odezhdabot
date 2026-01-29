"""Главный модуль для запуска Telegram бота."""

import asyncio
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from src.bot.handlers import admin, common, moderation, superadmin, user
from src.bot.middlewares.auth import AuthMiddleware
from src.bot.middlewares.database import DatabaseMiddleware
from src.bot.middlewares.logging import LoggingMiddleware
from src.core.config import settings
from src.core.logging import get_logger, setup_logging
from src.database.base import close_db, init_db

# Настройка логирования
setup_logging()
logger = get_logger(__name__)


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота.

    Args:
        bot: Экземпляр бота
    """
    logger.info("Starting bot...")

    # Инициализация базы данных
    await init_db()

    # Получение информации о боте
    bot_info = await bot.get_me()
    logger.info(
        "Bot started successfully",
        bot_id=bot_info.id,
        bot_username=bot_info.username,
        bot_name=bot_info.full_name,
    )

    # Уведомление супер-администраторов о запуске
    for admin_id in settings.superadmin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🤖 Бот <b>{bot_info.full_name}</b> запущен!\n\n"
                f"Окружение: <code>{settings.environment}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.warning(f"Failed to notify superadmin {admin_id}: {e}")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота.

    Args:
        bot: Экземпляр бота
    """
    logger.info("Shutting down bot...")

    # Уведомление супер-администраторов об остановке
    for admin_id in settings.superadmin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text="🛑 Бот остановлен",
            )
        except Exception as e:
            logger.warning(f"Failed to notify superadmin {admin_id}: {e}")

    # Закрытие соединений с БД
    await close_db()

    logger.info("Bot stopped successfully")


def setup_middlewares(dp: Dispatcher) -> None:
    """Настройка middlewares.

    Args:
        dp: Диспетчер
    """
    # Middlewares применяются в порядке регистрации
    # Сначала логирование, потом база данных, затем авторизация
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AuthMiddleware())

    logger.info("Middlewares configured")


def setup_handlers(dp: Dispatcher) -> None:
    """Настройка обработчиков.

    Args:
        dp: Диспетчер
    """
    # Регистрация роутеров в порядке приоритета
    # ВАЖНО: роутеры с более строгими фильтрами должны быть первыми!

    # Сначала общие хендлеры (help, etc)
    dp.include_router(common.router)

    # Затем хендлеры с проверкой ролей (от более строгих к менее строгим)
    dp.include_router(superadmin.router)  # Самый строгий фильтр
    dp.include_router(admin.router)       # Средний фильтр

    # Модерация каналов
    dp.include_router(moderation.router)

    # В конце - пользовательские хендлеры (самый общий фильтр)
    dp.include_router(user.router)

    logger.info("Handlers configured")


async def main() -> None:
    """Основная функция запуска бота."""
    logger.info(
        "Initializing bot",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    # Создание бота
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    # Создание Redis storage для FSM
    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url)
        storage = RedisStorage(redis=redis)
        logger.info("Redis storage initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis storage: {e}. Using memory storage.")
        from aiogram.fsm.storage.memory import MemoryStorage

        storage = MemoryStorage()

    # Создание диспетчера
    dp = Dispatcher(storage=storage)

    # Настройка middlewares и handlers
    setup_middlewares(dp)
    setup_handlers(dp)

    # Регистрация startup/shutdown хуков
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        # Запуск polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,  # Пропускаем накопившиеся обновления
        )
    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical("Critical error", error=str(e), exc_info=True)
        sys.exit(1)
