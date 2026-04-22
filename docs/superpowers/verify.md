# Dynamic Translations — Session State & Verification

Last updated: 2026-04-22

## Where we are

We are building **dynamic translations** for Naglasúpan. The design allows any logged-in user to edit translations inline, with changes propagating within seconds and no redeployment. The work is broken into 5 phases.

- **Phase 1 — Backend catalog + API + webhook:** ✅ Implemented (not yet smoke-tested end-to-end).
- **Phase 2 — Web-UI bilingual rendering (`next-intl` + locale routing):** ⏳ Not started. Next up.
- **Phase 3 — Authoring flow (MT generation + Django migrations + lint):** Pending.
- **Phase 4 — Inline edit UX (`<Translatable>`, pencil, popover, chips):** Pending.
- **Phase 5 — Editor worklist:** Pending.

## Artifacts

- **Design spec:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md`
- **Phase 1 plan:** `docs/superpowers/plans/2026-04-22-translations-backend.md`

Phases 2–5 will each get their own plan written at the start of the next session, using real Phase-1 code as context.

## What Phase 1 built

New Django app `apps.translations` with two models (`Translation`, `TranslationAudit`), a services layer following the existing `handler_interface` / `query_interface` / `django_impl` pattern (strict architectural rule: routers do not touch the ORM), a thin Django-Ninja router at `/api/i18n`, and a best-effort webhook that notifies the web-ui on edit.

### Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/i18n/{locale}` | — | Full non-retired catalog as `{key: text}`. |
| GET | `/api/i18n/{locale}/version` | — | Max `updated_at` as epoch int; 0 if empty. |
| PATCH | `/api/i18n/{locale}/{key}` | Bearer | Upsert; flips `is_machine_translated=False`; writes audit via save hook; fires revalidation webhook. |

### Relevant settings (added)

- `WEB_UI_REVALIDATE_URL` (env)
- `WEB_UI_REVALIDATE_SECRET` (env)

Unset by default = webhook is a no-op.

### Test state

- 484 tests pass across the full backend.
- `make lint` clean.
- OpenAPI regenerated (`src/web-ui/backend-openapi.json` updated in commit `mvxq`).

### Commits in Phase 1 (on top of the design+plan commit)

```
uwqv  feat(translations): scaffold app
wtuw  feat(translations): Translation model + migration
kxmv  feat(translations): TranslationAudit + automatic write on save
mrns  feat(translations): ninja schemas
zqkm  docs(translations): revise plan to use services/ handler+query layer
uszl  feat(translations): service interfaces (handler, query)
uytl  feat(translations): DjangoTranslationQuery
yoqy  feat(translations): revalidation webhook helper
plox  feat(translations): DjangoTranslationHandler.update_text
tymq  feat(translations): wire HANDLERS.translations / REPO.translations
truu  feat(translations): HTTP router wired to HANDLERS/REPO
xqku  feat(translations): admin registration (audit read-only)
mvxq  chore(translations): regen OpenAPI + lint clean
```

Pre-existing design + plan commits: `pttz` (design), `zqkm` (revised plan).

## Smoke test (run before starting Phase 2)

Two terminals.

### Terminal 1 — server (leave it running)

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1/src/django-backend
uv run python manage.py migrate
WEB_UI_REVALIDATE_URL=https://httpbin.org/post \
WEB_UI_REVALIDATE_SECRET=dev-secret \
uv run python manage.py runserver
```

### Terminal 2 — the checks

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1/src/django-backend
```

**1. Seed a row and capture a token** (one shell call — faster than the login flow):

```bash
TOKEN=$(uv run python manage.py shell -c "
from apps.translations.models import Translation
from apps.users.models import User
from api.auth.jwt import create_access_token

t, _ = Translation.objects.get_or_create(
    locale='is', key='nav.home',
    defaults={'text': 'Heim', 'source_hash': 'abc', 'is_machine_translated': True},
)
user, _ = User.objects.get_or_create(
    email='smoke@example.com',
    defaults={'kennitala': '0000000001', 'first_name': 'Smoke', 'last_name': 'Test', 'is_verified': True, 'is_active': True},
)
print(create_access_token(user.id))
" 2>/dev/null | tail -1)
echo "Token acquired: ${TOKEN:0:20}..."
```

**2. GET catalog — expect `{"nav.home":"Heim"}`:**

```bash
curl -s http://localhost:8000/api/i18n/is | jq .
```

**3. GET version — expect `{"version": <epoch>}`:**

```bash
curl -s http://localhost:8000/api/i18n/is/version | jq .
```

**4. PATCH without auth — expect `401`:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -X PATCH http://localhost:8000/api/i18n/is/nav.home \
  -H 'Content-Type: application/json' \
  -d '{"text":"Forsíða"}'
```

**5. PATCH with auth — expect 200 + updated row:**

```bash
curl -s -X PATCH http://localhost:8000/api/i18n/is/nav.home \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Forsíða"}' | jq .
```

**6. Confirm catalog reflects edit + MT flag flipped + audit written:**

```bash
curl -s http://localhost:8000/api/i18n/is | jq .
uv run python manage.py shell -c "
from apps.translations.models import Translation, TranslationAudit
t = Translation.objects.get(locale='is', key='nav.home')
print(f'text: {t.text}')
print(f'is_machine_translated: {t.is_machine_translated}')
print(f'updated_by: {t.updated_by.email if t.updated_by else None}')
print(f'audits: {TranslationAudit.objects.filter(translation=t).count()}')
"
```

Expect:
- `text: Forsíða`
- `is_machine_translated: False`
- `updated_by: smoke@example.com`
- `audits: 2` (one at seed, one at edit)

**7. Confirm webhook fired** — check Terminal 1's log; no `revalidate webhook failed` warning means the fire-and-forget succeeded. The target (httpbin.org) is real, so the call actually completes.

## Known open items heading into Phase 2

- The smoke test above has not yet been run by a human. If anything fails, come back with the failing command + output and we fix before planning Phase 2.
- `Translation.source_hash` is stored as an empty string for rows created via PATCH. That's intentional — it's backfilled by the migration generator in Phase 3.
- No `SystemUser` for MT seed attribution yet. Phase 3 adds it.

## How to kick off the next session

Open a new Claude Code session in this project, attach this file, and say something like:

> Read `docs/superpowers/verify.md` and let's start Phase 2 — web-ui bilingual rendering with `next-intl` and locale routing.

I'll:
1. Confirm Phase 1 smoke-tested cleanly (or fix if not).
2. Invoke `superpowers:writing-plans` to produce the Phase 2 plan (consuming the Phase 1 endpoints we built).
3. Resume the subagent-driven execution flow.
