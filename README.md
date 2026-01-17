# Telegram Shop Bot

Telegram бот для магазина одежды на aiogram 3.x с PostgreSQL.

## Технологический стек

- **Python 3.11+**
- **aiogram 3.x** - фреймворк для Telegram ботов
- **PostgreSQL** - основная база данных
- **asyncpg** - асинхронный драйвер для PostgreSQL
- **SQLAlchemy 2.0** - ORM для работы с БД
- **Redis** - хранилище состояний FSM и кэширование
- **Pydantic** - валидация данных и настроек
- **structlog** - структурированное логирование
- **Alembic** - миграции базы данных
- **Docker & Docker Compose** - контейнеризация

## Структура проекта

```
telegram-shop-bot/
├── src/
│   ├── bot/              # Логика бота
│   │   ├── handlers/     # Обработчики команд и сообщений
│   │   ├── middlewares/  # Промежуточные обработчики
│   │   ├── filters/      # Фильтры для обработчиков
│   │   └── keyboards/    # Клавиатуры (reply и inline)
│   ├── database/         # Работа с базой данных
│   │   ├── models/       # SQLAlchemy модели
│   │   └── repositories/ # Репозитории для работы с моделями
│   ├── services/         # Бизнес-логика
│   ├── core/             # Конфигурация и константы
│   │   ├── config.py     # Настройки приложения
│   │   ├── constants.py  # Константы, enum'ы, сообщения
│   │   └── logging.py    # Настройка логирования
│   ├── utils/            # Вспомогательные утилиты
│   └── main.py           # Точка входа
├── migrations/           # Alembic миграции
├── tests/                # Тесты
├── docker/               # Docker конфигурация
│   ├── Dockerfile
│   └── docker-compose.yml
├── logs/                 # Логи приложения
├── .env                  # Переменные окружения (создать из .env.example)
├── .env.example          # Пример переменных окружения
├── pyproject.toml        # Poetry зависимости и настройки
├── alembic.ini           # Настройки Alembic
└── README.md             # Этот файл
```

## Быстрый старт

### Предварительные требования

- Python 3.11+
- Poetry (для управления зависимостями)
- Docker и Docker Compose (опционально)
- PostgreSQL 14+ (если запускаете без Docker)
- Redis 7+ (если запускаете без Docker)

### Установка с Docker (рекомендуется)

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd telegram-shop-bot
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` и установите необходимые переменные:
```bash
nano .env  # или любой другой редактор
```

Обязательно установите:
- `BOT_TOKEN` - токен от @BotFather
- `ADMIN_IDS` - ID администраторов (через запятую)
- Пароли для PostgreSQL и Redis

4. Запустите проект с помощью Docker Compose:
```bash
cd docker
docker-compose up -d
```

5. Проверьте логи:
```bash
docker-compose logs -f bot
```

### Установка без Docker

1. Установите Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Установите зависимости:
```bash
poetry install
```

3. Создайте и настройте `.env` файл (см. выше)

4. Убедитесь, что PostgreSQL и Redis запущены

5. Создайте базу данных:
```bash
createdb telegram_bot
```

6. Примените миграции:
```bash
poetry run alembic upgrade head
```

7. Запустите бота:
```bash
poetry run python -m src
```

## Управление миграциями

### Создание новой миграции

```bash
poetry run alembic revision --autogenerate -m "описание изменений"
```

### Применение миграций

```bash
poetry run alembic upgrade head
```

### Откат миграций

```bash
alembic downgrade -1  # откатить одну миграцию
alembic downgrade base  # откатить все миграции
```

## Разработка

### Установка dev-зависимостей

```bash
poetry install --with dev
```

### Запуск тестов

```bash
poetry run pytest
poetry run pytest --cov=src  # с покрытием кода
```

### Форматирование кода

```bash
poetry run black src/
poetry run isort src/
```

### Проверка типов

```bash
poetry run mypy src/
```

### Линтинг

```bash
poetry run flake8 src/
```

## Конфигурация

Все настройки находятся в файле `.env`. Основные параметры:

### Telegram Bot
- `BOT_TOKEN` - токен бота от @BotFather

### База данных
- `POSTGRES_HOST` - хост PostgreSQL
- `POSTGRES_PORT` - порт PostgreSQL (по умолчанию 5432)
- `POSTGRES_DB` - имя базы данных
- `POSTGRES_USER` - пользователь БД
- `POSTGRES_PASSWORD` - пароль БД

### Redis
- `REDIS_HOST` - хост Redis
- `REDIS_PORT` - порт Redis (по умолчанию 6379)
- `REDIS_PASSWORD` - пароль Redis

### Логирование
- `LOG_LEVEL` - уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT` - формат логов (console, json)

### Администрирование
- `ADMIN_IDS` - ID администраторов через запятую

## Docker Compose сервисы

- **bot** - Telegram бот
- **postgres** - PostgreSQL база данных
- **redis** - Redis для FSM и кэширования
- **adminer** - Web-интерфейс для управления БД (доступен на http://localhost:8080, только в dev режиме)

### Запуск с Adminer (для разработки)

```bash
docker-compose --profile dev up -d
```

## Основные команды бота

- `/start` - начало работы с ботом
- `/help` - справка по командам
- `/menu` - показать главное меню

## Архитектура

### Слои приложения

1. **Handlers** - обработка входящих сообщений и команд
2. **Middlewares** - промежуточная обработка (логирование, БД, аутентификация)
3. **Repositories** - работа с базой данных
4. **Services** - бизнес-логика
5. **Models** - модели данных

### Паттерны

- **Repository Pattern** - для работы с БД
- **Dependency Injection** - через middleware
- **FSM** (Finite State Machine) - для управления состояниями диалогов
- **Factory Pattern** - для создания клавиатур

## Производительность

- Использование connection pooling для PostgreSQL
- Redis для хранения состояний FSM
- Асинхронная архитектура (async/await)
- Оптимизированные Docker образы (multi-stage build)

## Безопасность

- Хранение секретов в `.env` файле
- Валидация данных через Pydantic
- Проверка прав доступа через фильтры
- Запуск контейнера от непривилегированного пользователя

## Мониторинг и логи

Логи сохраняются в:
- Консоль (stdout)
- Файл `logs/bot.log` (с ротацией)

Формат логов настраивается через `LOG_FORMAT`:
- `console` - цветной вывод для разработки
- `json` - структурированный JSON для продакшена

## Troubleshooting

### Бот не запускается

1. Проверьте правильность `BOT_TOKEN`
2. Убедитесь, что PostgreSQL и Redis доступны
3. Проверьте логи: `docker-compose logs bot`

### Ошибки подключения к БД

1. Проверьте, что PostgreSQL запущен
2. Проверьте параметры подключения в `.env`
3. Убедитесь, что база данных создана

### Миграции не применяются

1. Проверьте настройки в `alembic.ini`
2. Убедитесь, что база данных доступна
3. Проверьте версию миграций: `alembic current`

## Контрибьюция

1. Создайте ветку для фичи: `git checkout -b feature/amazing-feature`
2. Закоммитьте изменения: `git commit -m 'Add amazing feature'`
3. Запушьте ветку: `git push origin feature/amazing-feature`
4. Создайте Pull Request

## Лицензия

MIT License

## Контакты

При возникновении вопросов создавайте issue в репозитории.

---

**Сделано с ❤️ и Python**
