#!/bin/bash

# Скрипт для управления миграциями базы данных через Alembic
# Использование:
#   ./migrate.sh upgrade    - применить все миграции
#   ./migrate.sh downgrade  - откатить последнюю миграцию
#   ./migrate.sh current    - показать текущую версию БД
#   ./migrate.sh history    - показать историю миграций
#   ./migrate.sh create "description" - создать новую миграцию

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

# Проверка наличия .env файла
if [ ! -f .env ]; then
    error ".env файл не найден!"
    exit 1
fi

# Загрузка переменных окружения
export $(cat .env | grep -v '^#' | xargs)

# Проверка команды
COMMAND=${1:-help}

case $COMMAND in
    upgrade)
        info "Применяем миграции базы данных..."
        echo ""

        # Показываем текущую версию
        info "Текущая версия БД:"
        python -m alembic current || warning "Не удалось получить текущую версию"
        echo ""

        # Применяем миграции
        info "Применяем все новые миграции..."
        python -m alembic upgrade head

        echo ""
        success "Миграции успешно применены!"

        # Показываем новую версию
        info "Новая версия БД:"
        python -m alembic current
        echo ""

        warning "Не забудьте перезапустить бота: docker compose restart bot"
        ;;

    downgrade)
        warning "Откат миграции..."
        echo ""

        # Показываем текущую версию
        info "Текущая версия БД:"
        python -m alembic current
        echo ""

        # Подтверждение
        read -p "Вы уверены, что хотите откатить последнюю миграцию? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            info "Отмена операции"
            exit 0
        fi

        # Откатываем одну миграцию
        info "Откатываем последнюю миграцию..."
        python -m alembic downgrade -1

        echo ""
        success "Миграция откачена!"

        # Показываем новую версию
        info "Текущая версия БД:"
        python -m alembic current
        echo ""

        warning "Не забудьте перезапустить бота: docker compose restart bot"
        ;;

    current)
        info "Текущая версия базы данных:"
        python -m alembic current
        ;;

    history)
        info "История миграций:"
        python -m alembic history --verbose
        ;;

    create)
        if [ -z "$2" ]; then
            error "Укажите описание миграции!"
            echo "Использование: ./migrate.sh create \"описание миграции\""
            exit 1
        fi

        info "Создаем новую миграцию: $2"
        python -m alembic revision --autogenerate -m "$2"

        success "Миграция создана!"
        warning "Проверьте созданный файл в migrations/versions/ перед применением!"
        ;;

    status)
        info "Статус миграций:"
        echo ""

        info "Текущая версия:"
        python -m alembic current

        echo ""
        info "Последние миграции:"
        python -m alembic history -n 5
        ;;

    help|*)
        echo "Управление миграциями базы данных"
        echo ""
        echo "Использование: ./migrate.sh КОМАНДА"
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
        echo "  ./migrate.sh upgrade"
        echo "  ./migrate.sh current"
        echo "  ./migrate.sh create \"add user avatar field\""
        ;;
esac
