# Dynamic Translations — Session State & Verification

Last updated: 2026-04-22 (end of Phase 3)

## Where we are

Building **dynamic translations** for Naglasúpan. 5-phase rollout:

- **Phase 1 — Backend catalog + API + webhook:** ✅ Implemented and smoke-tested (see §"Phase 1 smoke test" below if you need to reprove it).
- **Phase 2 — Web-UI bilingual rendering (`next-intl` + locale routing):** ✅ Implemented and smoke-tested end-to-end (`/` → Icelandic, `/en` → English, live revalidation via `/api/revalidate-i18n`, locale switcher, `hreflang`). Playwright `e2e/i18n.spec.ts` — 3/3 pass.
- **Phase 3 — Authoring flow (MT generator + Django migrations + lint):** ✅ Implemented. 549 Django tests pass. `make ci` green. One manual follow-up pending: the DeepL end-to-end smoke (needs a real `DEEPL_AUTH_KEY`) was not yet run with a real key.
- **Phase 4 — Inline edit UX (`<Translatable>`, pencil, popover, chips, history):** ⏳ **NEXT UP.** No plan written yet.
- **Phase 5 — Editor worklist:** Pending.

## Artifacts

- **Design spec:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md`
- **Phase 1 plan:** `docs/superpowers/plans/2026-04-22-translations-backend.md`
- **Phase 2 plan:** `docs/superpowers/plans/2026-04-22-translations-web-ui.md`
- **Phase 3 plan:** `docs/superpowers/plans/2026-04-22-translations-authoring.md`
- **Phase 4 plan:** not yet written — produce it at the start of the next session.

## What Phase 2 built (for Phase 4 context)

- All routes moved under `src/web-ui/src/app/[locale]/`.
- `next-intl` v4.9.1 with `localePrefix: "as-needed"`. Default locale `is`, second locale `en`.
- `src/web-ui/src/i18n/{config,routing,navigation,request}.ts` — routing + `NextIntlClientProvider` wiring.
- `src/web-ui/src/lib/i18n/catalog.ts` — server-only `fetchCatalog(locale)` via `unstable_cache` tagged `i18n:<locale>`.
- `src/web-ui/src/middleware.ts` — `next-intl` middleware (Next 16 emits a deprecation warning: `middleware` is slated to become `proxy`; still functional).
- `src/web-ui/src/components/LocaleSwitcher.tsx` + mount in `Navigation.tsx`.
- `src/web-ui/src/app/api/revalidate-i18n/route.ts` — `X-Revalidate-Secret` header + `revalidateTag(tag, "max")` (Next 16 signature).
- `src/web-ui/src/messages/en.json` — English source of truth (Nav + Footer keys only in Phase 2).
- Icelandic rows for Nav + Footer seeded by `apps/translations/migrations/0003_seed_phase2_ui_chrome.py`.
- `Navigation.tsx`, `UserMenu.tsx`, `Footer.tsx` use `useTranslations(...)` + `Link`/`usePathname` from `@/i18n/navigation`. All other pages still have hardcoded strings — **Phase 4 sweeps those**.

## What Phase 3 built (for Phase 4 context)

- `apps/translations/generators/` — `flatten.py`, `hashing.py`, `snapshot.py`, `diff.py`, `translator.py` (with `DeepLTranslator` + `StubTranslator`), `migration_writer.py`. Full unit test coverage.
- `apps/translations/management/commands/generate_translations.py` — Django management command that diffs, translates, writes a migration. 5 end-to-end tests covering added / retranslated / hash-bumped / retired / no-op.
- `apps/translations/generators/state/en-snapshot.json` — committed snapshot, seeded from current `en.json`.
- **`make translate-new-keys`** (from `src/django-backend/`) — the developer-run generator. Requires `DEEPL_AUTH_KEY` in env.
- **`make lint-translations`** — CI-safe snapshot-drift check (uses `StubTranslator`, no DeepL needed).
- `src/web-ui/scripts/lint-i18n.mjs` — verifies every `t("key")` resolves in `en.json`. Wired into `npm run lint`.
- Root `Makefile` — `make ci` gates backend lint + translations drift + web-ui lint + backend tests.
- `CLAUDE.md` has a `### Translations Workflow` section for developers.

## How to start the next session

Open a new Claude Code session in this project and say something like:

> Read `docs/superpowers/verify.md` and let's start Phase 4 — the inline edit UX.

