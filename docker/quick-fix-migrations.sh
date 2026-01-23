#!/bin/bash
# Быстрое применение миграций для исправления ошибки

echo "Применяем миграции..."
echo ""

echo "1. Миграция broadcasts..."
docker compose exec -T postgres psql -U botuser -d telegram_bot << 'EOF'
-- Миграция: Обновление таблицы broadcasts
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

UPDATE broadcasts
SET status = 'completed',
    total_target = sent_count,
    success_count = sent_count,
    completed_at = created_at
WHERE sent_count > 0 AND status IS NULL;

UPDATE broadcasts SET status = 'pending' WHERE status IS NULL;

CREATE INDEX IF NOT EXISTS ix_broadcasts_status ON broadcasts(status);
EOF

echo "✓ Миграция broadcasts применена"
echo ""

echo "2. Миграция users (last_active_at)..."
docker compose exec -T postgres psql -U botuser -d telegram_bot << 'EOF'
-- Миграция: Добавление last_active_at в users
ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

UPDATE users
SET last_active_at = created_at
WHERE last_active_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_users_last_active_at ON users(last_active_at);
EOF

echo "✓ Миграция users применена"
echo ""

echo "Все миграции применены успешно!"
echo ""
echo "Перезапустите бота: docker compose restart bot"
