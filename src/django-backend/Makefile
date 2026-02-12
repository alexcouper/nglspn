APP:=django-backend
.PHONY: help install dev migrate makemigrations shell test createsuperuser clean extract-openapi lint bootstrap seed

include ../../scripts/app-common.mk

help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  dev           Run development server (auto-bootstraps if no db)"
	@echo "  bootstrap     Initialize database with migrations and default users"
	@echo "  migrate       Run database migrations"
	@echo "  makemigrations Create new migrations"
	@echo "  shell         Open Django shell"
	@echo "  test          Run tests"
	@echo "  createsuperuser Create superuser"
	@echo "  extract-openapi Extract OpenAPI specification to openapi.json"
	@echo "  lint          Run ruff linter and formatter check"
	@echo "  seed          Populate database with sample users, projects, and competitions"
	@echo "  clean         Clean cache files"

install-deps:
	uv sync --all-extras

dev:
	@if [ ! -f db.sqlite3 ]; then \
		echo "No database found, running bootstrap..."; \
		$(MAKE) bootstrap; \
	fi
	@PORT=$$(../../scripts/find-free-port.sh 8000) && \
	echo $$PORT > ../../.backend-port && \
	echo "Starting Django on port $$PORT (saved to .backend-port)" && \
	ADMIN_ALLOWED_IPS=127.0.0.1 DEBUG=true uv run python manage.py runserver 0.0.0.0:$$PORT


bootstrap:
	uv run python scripts/bootstrap_db.py

seed: bootstrap
	uv run python scripts/seed_db.py

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

shell:
	uv run python manage.py shell

test:
	uv run pytest

createsuperuser:
	uv run python manage.py createsuperuser

extract-openapi:
	uv run python scripts/extract_openapi.py

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

lint:
	uv run ruff check .
	uv run ruff format --check .
