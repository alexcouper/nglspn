# 09. A uniform `extra-tests` stage, carrying the OpenAPI drift check

**Finding:** I10 — nothing in CI enforces that `backend-openapi.json` is regenerated; `npm run generate-types` reads the committed file, so a stale spec passes green.
**Alex:** Add that step too to make sure this is done. But do it by adding a stage that any service could add and using that in the for now hardcoded pipeline. eg a "make extra-tests" that we run in both web-ui and django-backend and one can be a no-op for now.
**Type:** fix proposal
**Effort:** M, three small file edits (`scripts/app-common.mk`, `src/django-backend/Makefile`, `.github/workflows/ci.yml`). The design question — how a service opts in without breaking the pipeline — is the part worth getting right.

## What is actually happening

The contract is generated in one place and consumed in another, and only the consumer runs in CI.

`src/django-backend/scripts/extract_openapi.py` writes the spec:

```python
output_file = repo_root / "src" / "web-ui" / "backend-openapi.json"
output_file.write_text(openapi_json, encoding="utf-8")
```

`src/web-ui/package.json`:

```json
"generate-types": "openapi-typescript backend-openapi.json -o src/lib/api-types.ts",
```

So `npm run generate-types` — the step CI does run — reads the **committed** JSON. Change a Ninja router or schema, forget `make extract-openapi`, and CI regenerates types from the old spec and passes. The frontend is then reviewed against a contract the backend no longer serves. On this branch the spec happens to be byte-identical to a fresh regeneration, but only because it was done by hand.

`CLAUDE.md` and `CONTRIBUTING.md:70-84` both call this out as mandatory. It is the repo's most-forgotten step and it is enforced by prose only.

### The repo's make layout

There is **no root `Makefile`**. Each service has one, and both include a shared fragment:

- `src/django-backend/Makefile` — `include ../../scripts/app-common.mk` on line 4. Targets: `install-deps`, `dev-services`, `dev-services-down`, `dev`, `bootstrap`, `seed`, `seed-prod-copy`, `migrate`, `makemigrations`, `shell`, `test`, `createsuperuser`, `extract-openapi`, `clean`, `lint`.
- `src/web-ui/Makefile` — `include ../../scripts/app-common.mk` on line 4. Targets: `install`, `dev`, `run-non-dev`, `build`, `build-app`, `lint`, `test`, `test-watch`, `e2e`, `clean`.
- `scripts/app-common.mk` — the entire file:

  ```make
  build:
  	../../scripts/build.sh $(APP)

  lint-default:
  	@echo "Linting not implemented for $(APP)"
  ```

  `lint-default` is dead — both services define `lint` outright and nothing depends on the default. Worth knowing, because it shows the intended "shared default" idiom exists but was never wired.

Neither service has a `Makefile` target that verifies the spec. `make extract-openapi` only *writes* it, so the check has to be regenerate-then-compare.

## Proposed change

### The stage

`make extra-tests` in every service, run identically from the pipeline. A service opts in by setting an `EXTRA_TESTS` variable before the include; a service that sets nothing inherits a no-op. This means adding a third service can never break the hardcoded pipeline by not having the target.

**`scripts/app-common.mk`**

```diff
 build:
 	../../scripts/build.sh $(APP)

 lint-default:
 	@echo "Linting not implemented for $(APP)"
+
+# Per-service verification stage. The pipeline runs `make extra-tests` for
+# every service, so every service must have the target. A service opts in by
+# setting EXTRA_TESTS to the command(s) to run *before* including this file;
+# anything that sets nothing inherits the no-op below and the pipeline line
+# stays uniform.
+EXTRA_TESTS ?= echo "$(APP): no extra tests"
+
+.PHONY: extra-tests
+extra-tests:
+	@$(EXTRA_TESTS)
```

A variable rather than an overridable target on purpose: if `app-common.mk` defined a real `extra-tests:` recipe and `src/django-backend/Makefile` defined another, GNU make emits `warning: overriding recipe for target 'extra-tests'` on every invocation. `?=` gives the same "default plus override" behaviour with no warning and no `-default` suffix convention.

**`src/django-backend/Makefile`** — the variable must be set before the include, since `?=` only takes effect if unset at that point.

