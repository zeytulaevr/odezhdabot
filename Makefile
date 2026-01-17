.PHONY: help install run dev test lint format clean docker-build docker-up docker-down docker-logs migrate

# Цвета для вывода
YELLOW=\033[0;33m
NC=\033[0m # No Color

help: ## Показать справку
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Установить зависимости
	poetry install

install-dev: ## Установить зависимости включая dev
	poetry install --with dev

run: ## Запустить бота
	poetry run python -m src

dev: ## Запустить бота в режиме разработки
	LOG_LEVEL=DEBUG poetry run python -m src

test: ## Запустить тесты
	poetry run pytest

test-cov: ## Запустить тесты с покрытием
	poetry run pytest --cov=src --cov-report=html --cov-report=term-missing

lint: ## Проверить код линтером
	poetry run flake8 src/
	poetry run mypy src/

format: ## Отформатировать код
	poetry run black src/
	poetry run isort src/

clean: ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.db" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage

docker-build: ## Собрать Docker образ
	cd docker && docker-compose build

docker-up: ## Запустить Docker контейнеры
	cd docker && docker-compose up -d

docker-down: ## Остановить Docker контейнеры
	cd docker && docker-compose down

docker-logs: ## Показать логи Docker контейнеров
	cd docker && docker-compose logs -f bot

docker-restart: ## Перезапустить Docker контейнеры
	cd docker && docker-compose restart

migrate: ## Применить миграции
	poetry run alembic upgrade head

migrate-create: ## Создать новую миграцию
	@read -p "Введите описание миграции: " desc; \
	poetry run alembic revision --autogenerate -m "$$desc"

migrate-rollback: ## Откатить последнюю миграцию
	poetry run alembic downgrade -1

db-shell: ## Подключиться к PostgreSQL
	docker exec -it telegram-bot-postgres psql -U botuser -d telegram_bot

redis-cli: ## Подключиться к Redis CLI
	docker exec -it telegram-bot-redis redis-cli
