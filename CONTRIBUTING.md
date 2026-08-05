# Contributing to Naglasúpan

Thanks for pitching in. Naglasúpan is a nail soup — it gets good because people
bring what they have. This guide gets you from clone to merged PR without
tripping over the handful of things that actually bite this repo.

It's written for **both humans and AI coding assistants**. If you're an
assistant, there's a short section near the bottom aimed squarely at you, but
read the rest too — the conventions are the same.

## The repo in one breath

| Part | Path | Stack |
|------|------|-------|
| **Backend** | `src/django-backend/` | Django 4.2 + **Django Ninja** (not DRF), Python 3.12, `uv`, Ruff, pytest + factory-boy. Layered: routers → `HANDLERS`/`REPO` services → models. |
| **Frontend** | `src/web-ui/` | Next.js 16 App Router, React 19, TypeScript (strict), Tailwind 4, vitest + Playwright. Talks to the backend through a typed `APIClient` and **generated** types. |
| **Infra** | `infra/prod/app/` | Terraform. |


## Local setup

Backend:

```bash
cd src/django-backend
make bootstrap          # create the database
make seed               # load some test data
make dev                # run it
```

Frontend:

```bash
cd src/web-ui
make install
make dev
```

That's the whole stack. See `README.md` for the why behind the project.

## Day-to-day commands

Run these before you push — CI runs the same on every PR
(`.github/workflows/ci.yml`).

**Backend** (`src/django-backend/`):

```bash
make lint          # ruff check + ruff format --check
make test          # pytest
make install-deps  # if pytest can't be found
```

**Frontend** (`src/web-ui/`):

```bash
npm run lint   # eslint + tsc --noEmit
npm test       # vitest
```

**Terraform** (`infra/prod/app/`):

```bash
terraform fmt -check
terraform validate
```

## Two workflows that bite

### 1. The API contract — regenerate types

The frontend's types are **generated** from the backend's OpenAPI schema. If you
touch a Ninja **router** (`api/routers/*.py`) or **schema** (`api/schemas/*.py`)
— anything that changes a request/response shape, status code, or endpoint —
regenerate:

```bash
cd src/django-backend && make extract-openapi   # updates web-ui/backend-openapi.json
cd src/web-ui && npm run generate-types          # updates src/lib/api-types.ts
```

Commit **`backend-openapi.json`**. Do **not** commit `api-types.ts` — it's
gitignored and regenerated locally and in CI. An API change without a matching
`backend-openapi.json` means the frontend is reviewing against a stale contract.

### 2. Migrations

Any change to `apps/*/models.py` (new/altered field, model, constraint, `Meta`)
needs a matching migration under `apps/*/migrations/` in the same change — a
model change with no migration breaks `migrate` at boot. Watch ordering across
apps, and make data migrations that add a uniqueness constraint populate/dedupe
in the same step.

## Planning a larger change: OpenSpec

Small, self-contained fixes can go straight to a PR. For anything multi-step or
architectural, capture the plan first as an **OpenSpec change** under
`openspec/changes/<name>/`:

```
proposal.md   why + what changes (with BREAKING markers)
design.md     the design rationale
specs/        capability specs the change adds or alters
tasks.md      the ordered task breakdown
```

Validate before you lean on it:

```bash
openspec validate <name>
```

Phased work ships as stacked PRs that each reference the change and the section
of `tasks.md` they cover (see #66, #67 for the pattern). Longer design rationale
that isn't an OpenSpec change lives in `docs/` — see [`docs.md`](docs.md) for the
full documentation map.

## Branches, commits, and PRs

- **Branch per change.** Descriptive names (`add-follow-preferences-ui`) are
  preferred over generated ones.
- **Commits** reference the issue or PR they relate to (`Fix #61: …`,
  `… (#64)`). Keep the subject line a real summary.
- **Open a PR against `main`.** The
  [pull request template](.github/PULL_REQUEST_TEMPLATE.md) lays out the shape
  we use: what the change does, where it fits, what's deliberately out of scope,
  a test plan, and a **verification line** (test counts, `lint` clean,
  `openspec validate` clean). Good PR descriptions are a point of pride here —
  the diff says what changed; the description says *why* and *what you checked*.
- **CI must be green** before merge: backend lint + tests, web-ui build.

## For AI coding assistants

You're a first-class contributor here. A few repo-specific expectations:

- **Use the local skills.** Invoke **`nglspn-docs`** when writing or updating any
  documentation, and **`nglspn-code-review`** before proposing a change as ready.
- **Honor the two workflows above** — regenerate `backend-openapi.json` on API
  changes, add migrations on model changes. These are the most-forgotten steps.
- **Run `make lint` + `make test` (backend) and `npm run lint` (frontend)**
  before claiming a change is done, and report the result in the PR's
  verification line. Don't assert "tests pass" without having run them.
- **Plan non-trivial work as an OpenSpec change** before implementing.
- **Match the house voice** — Icelandic user-facing strings, the `HANDLERS`/`REPO`
  services layer, generated types over hand-rolled interfaces.
- End commit and PR trailers per `CLAUDE.md`.

## Questions

Open an issue or start a discussion. Bringing a carrot is better than bringing
nothing — small fixes and doc improvements are genuinely welcome.
