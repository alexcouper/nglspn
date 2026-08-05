APP:=django-backend
.PHONY: help install dev migrate makemigrations shell test createsuperuser clean extract-openapi lint bootstrap seed seed-ballots seed-prod-copy dev-services dev-services-down

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
	@echo "  seed-ballots  Fill a competition with partial ballots to exercise the results page"
	@echo "  clean         Clean cache files"

install-deps:
	uv sync --all-extras

dev-services:
	@echo "Starting dev services (MinIO) via docker compose..."
	docker compose -f docker-compose.dev.yml up -d --wait minio
	docker compose -f docker-compose.dev.yml up --no-log-prefix --exit-code-from minio-init minio-init

dev-services-down:
	docker compose -f docker-compose.dev.yml down

# Env vars that point Django at the local MinIO instance started by
# `dev-services`. Prefixed onto `runserver` so they don't leak into other
# targets or require a .env file.
DEV_S3_ENV := \
	S3_BUCKET_NAME=naglasupan-dev \
	S3_ENDPOINT_URL=http://localhost:9000 \
	S3_REGION=us-east-1 \
	S3_PUBLIC_URL_BASE=http://localhost:9000/naglasupan-dev \
	S3_CDN_DOMAIN= \
	SCW_ACCESS_KEY=minioadmin \
	SCW_SECRET_KEY=minioadmin

dev: dev-services
	@if [ ! -f db.sqlite3 ]; then \
		echo "No database found, running bootstrap..."; \
		$(MAKE) bootstrap; \
	fi
	@PORT=$$(../../scripts/find-free-port.sh 8000) && \
	echo $$PORT > ../../.backend-port && \
	echo "Starting Django on port $$PORT (saved to .backend-port)" && \
	ADMIN_ALLOWED_IPS=127.0.0.1 ALLOWED_HOSTS=* DEBUG=true $(DEV_S3_ENV) \
		uv run python manage.py runserver 0.0.0.0:$$PORT


bootstrap:
	uv run python scripts/bootstrap_db.py

seed: bootstrap
	uv run python scripts/seed_db.py

seed-ballots:
	uv run python scripts/seed_ballots.py $(ARGS)

seed-prod-copy: bootstrap dev-services
	$(DEV_S3_ENV) uv run python scripts/seed_prod_copy.py

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
