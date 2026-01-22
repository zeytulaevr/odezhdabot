#!/bin/bash
# Скрипт для применения миграций базы данных
# Использование: ./apply-migrations.sh

set -e  # Остановка при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/../migrations"

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка наличия docker compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker не найден. Установите Docker и попробуйте снова.${NC}"
    exit 1
fi

# Переход в директорию docker
cd "$SCRIPT_DIR"

# Проверка, что контейнер postgres запущен
if ! docker compose ps postgres | grep -q "Up"; then
    echo -e "${RED}✗ Контейнер PostgreSQL не запущен.${NC}"
    echo "Запустите его командой: docker compose up -d postgres"
    exit 1
fi

echo -e "${YELLOW}=== Применение миграций ===${NC}"
echo

# Подсчет миграций
total_migrations=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | wc -l)

if [ "$total_migrations" -eq 0 ]; then
    echo -e "${YELLOW}Миграции не найдены в директории $MIGRATIONS_DIR${NC}"
    exit 0
fi

echo "Найдено миграций: $total_migrations"
echo

# Применение каждой миграции
success_count=0
failed_count=0

for migration in "$MIGRATIONS_DIR"/*.sql; do
    migration_name=$(basename "$migration")
    echo -e "${YELLOW}Применяем миграцию: $migration_name${NC}"

    if cat "$migration" | docker compose exec -T postgres psql -U botuser -d telegram_bot > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Миграция $migration_name применена успешно${NC}"
        ((success_count++))
    else
        echo -e "${RED}✗ Ошибка при применении миграции $migration_name${NC}"
        ((failed_count++))

        # Показываем детальную ошибку
        echo -e "${YELLOW}Детали ошибки:${NC}"
        cat "$migration" | docker compose exec -T postgres psql -U botuser -d telegram_bot

        echo
        echo -e "${YELLOW}Остановка процесса из-за ошибки${NC}"
        exit 1
    fi
    echo
done

# Итоги
echo -e "${YELLOW}=== Итоги ===${NC}"
echo -e "${GREEN}✓ Успешно: $success_count${NC}"

if [ "$failed_count" -gt 0 ]; then
    echo -e "${RED}✗ Ошибок: $failed_count${NC}"
    exit 1
else
    echo
    echo -e "${GREEN}Все миграции применены успешно!${NC}"
    echo
    echo "Перезапустите бота для применения изменений:"
    echo "  docker compose restart bot"
fi
