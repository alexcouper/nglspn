# 19. `CLAUDE.md` — remove the documentation for things that do not exist

**Finding:** Minor — `CLAUDE.md` documents `make ci`, `scripts/ci/` and `infra/prod/app/`. None of the three exist.
**Alex:** insteresting - remove the old documentation
**Type:** fix proposal
**Effort:** S, one file rewritten. The audit below found more drift than the three items in the finding — half the file is wrong.

## What is actually happening

`CLAUDE.md` is 95 lines. Every factual claim in it, checked against the repo:

| Lines | Claim | Verdict |
|---|---|---|
| 5 | "Django backend + Next.js web-ui + **Terraform infrastructure**" | **Wrong.** `infra/` contains exactly one file: `infra/grafana/serverless-containers-logs.json`. No `.tf` anywhere in the repo. |
| 10–13 | Backend `make lint` runs `ruff check` + `ruff format --check` | Correct. `src/django-backend/Makefile`. |
| 15–18 | Web UI `npm run lint  # runs: eslint` | **Incomplete.** `package.json` maps it to `eslint && tsc --noEmit`. Type checking is half the value and is not mentioned. Also `make lint` exists and is what CI runs. |
| 20–24 | Terraform lint "from `infra/prod/app/`" | **Wrong.** Path does not exist. |
| 28–31 | Backend `make test` = `uv run pytest` | Correct. |
| 33–37 | `make install-deps` if pytest is missing | Correct — the target exists (`uv sync --all-extras`), though it is missing from that Makefile's `.PHONY` and `help` list. |
| — | Frontend testing | **Missing entirely.** `src/web-ui/Makefile` has `test` (vitest), `test-watch`, `e2e`. None documented. |
| 39–51 | OpenAPI workflow: `make extract-openapi` then `npm run generate-types` | Correct commands. Does not say *which file to commit*, which is the part people get wrong. |
| 53–60 | "Terraform Workflow — from `infra/prod/app/`" | **Wrong.** Delete. |
| 62–67 | "Full CI Check: from project root `make ci`" | **Wrong.** There is no root `Makefile` at all. |
| 69–71 | "Use the Playwright MCP server for browser automation testing" | **Misleading.** The MCP server is not reliably present. The repo has its own Playwright: `src/web-ui/e2e/` (3 specs + fixtures), `playwright.config.ts`, `make e2e`, `npm run test:e2e`. None of it is mentioned. |
| 73–76 | Credentials in `.env.claude`, `source .env.claude` | Correct — file exists, gitignored at root `.gitignore:177`, carries `TEST_USER_EMAIL`, `TEST_USER_PASSWORD`, `TEST_APP_URL`. Worth noting `playwright.config.ts:6-16` already parses it, so sourcing is only needed for manual/MCP use. |
| 78–83 | The log-in-and-verify procedure | Fine. Keep. |
| 89 | Django backend → `src/django-backend/` | Correct. |
| 90 | Web UI → `src/web-ui/` | Correct. |
| 91 | Terraform → `infra/prod/app/` | **Wrong.** |
| 92 | CI scripts → `scripts/ci/` | **Wrong.** `scripts/` contains `app-common.mk`, `build.sh`, `find-free-port.sh`, `set_categories.py`. No `ci/`. CI is `.github/workflows/ci.yml`. |
| 93 | Roadmap → `roadmap/` | **Wrong.** No such directory. |
| — | `openspec/`, `docs/`, `infra/grafana/` | **Missing** from the table, and `openspec/` is where planning actually happens. |

### Where Terraform actually lives

It is in the separate `naglasupan-hq` repo. Three places in this repo name it:

- `openspec/changes/simplify-follow-and-cadence/tasks.md:50` — "the schedule itself lives in the `naglasupan-hq` infra repo, `k8s/base/notifications/`"
- `openspec/changes/simplify-follow-and-cadence/tasks.md:51` — "Delete the unreferenced `infra/modules/services/notification-scheduler/` Terraform module"
- `FOLLOW_UPS.md:64` — `naglasupan-hq:infra/modules/services/backend-task-checker/…`

So `CLAUDE.md` should not describe Terraform commands at all. It should say deployment and infrastructure live in `naglasupan-hq`, and that `infra/` here holds only the Grafana dashboard export. That is also the fact that matters operationally — blocker B1 in the summary is precisely "the thing you need to change is in the other repo".

### Load-bearing consequence

`openspec/changes/add-article-authoring/tasks.md:154` is:

```
- [ ] 16.1 Run `make ci` from project root — fix any lint, type, or test failures.
```

It is unticked and **cannot** be ticked, because the command does not exist. Fixing `CLAUDE.md` without fixing that task leaves a permanently unsatisfiable verification step.

