#!/bin/bash

# Скрипт для управления миграциями базы данных через Docker
# Использование:
#   ./docker-migrate.sh upgrade    - применить все миграции
#   ./docker-migrate.sh downgrade  - откатить последнюю миграцию
#   ./docker-migrate.sh current    - показать текущую версию БД
#   ./docker-migrate.sh history    - показать историю миграций

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Путь к docker-compose файлу
COMPOSE_FILE="docker/docker-compose.yml"

# Проверка, запущен ли Docker Compose
check_docker() {
    if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "bot.*Up"; then
        warning "Контейнер бота не запущен"
        info "Запускаем контейнеры..."
        docker compose -f "$COMPOSE_FILE" up -d
        sleep 3
    fi
}

# Проверка команды
COMMAND=${1:-help}

case $COMMAND in
    upgrade)
        info "Применяем миграции базы данных через Docker..."
        echo ""

        check_docker

        # Показываем текущую версию
        info "Текущая версия БД:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic current || warning "Не удалось получить текущую версию"
        echo ""

        # Применяем миграции
        info "Применяем все новые миграции..."
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic upgrade head

        echo ""
        success "Миграции успешно применены!"

        # Показываем новую версию
        info "Новая версия БД:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic current
        echo ""

        warning "Перезапускаем бота для применения изменений..."
        docker compose -f "$COMPOSE_FILE" restart bot
        sleep 2
        success "Бот перезапущен!"
        ;;

    downgrade)
        warning "Откат миграции через Docker..."
        echo ""

        check_docker

        # Показываем текущую версию
        info "Текущая версия БД:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic current
        echo ""

        # Подтверждение
        read -p "Вы уверены, что хотите откатить последнюю миграцию? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            info "Отмена операции"
            exit 0
        fi

        # Откатываем одну миграцию
        info "Откатываем последнюю миграцию..."
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic downgrade -1

        echo ""
        success "Миграция откачена!"

        # Показываем новую версию
        info "Текущая версия БД:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic current
        echo ""

        warning "Перезапускаем бота..."
        docker compose -f "$COMPOSE_FILE" restart bot
        sleep 2
        success "Бот перезапущен!"
        ;;

    current)
        check_docker
        info "Текущая версия базы данных:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic current
        ;;

    history)
        check_docker
        info "История миграций:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic history --verbose
        ;;

    status)
        check_docker
        info "Статус миграций:"
        echo ""

        info "Текущая версия:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic current

        echo ""
        info "Последние миграции:"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic history -n 5
        ;;

    create)
        if [ -z "$2" ]; then
            error "Укажите описание миграции!"
            echo "Использование: ./docker-migrate.sh create \"описание миграции\""
            exit 1
        fi

        check_docker

        info "Создаем новую миграцию: $2"
        docker compose -f "$COMPOSE_FILE" exec bot python -m alembic revision --autogenerate -m "$2"

        success "Миграция создана!"
        warning "Проверьте созданный файл в migrations/versions/ перед применением!"
        ;;

    help|*)
        echo "Управление миграциями базы данных через Docker"
        echo ""
        echo "Использование: ./docker-migrate.sh КОМАНДА"
        echo ""
        echo "Доступные команды:"
        echo "  upgrade     - Применить все новые миграции"
        echo "  downgrade   - Откатить последнюю миграцию"
        echo "  current     - Показать текущую версию БД"
        echo "  history     - Показать историю всех миграций"
        echo "  status      - Показать статус миграций"
        echo "  create \"msg\" - Создать новую миграцию (с автогенерацией)"
        echo "  help        - Показать эту справку"
        echo ""
        echo "Примеры:"
        echo "  ./docker-migrate.sh upgrade"
        echo "  ./docker-migrate.sh current"
        echo "  ./docker-migrate.sh create \"add user avatar field\""
        echo ""
        info "Этот скрипт работает с контейнерами Docker"
        info "Для локальной работы используйте ./migrate.sh"
        ;;
esac
