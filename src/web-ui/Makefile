APP:=web-ui
.PHONY: help install dev build-app lint clean build publish e2e

include ../../scripts/app-common.mk
help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  dev           Run development server"
	@echo "  build-app     Build the Next.js application"
	@echo "  lint          Run linter"
	@echo "  e2e           Run Playwright e2e tests"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build Docker image (requires TAG=xxx)"
	@echo "  publish       Push Docker image to registry (requires TAG=xxx)"

install:
	npm install

dev:
	@if [ -f ../../.backend-port ]; then \
		export NEXT_PUBLIC_API_URL="http://localhost:$$(cat ../../.backend-port)"; \
	fi && \
	PORT=$$(../../scripts/find-free-port.sh 3000) && \
	echo "Starting Next.js on port $$PORT (backend at $${NEXT_PUBLIC_API_URL:-http://localhost:8000})" && \
	PORT=$$PORT npm run dev

build:
	./scripts/build.sh

build-app:
	npm run build

lint:
	npm run lint

e2e:
	@if [ -f ../../.backend-port ]; then \
		export TEST_APP_URL="http://localhost:$$(../../scripts/find-free-port.sh 3000 | head -1)"; \
	fi && \
	npm run test:e2e

clean:
	rm -rf .next
	rm -rf node_modules

