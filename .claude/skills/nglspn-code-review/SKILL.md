---
name: nglspn-code-review
description: >-
  Senior-engineer code review for the Naglasúpan (nglspn) repo — Django Ninja
  backend + Next.js/React frontend + Terraform. Use this whenever the user asks
  you to review changes, review a branch or PR, "look over" or "sanity-check"
  code before merging, or asks "what would a senior engineer flag here?" in this
  repository. Trigger it even when the user doesn't say the word "review" — if
  they've finished a change and want a second pair of eyes, or mention checking a
  diff/PR against main, use this skill. It knows the repo's house gotchas
  (OpenAPI type regeneration, migrations, the HANDLERS/REPO services layer,
  X-Forwarded-For/IP trust, kennitala PII, auth transient-failure handling) that
  a generic review misses.
---

# Naglasúpan Code Review

You are doing a senior-engineer code review of a change in this repository.
Your job is to catch the things that actually bite this codebase — real bugs,
violations of its architecture, and the specific foot-guns this team has hit
before — while staying quiet about noise a linter or the author would catch on
their own.

**The bar:** every finding must be something a thoughtful senior engineer on
*this* project would raise in a PR. If you're not fairly sure it's real and
matters, leave it out. A short review of true issues beats a long one padded
with maybes.

## The repo in one breath

- **Backend** `src/django-backend/` — Django 4.2 + **Django Ninja** (not DRF),
  Python 3.12, `uv`, Ruff, pytest + factory-boy. Layered architecture: routers →
  `HANDLERS`/`REPO` services → models.
- **Frontend** `src/web-ui/` — Next.js 16 App Router, React 19, TypeScript
  (strict), Tailwind 4, vitest + Playwright. Talks to the backend through a typed
  `APIClient` and **generated** types.
- **Infra** `infra/prod/app/` — Terraform.
- The product is Icelandic; user-facing strings are in Icelandic, the domain is
  `naglasupan.is`.

## Workflow

### 1. Establish what changed

Default to **the current branch against `main`**. If the user named a PR number,
review that instead.

```bash
# Branch vs main (default) — committed + uncommitted
git fetch origin main --quiet 2>/dev/null
git diff origin/main...HEAD            # committed changes on the branch
git diff                              # unstaged working-tree changes
git status --short                    # what's modified/untracked
```

```bash
# A specific PR (only if the user gave a number)
gh pr view <N> --json title,body,files
gh pr diff <N>
```

Read the actual diff, not just file names. Pull surrounding context for changed
files when a finding depends on it, but anchor every finding to a line the change
*touched* — issues on untouched lines are out of scope unless the change made
them newly wrong.

### 2. Understand the intent

Before judging, know what the change is trying to do. Read the PR/commit
messages and the diff. A change that looks wrong in isolation is often correct
for its purpose — and vice versa. Hold the intent in mind as you review.

### 3. Review against the house checklist

Walk the relevant sections below. These are ordered by how often they draw real
blood in this repo, not alphabetically. Skip sections the diff doesn't touch.

#### A. The contract: OpenAPI ↔ TypeScript (check on EVERY backend API change)

This is the single most-forgotten step here. The frontend's types are
**generated** from the backend's OpenAPI schema.

- If the change touched a Ninja **router** (`src/django-backend/api/routers/*.py`)
  or **schema** (`src/django-backend/api/schemas/*.py`) — anything that alters a
  request/response shape, status code, or endpoint — then
  `src/web-ui/backend-openapi.json` **must be regenerated and committed in the
  same change** (`make extract-openapi`). If the API changed but that file didn't,
  flag it: the frontend is now reviewing against a stale contract.
- Do **not** expect `src/web-ui/src/lib/api-types.ts` in the diff — it is
  **gitignored** and regenerated locally/in CI. Its absence is correct; only
  `backend-openapi.json` is committed.

#### B. Migrations (check on every model change)

- If a `apps/*/models.py` changed (new field, altered field, new model,
  constraint, `Meta`), there must be a matching migration under
  `apps/*/migrations/`. A model change with no migration is a blocker — it breaks
  `migrate` at boot.
- Watch for **ordering across apps** (a migration depending on another app's
  not-yet-applied migration) and **non-atomic multi-step data migrations**. Slug
  backfills and uniqueness changes have bitten this repo before — a data migration
  that adds a unique constraint must populate/dedupe in the same logical step.

#### C. Backend architecture & conventions

- **Layering.** Writes go through `HANDLERS.<domain>.…`, reads through
  `REPO.<domain>.…` (both imported `from services import HANDLERS, REPO`). Routers
  orchestrate; they shouldn't run raw ORM queries or business logic inline. A new
  endpoint reaching straight into `Model.objects` instead of the services layer is
  an architecture smell worth flagging.
- **Router idioms.** Endpoints declare `auth=auth`, list their status codes in the
  decorator's `response={...}`, and return error tuples like
  `return 404, {"detail": "..."}` (signature `tuple[int, Model] | tuple[int,
  dict[str, str]]`). Authorization uses the shared `_helpers`
  (`require_full_edit`, `resolve_visible_project_or_404`, `get_optional_user`).
  Domain errors are raised as exceptions in services and caught in the router. A
  new endpoint that invents its own auth/error pattern instead of these helpers
  deserves a comment.
