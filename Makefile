.PHONY: ci lint test lint-backend lint-web-ui lint-translations test-backend

ci: lint test

lint: lint-backend lint-translations lint-web-ui

test: test-backend

lint-backend:
	$(MAKE) -C src/django-backend lint

lint-translations:
	$(MAKE) -C src/django-backend lint-translations

lint-web-ui:
	cd src/web-ui && npm run lint

test-backend:
	$(MAKE) -C src/django-backend test
