APP:=web-ui
.PHONY: help install dev run-non-dev build-app lint test test-watch clean build publish e2e extra-tests check-bundle-budgets

# Opt in to the shared `extra-tests` stage (see scripts/app-common.mk).
EXTRA_TESTS := $(MAKE) --no-print-directory check-bundle-budgets

include ../../scripts/app-common.mk
help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  dev           Run development server"
	@echo "  run-non-dev   Build and run prod-mode server on LAN (reproduce prod bugs)"
	@echo "  build-app     Build the Next.js application"
	@echo "  lint          Run linter"
	@echo "  test          Run unit tests (vitest)"
	@echo "  test-watch    Run unit tests in watch mode"
	@echo "  extra-tests   Service-specific extra CI checks (per-route bundle budgets)"
	@echo "  check-bundle-budgets Fail if a route's client JS exceeds bundle-budgets.json"
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
	export NEXT_PUBLIC_CDN_URL="$${NEXT_PUBLIC_CDN_URL:-http://localhost:9000/naglasupan-dev}" && \
	PORT=$$(../../scripts/find-free-port.sh 3000) && \
	echo "Starting Next.js on port $$PORT (backend at $${NEXT_PUBLIC_API_URL:-http://localhost:8000}, cdn at $$NEXT_PUBLIC_CDN_URL)" && \
	PORT=$$PORT npm run dev

run-non-dev:
	./scripts/run-non-dev.sh

build:
	./scripts/build.sh

build-app:
	npm run build

lint:
	npm run lint

test:
	npm run test

test-watch:
	npm run test:watch

# Per-route client-JS size budgets, measured from the production build. CI runs
# `extra-tests` before `build-app`, so build first when there is nothing to
# measure: a budget check that finds no bundle and exits 0 is worse than no
# check. An existing .next is reused, so it is cheap to run locally.
check-bundle-budgets:
	@if [ ! -f .next/BUILD_ID ]; then \
		echo "No production build in .next; building one to measure."; \
		$(MAKE) --no-print-directory build-app; \
	fi
	npm run test:scripts
	node scripts/check-bundle-budgets.mjs

e2e:
	@if [ -f ../../.backend-port ]; then \
		export TEST_APP_URL="http://localhost:$$(../../scripts/find-free-port.sh 3000 | head -1)"; \
	fi && \
	npm run test:e2e

clean:
	rm -rf .next
	rm -rf node_modules
