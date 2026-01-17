-- Инициализация базы данных для Telegram бота

-- Установка кодировки и локали
SET client_encoding = 'UTF8';

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Для поиска по подстрокам

-- Комментарий к базе данных
COMMENT ON DATABASE telegram_bot IS 'База данных для Telegram бота магазина одежды';

-- Базовые настройки
ALTER DATABASE telegram_bot SET timezone TO 'Europe/Moscow';