- **Authorization holes.** For any endpoint that reads or mutates a project's
  data, confirm it actually checks the caller may see/edit that object — missing
  ownership/visibility checks are the highest-value bug class. Cross-check that an
  object fetched by id is verified to belong to the project in the URL (the
  `_get_..._in_project` pattern).

#### D. Security & privacy (highest-signal area — real precedent in PR #19)

- **Never trust a spoofable client IP.** Any new code reading
  `HTTP_X_FORWARDED_FOR` / `REMOTE_ADDR` for a security decision (rate limiting,
  admin gating) must respect `NUM_TRUSTED_PROXIES` and count from the right —
  taking the leftmost `X-Forwarded-For` entry, or trusting it without the proxy
  count, lets an attacker forge it. This has been a recurring foot-gun.
- **PII: kennitala (Icelandic national ID).** It must never appear in an API
  response for *another* user. If a schema or endpoint exposes `kennitala`,
  confirm it's only ever the caller's own.
- **`ALLOWED_HOSTS`, CSP, secrets.** No hardcoded secrets; env-driven config via
  `os.getenv(...)`. CSP/domain values must be runtime/env-aware, not baked at
  build time. No hardcoded `naglasupan.com` (the domain is `.is`).
- **Heavy/external work is async.** Email and other slow side-effects go through
  the task runner via `HANDLERS.email`, never inline in the request path.

#### E. Frontend: auth, types, resilience

- **Transient vs. auth failure.** The `APIClient` distinguishes `"refreshed" |
  "invalid" | "transient"` outcomes for a reason: on a transient/5xx/network
  error it must **not** clear tokens or treat the user as logged out, and pages
  must **not** cache empty/error responses as if they were real data. This exact
  bug class has regressed repeatedly (e.g. #61/#64) — scrutinize any change to
  token refresh, logout, or error handling here.
- **Use generated types.** API response/request shapes come from
  `components["schemas"][...]` in the generated `api-types.ts`. Hand-rolled
  interfaces that duplicate an API shape will silently drift — flag them.
- **Client/server boundary.** Components using hooks/state/browser APIs need
  `"use client"`. Errors from the client surface as `ApiRequestError` (has
  `.status`/`.body`) — handle by narrowing on that, not string matching.
- **Image uploads** have been buggy here: check dimension/metadata fallbacks
  (don't assume width/height is present) and avoid relying on blob URLs for
  client-side dimensions.

#### F. Tests

New behavior should come with tests — pytest + factory-boy on the backend,
vitest on the frontend. "Missing tests for these" is the most common quality gap
when anyone reviews here. Flag genuinely untested new logic, but don't demand
tests for trivial or purely declarative changes.

#### G. Terraform (if `infra/` changed)

Expect `terraform fmt` clean and no plaintext secrets in `.tf`. Flag obvious
state/provider mistakes, but defer formatting to `fmt -check`.

### 4. Filter with senior judgment

Drop anything in this list before writing it up — raising these erodes trust:

- Issues a tool already catches: Ruff/ESLint/`tsc`/formatting/imports/type
  errors, failing builds. CI runs these; assume it will.
- Pre-existing issues on lines the change didn't touch.
- Nitpicks a senior engineer would let slide (naming taste, micro-style).
- Changes that are clearly intentional and central to the stated purpose.
- The gitignored `api-types.ts` being absent (see §A — that's correct).
- Speculative "what if" concerns you can't tie to a concrete failure.

For each surviving finding, sanity-check: *can I point at the line and explain
the concrete failure or the specific convention it breaks?* If not, cut it.

### 5. Write the report

Output to the conversation (don't post to GitHub unless the user explicitly asks).
Group by severity. Be concrete and cite `path:line`. Keep it tight.

```
## Code review — <branch or PR>

<One-sentence summary of what the change does.>

### Blockers
1. <What's wrong and the concrete consequence> — `path:line`
   <Why it matters here; cite the convention/precedent, e.g. "API changed but
   backend-openapi.json not regenerated — frontend contract is now stale.">

### Important
2. ...

### Minor / nits
3. ...

### Verdict
<Ready to merge / Address blockers first / etc. — one or two sentences.>
```

Rules for the report:

- If you found nothing worth raising, say so plainly: "No issues found — checked
  API/type sync, migrations, the services layer, auth/security, and tests." Don't
  invent filler.
- **Severity** reflects impact on *this* codebase: a forgotten OpenAPI regen, a
  missing migration, an auth/visibility hole, or an IP-trust/PII leak is a
  **Blocker**. Convention drift and missing tests are usually **Important**.
  Taste is **Minor**.
- Lead with the consequence, not the abstraction. "Anyone can bypass the rate
  limit by setting X-Forwarded-For" beats "improper header handling."
- No performative praise. State findings; the value is in being right, not nice.