```diff
 APP:=django-backend
-.PHONY: help install dev migrate makemigrations shell test createsuperuser clean extract-openapi lint bootstrap seed seed-prod-copy dev-services dev-services-down
+.PHONY: help install dev migrate makemigrations shell test createsuperuser clean extract-openapi lint bootstrap seed seed-prod-copy dev-services dev-services-down check-openapi-sync
+
+# Opt in to the shared `extra-tests` stage (see scripts/app-common.mk).
+EXTRA_TESTS := $(MAKE) --no-print-directory check-openapi-sync

 include ../../scripts/app-common.mk
```

and the check itself, next to `extract-openapi`:

```diff
 extract-openapi:
 	uv run python scripts/extract_openapi.py
+
+# Fails if the committed backend-openapi.json is not what the current routers
+# and schemas produce. Regenerates in place, so a failure leaves the correct
+# file on disk ready to commit.
+check-openapi-sync:
+	@before=$$(mktemp) && cp ../web-ui/backend-openapi.json $$before && \
+	uv run python scripts/extract_openapi.py && \
+	if diff -q $$before ../web-ui/backend-openapi.json >/dev/null; then \
+		rm -f $$before; \
+		echo "backend-openapi.json is in sync."; \
+	else \
+		rm -f $$before; \
+		echo "ERROR: backend-openapi.json was stale. It has been regenerated;"; \
+		echo "       commit src/web-ui/backend-openapi.json and push again."; \
+		exit 1; \
+	fi
```

and the help text:

```diff
 	@echo "  extract-openapi Extract OpenAPI specification to openapi.json"
+	@echo "  check-openapi-sync Fail if backend-openapi.json is stale"
+	@echo "  extra-tests   Service-specific extra CI checks (OpenAPI drift)"
 	@echo "  lint          Run ruff linter and formatter check"
```

**`src/web-ui/Makefile`** — no-op, so nothing to add beyond the `.PHONY` line and a help entry:

```diff
 APP:=web-ui
-.PHONY: help install dev run-non-dev build-app lint test test-watch clean build publish e2e
+.PHONY: help install dev run-non-dev build-app lint test test-watch clean build publish e2e extra-tests
```

```diff
 	@echo "  test-watch    Run unit tests in watch mode"
+	@echo "  extra-tests   Service-specific extra CI checks (none yet)"
 	@echo "  e2e           Run Playwright e2e tests"
```

`extra-tests` in web-ui resolves through `EXTRA_TESTS ?= echo "$(APP): no extra tests"` and prints `web-ui: no extra tests`. That is the no-op Alex asked for, and the day web-ui grows a bundle-size budget or a licence check it sets `EXTRA_TESTS` and the pipeline line does not change.

### Why `diff` and not `git diff --exit-code`

The one-liner in the review was `make extract-openapi && git diff --exit-code -- ../web-ui/backend-openapi.json`. It works in CI, where the checkout is a clean plain-git tree. It misfires locally in this repo: it is a colocated **jj** repo, and git `HEAD` lags jj's working-copy commit. At the time of writing `git status` reports `D REVIEW.md` for a deletion that is already committed in jj (`xyly 2aa5`). A `git diff` check would therefore report drift that does not exist as soon as the spec is touched in an earlier jj change.

The `mktemp` + `diff -q` form above compares the file against itself before and after regeneration. It is identical under git, jj, and no VCS at all, and it is what makes the target useful as a local pre-push check rather than a CI-only one.

If you would rather have the short version and accept CI-only correctness, it is:

```make
EXTRA_TESTS := $(MAKE) extract-openapi && git diff --exit-code -- ../web-ui/backend-openapi.json
```

Scope the path explicitly either way — an unscoped `git diff --exit-code` would also fire on `uv.lock` if `make install-deps` (`uv sync --all-extras`) ever touches it.

### The workflow

```diff
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
+      - run: make extra-tests
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
+      - run: make extra-tests
       - run: make test
       - run: make build-app
```

### Ordering constraint

The drift check must not run after anything that has already consumed or regenerated the spec, and must not run in a job where the tree has been dirtied by generation.

In practice this is satisfied for free, because the two concerns are in **different jobs**: `generate-types` only ever runs in the `web-ui` job and only ever *reads* `backend-openapi.json` while writing the gitignored `src/lib/api-types.ts` (`src/web-ui/.gitignore:44`). Nothing in the web-ui job can change the spec. So `extra-tests` in `django-backend` is independent by construction.

