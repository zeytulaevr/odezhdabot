# Миграции базы данных

Этот каталог содержит SQL миграции для обновления схемы базы данных.

## Список миграций

1. **001_update_broadcasts_table.sql** - Обновление таблицы broadcasts для системы массовых рассылок
2. **002_add_last_active_at_to_users.sql** - Добавление поля last_active_at в таблицу users

## Применение миграций

### Вариант 1: Через docker compose (рекомендуется)

Из директории `docker/`:

```bash
# Применить конкретную миграцию
docker compose exec postgres psql -U botuser -d telegram_bot -f /tmp/migration.sql

# Но файлы миграций находятся вне контейнера, поэтому используем cat + stdin:
cat ../migrations/001_update_broadcasts_table.sql | docker compose exec -T postgres psql -U botuser -d telegram_bot
cat ../migrations/002_add_last_active_at_to_users.sql | docker compose exec -T postgres psql -U botuser -d telegram_bot
```

### Вариант 2: Применить все миграции сразу

Создайте bash скрипт в `docker/`:

```bash
#!/bin/bash
# apply-migrations.sh

for migration in ../migrations/*.sql; do
    echo "Применяем миграцию: $migration"
    cat "$migration" | docker compose exec -T postgres psql -U botuser -d telegram_bot
    if [ $? -eq 0 ]; then
        echo "✓ Миграция $migration применена успешно"
    else
        echo "✗ Ошибка при применении миграции $migration"
        exit 1
    fi
done

echo "Все миграции применены успешно!"
```

Сделайте скрипт исполняемым и запустите:

```bash
chmod +x apply-migrations.sh
./apply-migrations.sh
```

### Вариант 3: Напрямую через psql (если PostgreSQL доступен локально)

```bash
psql -h localhost -p 5432 -U botuser -d telegram_bot -f migrations/001_update_broadcasts_table.sql
psql -h localhost -p 5432 -U botuser -d telegram_bot -f migrations/002_add_last_active_at_to_users.sql
```

### Вариант 4: Через Adminer (веб-интерфейс)

1. Запустите Adminer:
   ```bash
   cd docker/
   docker compose --profile dev up -d adminer
   ```

2. Откройте в браузере: http://localhost:8080

3. Войдите с учетными данными:
   - Система: PostgreSQL
   - Сервер: postgres
   - Пользователь: botuser
   - Пароль: changeme (или ваш из .env)
   - База данных: telegram_bot

4. SQL команда → Скопируйте содержимое миграции → Выполнить

## Проверка применения миграций

После применения миграций проверьте структуру таблиц:

```bash
# Проверка таблицы broadcasts
cat <<'EOF' | docker compose exec -T postgres psql -U botuser -d telegram_bot
\d broadcasts
EOF

# Проверка таблицы users
cat <<'EOF' | docker compose exec -T postgres psql -U botuser -d telegram_bot
\d users
EOF
```

## Откат миграций (если нужно)

### Откат 001_update_broadcasts_table.sql

```sql
ALTER TABLE broadcasts
DROP COLUMN IF EXISTS media_type,
DROP COLUMN IF EXISTS media_file_id,
DROP COLUMN IF EXISTS buttons,
DROP COLUMN IF EXISTS status,
DROP COLUMN IF EXISTS total_target,
DROP COLUMN IF EXISTS success_count,
DROP COLUMN IF EXISTS failed_count,
DROP COLUMN IF EXISTS error_log,
DROP COLUMN IF EXISTS completed_at;

DROP INDEX IF EXISTS ix_broadcasts_status;
```

### Откат 002_add_last_active_at_to_users.sql

```sql
DROP INDEX IF EXISTS ix_users_last_active_at;
ALTER TABLE users DROP COLUMN IF EXISTS last_active_at;
```

## Переменные окружения

По умолчанию используются:
- **POSTGRES_DB**: telegram_bot
- **POSTGRES_USER**: botuser
- **POSTGRES_PASSWORD**: changeme

Если вы изменили эти значения в `.env`, используйте свои значения в командах выше.

## Автоматическое применение при разработке

В development режиме (`ENVIRONMENT=development`) таблицы создаются автоматически при запуске бота через `Base.metadata.create_all()`.

Однако миграции все равно **рекомендуется применять вручную** для:
- Добавления новых колонок к существующим таблицам
- Изменения типов данных
- Добавления индексов
- Обновления существующих данных

## Production

⚠️ **В production окружении:**
1. Всегда делайте резервную копию БД перед миграцией
2. Тестируйте миграции на staging окружении
3. Применяйте миграции во время maintenance window
4. Проверяйте логи после применения

```bash
# Создать бэкап
docker compose exec postgres pg_dump -U botuser telegram_bot > backup_$(date +%Y%m%d_%H%M%S).sql

# Применить миграции
cat migrations/001_update_broadcasts_table.sql | docker compose exec -T postgres psql -U botuser -d telegram_bot
cat migrations/002_add_last_active_at_to_users.sql | docker compose exec -T postgres psql -U botuser -d telegram_bot

# Проверить состояние
docker compose logs bot
```
