.PHONY: help install dev-install run-bot run-admin migrate migrate-new seed test lint format docker-up docker-down docker-build docker-logs

help:
	@echo "دستورات موجود:"
	@echo "  make install        نصب وابستگی‌های اصلی"
	@echo "  make dev-install    نصب وابستگی‌های توسعه (تست/لینت)"
	@echo "  make run-bot        اجرای بات تلگرام (لوکال)"
	@echo "  make run-admin      اجرای پنل مدیریت (لوکال)"
	@echo "  make migrate        اجرای مایگریشن‌های آلمبیک"
	@echo "  make migrate-new    ساخت مایگریشن جدید (m=پیام)"
	@echo "  make seed           پر کردن دیتابیس با داده نمونه"
	@echo "  make test           اجرای تست‌ها با پوشش کد"
	@echo "  make lint           بررسی کیفیت کد با ruff/mypy"
	@echo "  make format         فرمت خودکار کد"
	@echo "  make docker-up      اجرای کل استک با Docker Compose"
	@echo "  make docker-down    خاموش‌کردن استک Docker"
	@echo "  make docker-build   ری‌بیلد ایمیج‌های Docker"
	@echo "  make docker-logs    نمایش لاگ زنده سرویس‌ها"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements-dev.txt

run-bot:
	python -m src.bot.main

run-admin:
	uvicorn src.admin.main:app --reload --port 8000

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(m)"

seed:
	python -m scripts.seed

test:
	pytest --cov=src --cov-report=term-missing

lint:
	ruff check src tests
	mypy src

format:
	ruff check --fix src tests
	ruff format src tests

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-build:
	docker compose build --no-cache

docker-logs:
	docker compose logs -f
