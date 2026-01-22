-- Миграция: Добавление поля last_active_at в таблицу users
-- Дата: 2026-01-22
-- Описание: Добавление поля для отслеживания последней активности пользователей

-- Добавляем колонку last_active_at
ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Обновляем существующие записи - устанавливаем last_active_at = created_at
UPDATE users
SET last_active_at = created_at
WHERE last_active_at IS NULL;

-- Создаем индекс для быстрого поиска активных пользователей
CREATE INDEX IF NOT EXISTS ix_users_last_active_at ON users(last_active_at);

-- Комментарий к колонке
COMMENT ON COLUMN users.last_active_at IS 'Дата последней активности пользователя';
