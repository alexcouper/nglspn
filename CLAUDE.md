# Naglasúpan - Claude Development Guide

## Project Overview

Django backend + Next.js web-ui for Naglasúpan. Deployment and infrastructure
(Terraform, Kubernetes) live in the **separate `naglasupan-hq` repo** — `infra/`
here holds only a Grafana dashboard export.

## Version control

The repo is jj-colocated. Use `jj`, not `git`. Git HEAD lags the jj working
copy, so `git status` and `git diff` report phantom modifications — don't read
them as truth, and don't write checks that depend on them.

## Commands

Every check CI runs is a `make` target in one of the two service directories.
There is no root `Makefile` and no `make ci` — running the pipeline locally
means running both lists below. The pipeline is `.github/workflows/ci.yml`: two
independent jobs, same stage order, `install → lint → extra-tests → test →
(build)`.

**Django Backend** (from `src/django-backend/`):
```bash
make install-deps  # uv sync --all-extras; run this if pytest can't be found
make lint          # ruff check . && ruff format --check .
make extra-tests   # fails if backend-openapi.json is stale (see below)
make test          # pytest
```

**Web UI** (from `src/web-ui/`):
```bash
npm ci             # or: make install
make lint          # eslint && tsc --noEmit
make extra-tests   # service-specific extra CI checks
make test          # vitest run
make test-watch    # vitest, watch mode
make build-app     # next build
```

`extra-tests` is defined once, in `scripts/app-common.mk`, as `@$(EXTRA_TESTS)`
with `EXTRA_TESTS ?= echo "$(APP): no extra tests"`. A service opts in by
assigning `EXTRA_TESTS` **before** its `include ../../scripts/app-common.mk`
line — `?=` only fires while the variable is unset. Set the variable; don't add
a second `extra-tests:` recipe, or make warns on every invocation. A service
that assigns nothing inherits the no-op, so a new service can't break the
pipeline by lacking the target.

Playwright is deliberately not in CI: `playwright.config.ts` has no `webServer`
block and the specs need a Next server, a Django backend, a database and S3, so
it is a separate job rather than a line. See `src/web-ui/e2e/` below.

## OpenAPI Workflow

When modifying Django API endpoints, you MUST regenerate types:

1. Make changes to the Django API (`api/routers/*.py`, `api/schemas/*.py`).
2. Generate the OpenAPI spec:
   ```bash
   cd src/django-backend && make extract-openapi
   ```
   This writes `src/web-ui/backend-openapi.json` in place. **Commit it.**
3. Generate TypeScript types in web-ui:
   ```bash
   cd src/web-ui && npm run generate-types
   ```
   This writes `src/lib/api-types.ts`, which is **gitignored** — do not commit
   it. `npm run dev`, `npm run build` and CI all regenerate it.

The backend's `make extra-tests` runs `check-openapi-sync`, which regenerates
the spec into a temp file and `diff -q`s it, so a skipped step 2 fails the
build. It regenerates in place, so a failing run leaves the correct file ready
to commit.

## Migrations

Any change to `apps/*/models.py` needs a matching migration in the same change.
Check with:

```bash
cd src/django-backend && uv run python manage.py makemigrations --check --dry-run
```

## Browser Testing with Playwright

The repo has its own Playwright suite in `src/web-ui/e2e/`, configured by
`src/web-ui/playwright.config.ts`. It needs the backend and frontend both
running (`make dev` in each) and a seeded database (`make seed` in the backend).

```bash
cd src/web-ui && npx playwright test e2e/login.spec.ts   # or: npm run test:e2e
```

Point it at a running server with `TEST_APP_URL`; it defaults to
`http://localhost:3000`. (`make e2e` in the web-ui Makefile currently derives
`TEST_APP_URL` from `scripts/find-free-port.sh`, i.e. a port with nothing
listening on it — don't use it.)

Test user credentials come from `.env.claude` at the repo root (gitignored):
`TEST_USER_EMAIL`, `TEST_USER_PASSWORD`, `TEST_APP_URL`. `playwright.config.ts`
parses that file itself; `source .env.claude` is only needed when driving a
browser by hand or through the Playwright MCP server, which may not be present
in a given session.

Two limits that bite scripted runs: login is rate-limited to 5 requests per
minute per IP (`api/routers/auth.py`, `api/rate_limit.py`), and a project caps
at 10 gallery images (`services/images/handler_interface.py`).

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
| CI pipeline | `.github/workflows/ci.yml` |
| Shared make fragment | `scripts/app-common.mk` |
| Change plans | `openspec/changes/<name>/` |
| Design docs and investigations | `docs/` — see `docs.md` for the map |
| Grafana dashboards | `infra/grafana/` |
| Terraform / k8s / deployment | separate repo: `naglasupan-hq` |