The assistant should:
1. **Confirm state:** run `make ci` (expect green) and optionally re-run the Phase 1 or Phase 2 smoke test below if anything feels off.
2. **(Optional) Do the outstanding DeepL smoke** if it hasn't been done: export `DEEPL_AUTH_KEY`, add one throwaway key to `en.json`, run `cd src/django-backend && make translate-new-keys`, inspect the generated migration for a plausible Icelandic translation, then revert.
3. **Invoke `superpowers:writing-plans`** to produce the Phase 4 plan, consuming the Phase 2 `NextIntlClientProvider` + PATCH endpoint + revalidate webhook.
4. **Offer execution choice** (subagent-driven vs inline) and run.

### Phase 4 scope reminder (from design spec §Edit UX)

- A "Edit translations" toggle in the user menu, cookie-persisted.
- Global `<Translatable i18n-key="...">` wrapper → pencil-on-hover (absolutely positioned, no reflow).
- Click → inline popover with: Icelandic textarea, English reference, ICU placeholder chips (non-editable), last-N history, save/cancel/revert.
- Save path: PATCH to `/api/i18n/{locale}/{key}` → optimistic update to `NextIntlClientProvider` (editor sees change instantly) → Django webhook fires → other users see the change on next render.
- Concurrency: last-write-wins, with "edited N seconds ago by X" warning if `updated_at` changed since popover open.
- Missing-translation fallback already handled by Phase 2's `deepMerge` in `request.ts`; edit mode marks fallback strings visually.
- Also: Phase 4 is the right time to sweep hardcoded strings on the other pages to `t()` and flip on the "no hardcoded JSX strings" lint rule (deferred from Phase 3).

## Phase 1 smoke test (only if you need to re-prove it)

Two terminals. The Django server must be started with the webhook env vars for the PATCH → web-ui revalidation round-trip to fire automatically; without them the webhook is a no-op.

### Terminal 1 — server

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1/src/django-backend
uv run python manage.py migrate
WEB_UI_REVALIDATE_URL=http://localhost:3000/api/revalidate-i18n \
WEB_UI_REVALIDATE_SECRET=dev-secret \
uv run python manage.py runserver 0.0.0.0:8001
```

### Terminal 2 — web-ui

```bash
cd /Users/alex/Work/codalens/nglspn/nglspn-w1/src/web-ui
API_URL=http://localhost:8001 \
NEXT_PUBLIC_API_URL=http://localhost:8001 \
WEB_UI_REVALIDATE_SECRET=dev-secret \
npm run dev
```

### Terminal 3 — verification

```bash
# Acquire a token
cd /Users/alex/Work/codalens/nglspn/nglspn-w1/src/django-backend
TOKEN=$(uv run python manage.py shell -c "
from apps.users.models import User
from api.auth.jwt import create_access_token
user, _ = User.objects.get_or_create(
    email='smoke@example.com',
    defaults={'kennitala': '0000000001', 'first_name': 'Smoke', 'last_name': 'Test', 'is_verified': True, 'is_active': True},
)
print(create_access_token(user.id))
" 2>/dev/null | tail -1)

# Bilingual render check
curl -s http://localhost:3000/    | grep -oE '>(Verkefni|Keppnir)<' | sort -u
curl -s http://localhost:3000/en  | grep -oE '>(Projects|Competitions)<' | sort -u

# Live edit → webhook → revalidation
curl -s -X PATCH http://localhost:8001/api/i18n/is/nav.projects \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"VERKVERK"}'
sleep 1
curl -s http://localhost:3000/    | grep -oE '>VERKVERK<'
curl -s -X PATCH http://localhost:8001/api/i18n/is/nav.projects \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"Verkefni"}'   # reset
```

Expected: Icelandic labels at `/`, English labels at `/en`, `VERKVERK` rendered after PATCH, returns to `Verkefni` after the reset.

## Known open items heading into Phase 4

- **DeepL smoke not yet run with a real key.** Either do it first (task 10 of Phase 3 plan) or let it happen naturally the first time someone adds a new key.
- **`revalidateTag(tag, "max")`** — the `"max"` second arg is a Next 16 adaptation made by the Phase 2 implementer. Works end-to-end in dev; re-verify on a prod deploy.
- **`middleware.ts` vs `proxy.ts`** — Next 16 deprecation warning. Cosmetic for now; rename when the replacement path stabilizes.
- **Hardcoded strings on non-chrome pages** — Phase 4 sweep.
