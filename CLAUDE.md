# Naglasúpan - Claude Development Guide

## Project Overview

Django backend + Next.js web-ui + Terraform infrastructure for Naglasúpan.


### Linting

**Django Backend** (from `src/django-backend/`):
```bash
make lint  # runs: uv run ruff check . && uv run ruff format --check .
```

**Web UI** (from `src/web-ui/`):
```bash
npm run lint  # runs: eslint
```

**Terraform** (from `infra/prod/app/`):
```bash
terraform fmt -check
terraform validate
```

### Testing

**Django Backend** (from `src/django-backend/`):
```bash
make test  # runs: uv run pytest
```

Note that you might need to install deps, if pytest can't be found:

```bash
make install-deps
```

### OpenAPI Workflow

When modifying Django API endpoints, you MUST regenerate types:

1. Make changes to Django API
2. Generate OpenAPI spec:
   ```bash
   cd src/django-backend && make extract-openapi
   ```
3. Generate TypeScript types in web-ui:
   ```bash
   cd src/web-ui && npm run generate-types
   ```

### Terraform Workflow

From `infra/prod/app/`:
```bash
terraform fmt      # Format files
terraform validate # Validate configuration
terraform plan     # Preview changes (requires credentials)
```

### Full CI Check

From project root:
```bash
make ci
```

## Browser Testing with Playwright

Use the Playwright MCP server for browser automation testing.

Test user credentials are in `.env.claude`:
```bash
source .env.claude
```

When testing authenticated features:
1. Navigate to the application URL (from `$TEST_APP_URL`)
2. Log in with test credentials (`$TEST_USER_EMAIL`, `$TEST_USER_PASSWORD`)
3. Perform the test scenario
4. Verify expected behavior visually
5. Only report back when the feature is confirmed working

## File Locations

| Component | Path |
|-----------|------|
| Django backend | `src/django-backend/` |
| Web UI | `src/web-ui/` |
| Terraform | `infra/prod/app/` |
| CI scripts | `scripts/ci/` |
| Roadmap | `roadmap/` |

