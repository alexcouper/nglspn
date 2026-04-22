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

### Translations Workflow

When you add a `t('new.key')` call in the web-ui:

1. Add the key to `src/web-ui/src/messages/en.json`.
2. Export `DEEPL_AUTH_KEY` (get one free at https://www.deepl.com/pro-api — free-tier keys end in `:fx`).
3. From `src/django-backend`, run `make translate-new-keys`. This:
   - Diffs `en.json` against `apps/translations/generators/state/en-snapshot.json`.
   - Calls DeepL for new keys (and for changed keys whose IS row is still machine-translated).
   - Bumps `source_hash` only (no retranslation) for changed keys whose IS row has been human-edited.
   - Marks removed keys as `retired=True`.
   - Writes a new Django data migration and updates the snapshot.
4. Commit the generated migration + the updated snapshot in the same PR as your code change.

`make ci` runs `make lint-translations` which fails if `en.json` and the snapshot have drifted — i.e. someone added a key without running `make translate-new-keys`. It also runs the web-ui's `npm run lint`, which includes `scripts/lint-i18n.mjs`: every `t("key")` call in a `.ts`/`.tsx` file must resolve to a key in `en.json`.

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