It still matters for two futures:

- If the jobs are ever merged into one, `check-openapi-sync` must run **before** `npm run generate-types` / `make build-app`, otherwise a stale spec has already produced types that then get validated against themselves.
- `make build-app` runs `npm run build`, which reruns `generate-types`. Same reasoning.

Position within the backend job: after `lint`, before `test`. The check is seconds; `make test` is 4m41s. Failing on a stale spec should not cost five minutes. That also matches the uniform stage order in document 08: install → lint → extra-tests → test → build.

### Ownership split with document 08

| Line | Owner |
|---|---|
| `- run: make extra-tests` in **both** jobs | **this document (09)** |
| `scripts/app-common.mk`, both `Makefile`s | **this document (09)** |
| `- run: make test` in the `web-ui` job | document 08 |

Apply both in one change; the workflow diff above already shows `make test` present so the intended final file is unambiguous.

### Commands

```bash
jj new -m "CI: add a per-service extra-tests stage; enforce OpenAPI regeneration"
# edit scripts/app-common.mk, src/django-backend/Makefile, src/web-ui/Makefile, .github/workflows/ci.yml

cd src/web-ui && make extra-tests
# expect: web-ui: no extra tests

cd src/django-backend && make extra-tests
# expect: backend-openapi.json is in sync.
```

## Tests

There is no unit test for a Makefile target; verify by exercising both outcomes.

**Positive** — on the branch as it stands, the spec is in sync, so the target must pass:

```bash
cd src/django-backend && make extra-tests   # exit 0
```

**Negative** — prove it actually catches drift. Perturb the spec, run, restore:

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-hq
python3 -c "p='src/web-ui/backend-openapi.json'; s=open(p).read(); open(p,'w').write(s.replace('\"title\":','\"title_DRIFT\":',1))"
cd src/django-backend && make extra-tests   # must exit 1 with the ERROR message
```

The target regenerates in place, so the file is already restored to correct content by the failing run itself — confirm with `jj diff --stat -- src/web-ui/backend-openapi.json` (expect empty).

**Second negative** — prove it catches a real backend change, which is the case that matters:

```bash
# add a field to any schema in src/django-backend/api/schemas/, then:
cd src/django-backend && make extra-tests   # must exit 1
# revert the schema change, then re-run: exit 0
```

**No-op path**:

```bash
cd src/web-ui && make extra-tests   # exit 0, prints "web-ui: no extra tests"
```

## Risks and what this does not cover

- **`extract_openapi.py` fails silently.** It wraps everything in `except Exception: return False` and `sys.exit(1)` with **no message**. If spec extraction breaks for an unrelated reason — an import error in a router, a settings problem — CI shows a bare non-zero exit at `make extra-tests` and the operator will assume drift. Worth deleting the blanket `except` in a follow-up so the traceback surfaces; out of scope here, but it is the first thing to look at if this step ever fails inexplicably.
- **The check needs Django to import.** `django.setup()` plus `from api.main import api`. No database connection is made, and `make test` in the same job already proves settings load in CI, so this is safe — but it does make the backend job's `extra-tests` step depend on `make install-deps` having run.
- **`$(MAKE)` recursion inside `EXTRA_TESTS`** prints "Entering directory" noise without `--no-print-directory`; the diff includes the flag. Cosmetic.
- **This does not stop anyone regenerating the spec without regenerating types.** It can't — `api-types.ts` is gitignored by design and regenerated in CI and locally on every `npm run dev` / `build`. The gap this closes is only the committed-spec-goes-stale one, which is the one that actually happens.
- **It does not validate that the spec is semantically compatible** with what the frontend calls. A breaking rename regenerates cleanly and passes; the failure then shows up as a `tsc` error in `make lint` in the web-ui job. That is the right division of labour, but it means "extra-tests green" means "the spec matches the code", not "the frontend still works".
- **The variable-based default is slightly clever.** If someone later adds a plain `extra-tests:` target to a service Makefile alongside the include, make will warn about an overridden recipe. The comment in `app-common.mk` says to set `EXTRA_TESTS` instead; that is the only thing keeping it obvious.