### Same drift in `CONTRIBUTING.md`

Not asked for, but it is the same three facts and it will be found next:

- `CONTRIBUTING.md:17` — `| **Infra** | infra/prod/app/ | Terraform. |`
- `CONTRIBUTING.md:61-66` — a Terraform section with `terraform fmt -check` / `terraform validate`
- `CONTRIBUTING.md:130` — "CI must be green: backend lint + tests, web-ui build" — becomes stale the moment documents 08/09 land
- `CONTRIBUTING.md:146` — "End commit and PR trailers per `CLAUDE.md`" — `CLAUDE.md` says nothing about trailers, so this already dangles

Fix both files in one change, or the correction is half done.

## Proposed change

### Dependency on documents 08 and 09 — read this first

Documents 08 and 09 add `make test` to the web-ui CI job and a `make extra-tests` stage to both services. The Testing section below **describes the pipeline as it will be once those land.** If you apply this document first, the `make extra-tests` lines will document a target that does not exist yet — the same failure mode being fixed here.

Order: apply 08 and 09, then this. Or apply this and strike the two `extra-tests` lines, marked in the replacement below.

### Full replacement for `CLAUDE.md`

```markdown
# Naglasúpan - Claude Development Guide

## Project Overview

Django backend + Next.js web-ui. Deployment and infrastructure (Terraform, the
Kubernetes CronJobs that drive scheduled tasks) live in the **separate
`naglasupan-hq` repo** — `infra/` here holds only a Grafana dashboard export.

## Commands

Every check CI runs is a `make` target in one of the two service directories.
There is no root Makefile — run them from `src/django-backend/` or
`src/web-ui/`. The pipeline is `.github/workflows/ci.yml`.

**Django Backend** (from `src/django-backend/`):

```bash
make install-deps    # uv sync --all-extras; run this if pytest can't be found
make lint            # ruff check . && ruff format --check .
make extra-tests     # fails if backend-openapi.json is stale (see below)
make test            # pytest
```

**Web UI** (from `src/web-ui/`):

```bash
npm ci               # or: make install
make lint            # eslint && tsc --noEmit
make extra-tests     # no-op today; the stage exists so the pipeline is uniform
make test            # vitest run
make test-watch      # vitest, watch mode
make build-app       # next build
```

Running the full pipeline locally means running both lists. There is no
`make ci`.

## OpenAPI Workflow

When modifying Django API endpoints, you MUST regenerate types:

1. Make changes to the Django API (`api/routers/*.py`, `api/schemas/*.py`).
2. Regenerate the spec:
   ```bash
   cd src/django-backend && make extract-openapi
   ```
   This writes `src/web-ui/backend-openapi.json`. **Commit it.**
3. Regenerate the TypeScript types:
   ```bash
   cd src/web-ui && npm run generate-types
   ```
   This writes `src/lib/api-types.ts`, which is **gitignored** — do not commit
   it. It is regenerated on every `npm run dev` / `npm run build` and in CI.

`make extra-tests` in the backend fails the build if step 2 was skipped.

## Migrations

Any change to `apps/*/models.py` needs a matching migration in the same change.
Check with:

```bash
cd src/django-backend && uv run python manage.py makemigrations --check --dry-run
```

## Browser Testing with Playwright

The repo has its own Playwright suite in `src/web-ui/e2e/`, configured by
`src/web-ui/playwright.config.ts`. It needs the backend and the frontend both
running (`make dev` in each), and a seeded database (`make seed` in the
backend).

```bash
cd src/web-ui && npm run test:e2e        # or: npx playwright test e2e/login.spec.ts
```

Credentials come from `.env.claude` at the repo root (gitignored):
`TEST_USER_EMAIL`, `TEST_USER_PASSWORD`, `TEST_APP_URL`. `playwright.config.ts`
loads that file itself; `source .env.claude` is only needed when driving a
browser by hand or through the Playwright MCP server, which may or may not be
available in a given session.

Point Playwright at a running server with `TEST_APP_URL`; it defaults to
`http://localhost:3000`.

When verifying an authenticated feature manually:

1. Navigate to `$TEST_APP_URL`.
2. Log in with `$TEST_USER_EMAIL` / `$TEST_USER_PASSWORD`.
3. Perform the scenario.
4. Verify the expected behaviour visually.
5. Only report back when the feature is confirmed working.

