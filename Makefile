# Makefile for HLS Stream Checker

# Default target
.PHONY: help install run check web test clean

help:
	@echo "HLS Stream Checker - Утилита для проверки качества HLS потоков"
	@echo ""
	@echo "Доступные команды:"
	@echo "  install     - Установка зависимостей"
	@echo "  run         - Запуск проверки HLS потоков"
	@echo "  web         - Запуск веб-интерфейса"
	@echo "  test        - Запуск тестов"
	@echo "  clean       - Очистка временных файлов"
	@echo "  help        - Показать это сообщение"

install:
	@echo "Установка зависимостей..."
	pip install -r requirements.txt

run:
	@echo "Запуск проверки HLS потоков..."
	python hls_checker_single.py --count 1 --minutes 1

web:
	@echo "Запуск веб-интерфейса..."
	python run_web.py

test:
	@echo "Запуск тестов..."
	python -m pytest tests/ -v

test-web:
	@echo "Тестирование веб API..."
	python test_web_api.py

clean:
	@echo "Очистка временных файлов..."
	rm -rf data/csv/*.csv
	rm -rf data/json/*.json
	rm -rf logs/*.log
	@echo "Очистка завершена"

format:
	@echo "Форматирование кода..."
	black .
	isort .

lint:
	@echo "Проверка кода..."
	flake8 .
	black --check .
	isort --check-only .

setup-ubuntu:
	@echo "Настройка окружения Ubuntu..."
	./setup_ubuntu.sh

deploy:
	@echo "Развертывание приложения..."
	./deploy.sh

.PHONY: help install run check web test clean format lint setup-ubuntu deploy