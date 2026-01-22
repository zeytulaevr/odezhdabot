-- Миграция: Обновление таблицы broadcasts для системы массовых рассылок
-- Дата: 2026-01-22
-- Описание: Добавление полей для медиа, статусов, статистики и логов

-- Добавляем новые колонки
ALTER TABLE broadcasts
ADD COLUMN IF NOT EXISTS media_type VARCHAR(20),
ADD COLUMN IF NOT EXISTS media_file_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS buttons JSONB,
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending' NOT NULL,
ADD COLUMN IF NOT EXISTS total_target INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS success_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS failed_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS error_log JSONB,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;

-- Обновляем существующие записи (если есть)
-- Устанавливаем статус "completed" для старых рассылок с sent_count > 0
UPDATE broadcasts
SET status = 'completed',
    total_target = sent_count,
    success_count = sent_count,
    completed_at = created_at
WHERE sent_count > 0 AND status IS NULL;

-- Устанавливаем статус "pending" для остальных
UPDATE broadcasts
SET status = 'pending'
WHERE status IS NULL;

-- Создаем индекс для статуса (если не существует)
CREATE INDEX IF NOT EXISTS ix_broadcasts_status ON broadcasts(status);

-- Комментарии к новым колонкам
COMMENT ON COLUMN broadcasts.media_type IS 'Тип медиа: photo, video, document';
COMMENT ON COLUMN broadcasts.media_file_id IS 'File ID медиа для Telegram API';
COMMENT ON COLUMN broadcasts.buttons IS 'Inline кнопки для сообщения';
COMMENT ON COLUMN broadcasts.status IS 'Статус: pending, in_progress, completed, failed, cancelled';
COMMENT ON COLUMN broadcasts.total_target IS 'Всего получателей по фильтрам';
COMMENT ON COLUMN broadcasts.success_count IS 'Успешно доставлено';
COMMENT ON COLUMN broadcasts.failed_count IS 'Ошибки отправки';
COMMENT ON COLUMN broadcasts.error_log IS 'Логи ошибок отправки';
COMMENT ON COLUMN broadcasts.completed_at IS 'Дата завершения рассылки';
