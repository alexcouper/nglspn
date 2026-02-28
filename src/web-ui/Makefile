APP:=web-ui
.PHONY: help install dev build-app lint clean build publish e2e maintenance-on maintenance-off dev-maintenance

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
	@echo ""
	@echo "Maintenance mode:"
	@echo "  maintenance-on    Enable maintenance in public/maintenance.json"
	@echo "  maintenance-off   Disable maintenance in public/maintenance.json"
	@echo "  dev-maintenance   Run dev server with local maintenance config"

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

maintenance-on:
	@sed -i '' 's/"enabled": false/"enabled": true/' public/maintenance.json
	@echo "Maintenance mode enabled in public/maintenance.json"
	@echo "Run: make dev-maintenance"

maintenance-off:
	@sed -i '' 's/"enabled": true/"enabled": false/' public/maintenance.json
	@echo "Maintenance mode disabled in public/maintenance.json"

dev-maintenance:
	@if [ -f ../../.backend-port ]; then \
		export NEXT_PUBLIC_API_URL="http://localhost:$$(cat ../../.backend-port)"; \
	fi && \
	PORT=$$(../../scripts/find-free-port.sh 3000) && \
	echo "Starting Next.js on port $$PORT with local maintenance config" && \
	echo "Bypass maintenance: http://localhost:$$PORT/?bypass_maintenance=local-bypass" && \
	NEXT_PUBLIC_USE_LOCAL_MAINTENANCE=true MAINTENANCE_BYPASS_SECRET=local-bypass PORT=$$PORT npm run dev

clean:
	rm -rf .next
	rm -rf node_modules

