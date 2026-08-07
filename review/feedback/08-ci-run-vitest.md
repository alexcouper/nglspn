# 08. Run the vitest suite in CI

**Finding:** I9 — `.github/workflows/ci.yml` never runs the frontend tests, so 89 new vitest tests and two Playwright specs do not execute on a PR.
**Alex:** Yes let's have the ci run the vitest tests.
**Type:** fix proposal
**Effort:** S, one workflow line for vitest. Playwright is a separate, much larger job and is deferred — reasoning below.

## What is actually happening

`.github/workflows/ci.yml` has two jobs. Verbatim, the whole file:

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  django-backend:
    name: Django Backend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/django-backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: make install-deps
      - run: make lint
      - run: make test

  web-ui:
    name: Web UI Build
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/web-ui
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: src/web-ui/package-lock.json
      - run: npm ci
      - run: npm run generate-types
      - run: make lint
      - run: make build-app
```

The backend job runs `make test`. The web-ui job does not.

The targets already exist. `src/web-ui/Makefile`:

```make
test:
	npm run test

test-watch:
	npm run test:watch

e2e:
	@if [ -f ../../.backend-port ]; then \
		export TEST_APP_URL="http://localhost:$$(../../scripts/find-free-port.sh 3000 | head -1)"; \
	fi && \
	npm run test:e2e
```

and `src/web-ui/package.json` maps `test` → `vitest run`, `test:e2e` → `playwright test`.

`src/web-ui/vitest.config.ts` already excludes the Playwright directory:

```ts
include: ["src/**/*.{test,spec}.{ts,tsx}"],
exclude: ["node_modules", ".next", "e2e"],
```

So `make test` runs vitest only — 11 files, 153 tests, 2.7 s locally. It needs nothing beyond `npm ci`, which the job already does. There is no reason it is not there other than nobody added the line.

`make lint` in that job is `npm run lint` = `eslint && tsc --noEmit`, so type checking is already covered; vitest adds behaviour coverage, including `markdown-parity.test.tsx`, the only guard against the MDXEditor pipeline and the read page's remark/rehype pipeline drifting apart.

## Proposed change

One line in `.github/workflows/ci.yml`, in the `web-ui` job, after `make lint` and before `make build-app`:

```diff
       - run: npm ci
       - run: npm run generate-types
       - run: make lint
+      - run: make extra-tests
+      - run: make test
       - run: make build-app
```

Position: before `build-app`. Vitest takes ~3 s, the Next build takes minutes; putting the cheap check first makes a broken test fail the PR quickly. After `lint` because a type error should surface before a test failure that is really a type error.

`make test` already exists in `src/web-ui/Makefile:44`. **No Makefile change is needed for this document.**

### Ownership split with document 09

The final `ci.yml` is one coherent edit; the two documents own different lines of it:

| Line | Owner |
|---|---|
| `- run: make test` in the `web-ui` job | **this document (08)** |
| `- run: make extra-tests` in the `web-ui` job | document 09 |
| `- run: make extra-tests` in the `django-backend` job | document 09 |
| all `Makefile` / `scripts/app-common.mk` changes | document 09 |

The `extra-tests` line is shown greyed into the diff above only so the intended final order is unambiguous. If 09 is not applied, drop that line and the diff is a single addition.

Final state of both jobs once 08 and 09 are applied:

```yaml
  django-backend:
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: make install-deps
      - run: make lint
      - run: make extra-tests      # 09
      - run: make test

  web-ui:
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: src/web-ui/package-lock.json
      - run: npm ci
      - run: npm run generate-types
      - run: make lint
      - run: make extra-tests      # 09
      - run: make test             # 08
      - run: make build-app
```

Same stage order in both jobs: install → lint → extra-tests → test → (build).

### Commands

```bash
jj new -m "CI: run the web-ui vitest suite on pull requests"
# edit .github/workflows/ci.yml as above
cd src/web-ui && make test        # confirm the target passes locally first
```

Expected: `Test Files 11 passed (11) / Tests 153 passed (153)`.

## Playwright — do not add it now

`make e2e` should **not** go into CI in this change. This is not caution, it is that the job does not exist yet and would be several days of work, not a line:

1. **No servers.** `src/web-ui/playwright.config.ts` has no `webServer` block. `baseURL` falls back to `process.env.TEST_APP_URL || "http://localhost:3000"`. Nothing in CI would be listening. The specs need a running Next server *and* a running Django backend *and* a database *and* S3/MinIO — `article-images.spec.ts` uploads through the presigned-PUT path.

2. **Real credentials.** Every spec logs in with `process.env.TEST_USER_PASSWORD` and throws if it is unset (`e2e/article-images.spec.ts:9-14`, `e2e/login.spec.ts:6-11`). The config reads these from `../../.env.claude`, which is gitignored (root `.gitignore:177`). CI would need GitHub secrets plus a seeded user that matches them.

3. **A seeded, mutable database.** The specs walk from `/my-projects` to a project and create articles. They need `make seed` data and they leave rows behind.

4. **Known environmental limits that break naive runs.** There is a 5-per-minute login rate limit and a 10-image-per-project cap. `playwright.config.ts` sets `workers: process.env.CI ? 1 : undefined` and `retries: 2` — retries multiply login attempts, which is exactly the shape that trips the rate limit. Each spec would need `storageState` login reuse rather than logging in per test.

5. **The `make e2e` target is itself wrong.** It sets

   ```make
   export TEST_APP_URL="http://localhost:$$(../../scripts/find-free-port.sh 3000 | head -1)"
   ```

   and `scripts/find-free-port.sh` returns the first port with *nothing listening on it*. The target therefore points Playwright at a guaranteed-dead port whenever `../../.backend-port` exists. That is a live bug in the target, independent of CI, and it means "add `- run: make e2e`" would not work even against a running stack.

Recommendation: leave Playwright as a local/manual tool for now and fix `make e2e` separately. If it is later wanted in CI, the shape is a third job that brings the stack up via `docker-compose.yml`, runs `make bootstrap && make seed`, injects `TEST_USER_EMAIL`/`TEST_USER_PASSWORD` from repository secrets, runs `npx playwright install --with-deps chromium`, and uses a shared `storageState`. That is a proposal of its own, not a line in this one.

## Tests

The change is CI configuration; verification is the pipeline itself.

```bash
cd src/web-ui && make test          # must pass before pushing
```

Then confirm on the PR that the `Web UI Build` job shows a `make test` step with the vitest summary in its log.

Negative check — prove the step actually gates. On a throwaway change, break one assertion in `src/app/projects/[slug]/articles/markdown-parity.test.tsx`, push, and confirm the job goes red at the `make test` step rather than green. Then drop the change.

## Risks and what this does not cover

- **CI time.** Negligible: ~3 s of vitest against a multi-minute Next build.
- **Flakiness.** All 11 suites are jsdom unit tests with no network and no timers beyond `MyRanking.test.tsx`. Nothing here is a plausible flake source, but a newly-red PR on an unrelated branch is the first thing to look at if one appears.
- **This does not enforce OpenAPI regeneration.** Separate finding, document 09.
- **This does not run Playwright**, so the create → publish → notify → delete path stays unguarded by CI, and `openspec/changes/add-article-authoring/tasks.md:156` (16.3) stays unticked and honest.
- **`make build-app` runs `npm run build`, which reruns `generate-types`.** Unrelated to this change, but it means the job regenerates types twice. Not worth touching here.
