# Инструкция по применению миграции 007

## Проблема
В базе данных отсутствуют новые поля для медиа (welcome_message_media, help_message_media, large_order_message_media).

## Решение

### Вариант 1: Через docker-compose (рекомендуется)

```bash
# Войти в контейнер бота
docker-compose exec telegram-bot bash

# Запустить миграцию
./migrate.sh upgrade

# Выйти из контейнера
exit
```

### Вариант 2: Через docker exec

```bash
docker exec -it telegram-bot ./migrate.sh upgrade
```

### Вариант 3: Прямое подключение к PostgreSQL

Если Docker недоступен, выполните SQL скрипт напрямую в PostgreSQL:

```bash
# Подключитесь к PostgreSQL
psql -U your_db_user -d your_db_name

# Или используйте pgAdmin, DBeaver и т.д.
```

Затем выполните SQL из файла `add_media_fields.sql`:

```sql
-- Add welcome_message_media column
ALTER TABLE bot_settings
ADD COLUMN IF NOT EXISTS welcome_message_media VARCHAR(200) NULL;

COMMENT ON COLUMN bot_settings.welcome_message_media IS 'File ID медиа для приветственного сообщения';

-- Add help_message_media column
ALTER TABLE bot_settings
ADD COLUMN IF NOT EXISTS help_message_media VARCHAR(200) NULL;

COMMENT ON COLUMN bot_settings.help_message_media IS 'File ID медиа для сообщения помощи';

-- Add large_order_message_media column
ALTER TABLE bot_settings
ADD COLUMN IF NOT EXISTS large_order_message_media VARCHAR(200) NULL;

COMMENT ON COLUMN bot_settings.large_order_message_media IS 'File ID медиа для сообщения о большом заказе';
```

### Вариант 4: Через Docker CLI (если контейнер называется по-другому)

```bash
# Найдите имя контейнера
docker ps | grep telegram-bot

# Выполните команду с правильным именем
docker exec -it <container_name> ./migrate.sh upgrade
```

## Проверка

После применения миграции проверьте, что поля добавлены:

```sql
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'bot_settings'
AND column_name LIKE '%_media';
```

Должно вернуть 3 строки:
- welcome_message_media
- help_message_media
- large_order_message_media

## Перезапуск бота

После применения миграции перезапустите бота:

```bash
docker-compose restart telegram-bot
```

Или:

```bash
docker restart telegram-bot
```