Note: login is rate-limited to 5 attempts per minute, and a project caps at 10
gallery images. Both bite naive scripted runs.

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
```

Strike the two `make extra-tests` lines and the sentence "`make extra-tests` in the backend fails the build if step 2 was skipped" if document 09 is not being applied.

### The accompanying openspec fix

```diff
-- [ ] 16.1 Run `make ci` from project root — fix any lint, type, or test failures.
+- [ ] 16.1 Run `make lint && make extra-tests && make test` in `src/django-backend/`
+      and `make lint && make extra-tests && make test && make build-app` in
+      `src/web-ui/` — fix any lint, type, or test failures. (There is no root
+      `make ci`; these are the steps `.github/workflows/ci.yml` runs.)
```

in `openspec/changes/add-article-authoring/tasks.md:154`.

### `CONTRIBUTING.md`

```diff
 | **Frontend** | `src/web-ui/` | Next.js 16 App Router, React 19, TypeScript (strict), Tailwind 4, vitest + Playwright. Talks to the backend through a typed `APIClient` and **generated** types. |
-| **Infra** | `infra/prod/app/` | Terraform. |
+| **Infra** | separate repo, `naglasupan-hq` | Terraform + Kubernetes, including the CronJobs that drive scheduled tasks. `infra/` here is only a Grafana dashboard export. |
```

```diff
 **Frontend** (`src/web-ui/`):

 ```bash
-npm run lint   # eslint + tsc --noEmit
-npm test       # vitest
+make lint          # eslint + tsc --noEmit
+make test          # vitest
+make extra-tests   # no-op today; kept uniform with the backend
 ```
-
-**Terraform** (`infra/prod/app/`):
-
-```bash
-terraform fmt -check
-terraform validate
-```
```

```diff
-- **CI must be green** before merge: backend lint + tests, web-ui build.
+- **CI must be green** before merge: backend lint + OpenAPI drift check + tests;
+  web-ui lint, unit tests, and build.
```

```diff
-- End commit and PR trailers per `CLAUDE.md`.
```

(The last one dangles — `CLAUDE.md` has never said anything about trailers. Either drop the bullet or write the convention down somewhere. Dropping it is the honest option.)

### Commands

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-hq
jj new -m "CLAUDE.md/CONTRIBUTING.md: drop docs for commands and paths that don't exist"
# apply the replacement and the diffs above
jj diff --stat
```

## Tests

There is nothing to run. Verify by asserting the negative — every command and path the file names must exist:

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-hq

# every path named in the File Locations table
for p in src/django-backend src/web-ui .github/workflows/ci.yml \
         scripts/app-common.mk openspec/changes docs infra/grafana; do
  test -e "$p" && echo "ok   $p" || echo "MISS $p"
done

# every make target named in the file
cd src/django-backend && make -n install-deps lint extra-tests test extract-openapi >/dev/null && echo "backend targets ok"
cd ../web-ui        && make -n lint extra-tests test test-watch build-app >/dev/null && echo "web-ui targets ok"
```

`make -n` resolves the target without running it, so this is a cheap existence check. It will fail on `extra-tests` until document 09 lands — that is the dependency, working as intended.

Then, separately: nothing should reference `make ci` any more.

```bash
grep -rn "make ci\|scripts/ci\|infra/prod/app" --exclude-dir=.git --exclude-dir=.jj \
  --exclude-dir=node_modules --exclude-dir=review .
# expect: no output
```

## Risks and what this does not cover

- **Shortening `CLAUDE.md` loses nothing, because what it loses was false.** The only judgement call is the Playwright section: replacing "use the MCP server" with "run `make e2e`" is more accurate but points at a target that is itself broken — `src/web-ui/Makefile:50` sets `TEST_APP_URL` to a port `scripts/find-free-port.sh` guarantees is **free**, i.e. nothing is listening on it. The replacement above deliberately documents `npm run test:e2e` and `TEST_APP_URL` directly rather than `make e2e`, so the doc is not describing a broken path. Fixing the target is separate (see document 08).
- **`docs.md` says `CLAUDE.md` should hold "repo facts and commands an AI assistant needs every session. Keep it current and short."** The replacement is longer than the original in the Playwright and OpenAPI sections. If that is unwelcome, cut the manual-verification numbered list — it is procedure, not repo fact, and it belongs in `CONTRIBUTING.md`.
- **This does not add a root `make ci`.** That is the other way to resolve the same drift, and it would be defensible — a root Makefile delegating to both services would make the local pipeline one command and would have prevented the `node_modules` accident in document 17 by giving people a reason not to run tools from the root. It is a bigger change than a doc fix and should be its own decision. Documenting reality is the smaller, safer move; note that choosing it means `openspec` task 16.1 has to be reworded rather than satisfied.
- **The `naglasupan-hq` claim rests on three in-repo references, not on having read that repo.** If its layout has moved, the "Terraform / k8s / deployment" row will be right in spirit and wrong in detail.
