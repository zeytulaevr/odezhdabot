# Production Deployment Checklist

## 🔧 Конфигурация

### 1. Environment Variables (.env)

```bash
# Bot Configuration
BOT_TOKEN=your_bot_token_here
ENVIRONMENT=production

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=telegram_bot
POSTGRES_USER=botuser
POSTGRES_PASSWORD=strong_password_here

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=strong_password_here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=logs/bot.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5

# Admin IDs (comma-separated)
SUPERADMIN_IDS=123456789,987654321
ADMIN_IDS=111222333

# Channel Configuration
CHANNEL_ID=-1001234567890
CHANNEL_THREAD_ID=1

# Database Pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_ECHO=false
```

### 2. Docker Configuration

Проверьте `docker/docker-compose.yml`:

```yaml
services:
  bot:
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

## 🗄️ База данных

### 1. Применить миграции

```bash
cd docker/
./apply-migrations.sh
```

Или вручную:
```bash
cat ../migrations/001_update_broadcasts_table.sql | docker compose exec -T postgres psql -U botuser -d telegram_bot
cat ../migrations/002_add_last_active_at_to_users.sql | docker compose exec -T postgres psql -U botuser -d telegram_bot
```

### 2. Создать индексы (для production)

```sql
-- Индексы для производительности
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_active
ON users(last_active_at DESC)
WHERE is_banned = false;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created
ON orders(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_status
ON orders(user_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_broadcasts_status_created
ON broadcasts(status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_available_category
ON products(is_available, category_id)
WHERE is_available = true;
```

### 3. Backup Strategy

```bash
# Ежедневный бэкап
docker compose exec postgres pg_dump -U botuser telegram_bot | gzip > backups/backup_$(date +%Y%m%d).sql.gz

# Добавить в cron
0 2 * * * cd /path/to/odezhdabot && docker compose exec -T postgres pg_dump -U botuser telegram_bot | gzip > backups/backup_$(date +\%Y\%m\%d).sql.gz
```

## 🚀 Запуск

### 1. Проверка конфигурации

```bash
# Проверить .env
cat .env

# Проверить docker-compose.yml
cat docker/docker-compose.yml
```

### 2. Запуск сервисов

```bash
cd docker/

# Запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f bot
```

### 3. Проверка здоровья

```bash
# Проверка PostgreSQL
docker compose exec postgres pg_isready -U botuser

# Проверка Redis
docker compose exec redis redis-cli -a yourpassword ping

# Проверка бота (в логах должно быть)
# ✓ Database tables created successfully
# ✓ Bot started successfully
```

## 🔒 Безопасность

### 1. Firewall

```bash
# Разрешить только необходимые порты
ufw allow 22/tcp   # SSH
ufw deny 5432/tcp  # PostgreSQL (только из Docker network)
ufw deny 6379/tcp  # Redis (только из Docker network)
ufw enable
```

### 2. SSL/TLS для webhook (если используется)

```bash
# Получить сертификат Let's Encrypt
certbot certonly --standalone -d yourdomain.com
```

### 3. Rate Limiting

Уже реализовано в коде:
- Рассылки: 20 msg/sec
- API запросы: автоматический retry

### 4. Secrets Management

```bash
# НЕ коммитить .env в git
echo ".env" >> .gitignore

# Использовать Docker secrets в production
docker secret create bot_token ./bot_token.txt
```

## 📊 Мониторинг

### 1. Логи

```bash
# Просмотр логов в реальном времени
docker compose logs -f bot

# Поиск ошибок
docker compose logs bot | grep -i error

# Анализ JSON логов (с jq)
docker compose logs bot --no-log-prefix | jq 'select(.level == "error")'
```

### 2. Метрики

Доступ через бота:
```
/superadmin → Статистика
```

Или через API (если добавлен HTTP endpoint):
```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

### 3. Алерты

Проверьте получение алертов:
```python
# В коде бота
from src.utils.alerts import send_critical_alert

await send_critical_alert(
    bot=bot,
    message="Test alert",
    details={"test": True}
)
```

## 🔧 Обслуживание

### 1. Обновление кода

```bash
# Pull изменений
git pull origin main

# Перезапуск бота
cd docker/
docker compose restart bot

# Или полная пересборка
docker compose down
docker compose up -d --build
```

### 2. Очистка логов

```bash
# Автоматическая ротация уже настроена (5 файлов по 10MB)

# Ручная очистка старых логов
find logs/ -name "bot.log.*" -mtime +30 -delete
```

### 3. Очистка Docker

```bash
# Очистка неиспользуемых образов
docker system prune -a

# Очистка volumes (ОСТОРОЖНО!)
docker volume prune
```

## 🐛 Troubleshooting

### Бот не запускается

1. Проверить логи:
   ```bash
   docker compose logs bot
   ```

2. Проверить переменные окружения:
   ```bash
   docker compose config
   ```

3. Проверить БД:
   ```bash
   docker compose exec postgres psql -U botuser -d telegram_bot -c "SELECT 1"
   ```

### Высокая нагрузка на БД

1. Проверить медленные запросы:
   ```sql
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

2. Добавить индексы (см. раздел База данных)

3. Увеличить connection pool:
   ```python
   # В .env
   DB_POOL_SIZE=20
   DB_MAX_OVERFLOW=40
   ```

### Память заканчивается

1. Проверить использование:
   ```bash
   docker stats
   ```

2. Ограничить память в docker-compose.yml

3. Проверить утечки памяти в логах

### Рассылки не отправляются

1. Проверить статус:
   ```
   /superadmin → Рассылка → История
   ```

2. Проверить логи:
   ```bash
   docker compose logs bot | grep broadcast
   ```

3. Проверить rate limiting (20 msg/sec)

## 📈 Масштабирование

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  bot:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
```

### Database Replication

```yaml
services:
  postgres-replica:
    image: postgres:16-alpine
    environment:
      POSTGRES_PRIMARY: postgres
      POSTGRES_PRIMARY_PORT: 5432
```

### Load Balancing

```yaml
services:
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
```

## 🎯 Performance Optimization

### 1. Database Connections

```python
# В .env для высокой нагрузки
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
```

### 2. Redis Caching

```python
# Кэширование метрик (добавить в MonitoringService)
@cached(ttl=300)  # 5 минут
async def get_system_stats(self):
    # ...
```

### 3. Batch Operations

```python
# Уже реализовано в broadcast_sender.py
BATCH_SIZE = 20  # Отправка батчами
```

## ✅ Production Checklist

- [ ] `.env` настроен корректно
- [ ] `ENVIRONMENT=production`
- [ ] `LOG_FORMAT=json`
- [ ] `LOG_LEVEL=INFO` (не DEBUG)
- [ ] Все миграции применены
- [ ] Индексы созданы
- [ ] Backup стратегия настроена
- [ ] Firewall настроен
- [ ] SSL сертификаты установлены (если webhook)
- [ ] `superadmin_ids` заполнены
- [ ] Алерты протестированы
- [ ] Логи ротируются
- [ ] Docker restart policy: `unless-stopped`
- [ ] Resource limits установлены
- [ ] Monitoring настроен
- [ ] Health checks работают
- [ ] Документация обновлена

## 📞 Контакты для поддержки

- **Логи**: `docker compose logs -f bot`
- **Статус**: `/superadmin` в боте
- **Метрики**: `/superadmin → Статистика`
- **Алерты**: Telegram (автоматически super_admin)
