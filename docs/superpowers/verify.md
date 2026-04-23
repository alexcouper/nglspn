# Dynamic Translations — Session State & Verification

Last updated: 2026-04-23 (end of Phase 4)

## Where we are

Building **dynamic translations** for Naglasúpan. 5-phase rollout:

- **Phase 1 — Backend catalog + API + webhook:** ✅ Implemented and smoke-tested (see §"Phase 1 smoke test" below if you need to reprove it).
- **Phase 2 — Web-UI bilingual rendering (`next-intl` + locale routing):** ✅ Implemented and smoke-tested end-to-end. Playwright `e2e/i18n.spec.ts` — 3/3 pass.
- **Phase 3 — Authoring flow (MT generator + Django migrations + lint):** ✅ Implemented. `make ci` green.
- **Phase 4 — Inline edit UX (`<Translatable>`, pencil, popover, chips, history):** ✅ Implemented. `make ci` green (557 backend tests + lint + i18n drift). Plan: `docs/superpowers/plans/2026-04-23-translations-inline-edit.md`. **Not yet executed:** the Playwright e2e (`e2e/i18n-edit.spec.ts`) — needs both servers + a logged-in test user; run manually before shipping. **Deferred:** the hardcoded-string sweep on non-chrome pages and the `no-hardcoded-jsx-strings` ESLint rule are both gated on the MT-provider decision (DeepL paused).
- **Phase 5 — Editor worklist:** Pending.

## Artifacts

- **Design spec:** `docs/superpowers/specs/2026-04-22-dynamic-translations-design.md`
- **Phase 1 plan:** `docs/superpowers/plans/2026-04-22-translations-backend.md`
- **Phase 2 plan:** `docs/superpowers/plans/2026-04-22-translations-web-ui.md`
- **Phase 3 plan:** `docs/superpowers/plans/2026-04-22-translations-authoring.md`
- **Phase 4 plan:** `docs/superpowers/plans/2026-04-23-translations-inline-edit.md`

---

## Full feature inventory (Phases 1–4)

### Phase 1 — Backend catalog + API + webhook

- `Translation` table (`locale`, `key`, `text`, `source_hash`, `updated_by`, `updated_at`, `is_machine_translated`, `retired`) with `(locale, key)` uniqueness.
- `TranslationAudit` table (full before/after history, `changed_by`, `changed_at`).
- `Translation.save()` hook auto-writes an audit row on every text change.
- `GET /api/i18n/{locale}` — full non-retired catalog as `{key: text}`.
- `GET /api/i18n/{locale}/version` — `max(updated_at)` as epoch int (cheap probe).
- `PATCH /api/i18n/{locale}/{key}` — auth-required edit; flips `is_machine_translated` to False; upserts; fires webhook.
- Service-layer split: `TranslationQueryInterface` (read) and `TranslationHandlerInterface` (write).
- `notify_web_ui(locale)` webhook → POSTs to web-ui's revalidation endpoint with shared-secret header; failures don't fail the edit.

### Phase 2 — Web-UI bilingual rendering

- All routes moved under `src/web-ui/src/app/[locale]/`.
- `next-intl` v4.9.1 with `localePrefix: "as-needed"`. Default `is`, second `en`.
- `src/web-ui/src/i18n/{config,routing,navigation,request}.ts` — locale config + routing + `NextIntlClientProvider` wiring.
- `src/web-ui/src/lib/i18n/catalog.ts` — server-only `fetchCatalog(locale)` via `unstable_cache` tagged `i18n:<locale>` (60s safety revalidate).
- `next-intl` middleware (Accept-Language detection + cookie).
- `<LocaleSwitcher>` in nav (toggles `/` ↔ `/en`, sets `NEXT_LOCALE` cookie).
- `src/web-ui/src/app/api/revalidate-i18n/route.ts` — `X-Revalidate-Secret` header + `revalidateTag(tag, "max")` (Next 16 signature).
- `src/web-ui/src/messages/en.json` — English source of truth in code.
- `apps/translations/migrations/0003_seed_phase2_ui_chrome.py` — Icelandic for Nav + Footer keys.
- Deep-merge fallback in `i18n/request.ts` so missing Icelandic keys never break render.
- `<LocaleHtmlLang>` sets `<html lang>` per locale.
- `hreflang` link tags on every page for SEO.
- Playwright `e2e/i18n.spec.ts` — `/` Icelandic, `/en` English, locale-switcher round-trip.

### Phase 3 — Authoring flow (developer loop)

- `apps/translations/generators/` — composable pieces:
  - `flatten.py` — `en.json` nested → dotted-key flat map.
  - `hashing.py` — stable 16-char `source_hash(text)`.
  - `snapshot.py` — read/write the committed `en-snapshot.json`.
  - `diff.py` — added / changed / removed / hash-bump-only categorization.
  - `translator.py` — `TranslatorProtocol` + `DeepLTranslator` + `StubTranslator`.
  - `migration_writer.py` — emits idempotent `update_or_create` Django data migrations.
- `manage.py generate_translations` — full pipeline (diff → translate → write migration). 5 e2e test scenarios.
- Snapshot state file `apps/translations/generators/state/en-snapshot.json` (committed).
- `make translate-new-keys` — developer-run pre-push command (needs `DEEPL_AUTH_KEY`).
- `make lint-translations` — CI-safe drift check (uses StubTranslator, no DeepL needed).
- `src/web-ui/scripts/lint-i18n.mjs` — every `t("key")` call (resolves through any `useTranslations("ns")`) must exist in `en.json`. Wired into `npm run lint`.
- Root `Makefile` — `make ci` gates backend lint + translations drift + web-ui lint + backend tests.
- `CLAUDE.md` has a `### Translations Workflow` section for developers.
- Re-translate-vs-bump-only rule for changed source: keys still flagged `is_machine_translated=True` get re-translated; human-edited keys only get `source_hash` bumped.

### Phase 4 — Inline edit UX

**Backend**
- `GET /api/i18n/{locale}/{key}` — returns current text + `updated_at` + last 10 audit entries (with display name); empty payload for missing rows.
- `TranslationDetailResponse` + `TranslationAuditEntryResponse` schemas; OpenAPI + TS types regenerated.
- PATCH-contract regression test (locks `updated_at` in response).
- `apps/translations/migrations/0004_seed_phase4_edit_ui.py` — hand-authored Icelandic for all 14 new edit-mode UI keys.
- `en-snapshot.json` updated (lint-translations green without DeepL).

**Web-UI infra**
- `src/web-ui/src/lib/i18n/edit-mode-cookie.ts` + `.client.ts` — `nglspn-edit-mode` cookie helpers (server read + client read/write).
- `src/web-ui/src/lib/i18n/api.ts` — typed `getTranslationDetail(locale, key)` + `patchTranslation(locale, key, text, bearerToken)`.
- `src/web-ui/src/lib/i18n/messages.ts` — server helper `loadMessages(locale)` returning merged + locale-only + English catalogs separately.
- `src/web-ui/src/contexts/editable-messages.tsx` — `EditableMessagesProvider` that lifts messages into client state and exposes:
  - `editMode`
  - `applyOverride(key, text)` — optimistic update, editor sees change instantly.
  - `isFallback(key)` — true when the locale catalog has no row for this key.
  - `readEnglish(key)` — English source for the popover reference.
- Layout rewired to read cookie + wrap children in `EditableMessagesProvider`.

**Edit UI**
- `<EditModeToggle>` — menu item in `UserMenu` that flips the cookie + `router.refresh()`. Label reads "Edit translations" / "Editing translations: on".
- `<Translatable tKey="...">` wrapper:
  - Zero overhead when edit mode is off (renders children inline).
  - When on: pencil overlay on hover (absolutely positioned, no reflow), `data-i18n-key` attribute, dotted-amber underline marker for English-fallback strings.
- `<TranslationPopover>` — portal-rendered, anchored to pencil:
  - Single round-trip on open: text + `updated_at` + history.
  - English reference block (hidden when locale === "en").
  - Save / Cancel buttons; Esc and outside-click close.
  - Bearer-token PATCH; on success calls `applyOverride` for instant render; Django webhook propagates to other users within seconds.
- `<ChipsEditor>` (`TranslationChips.tsx`):
  - `contentEditable` div that renders `{name}` / `{count, plural, ...}` placeholders as atomic non-editable amber chips.
  - `validateAgainstReference(en, draft)` — checks all reference placeholders are still present.
  - Save disabled + amber warning when chips are missing.
- History disclosure inside popover — last N entries (who, when, new text), each with "Revert to this" that loads the old text into the draft.
- Relative-time formatter (`12s ago`, `5m ago`, `2h ago`, …).
- Concurrency check on save:
  - Re-fetches detail before PATCH; if `updated_at` moved, shows non-blocking warning `"Edited Ns ago by X. Save anyway?"` with explicit confirm (last-write-wins).
  - Audit log makes any mis-overwrite recoverable from the same popover.
- Chrome wrapping: every chrome `t("...")` call in Navigation (desktop + mobile), Footer, and UserMenu wrapped with `<Translatable>`.
- `e2e/i18n-edit.spec.ts` — Playwright spec for the edit happy path (not yet executed).

### Explicitly deferred

- DeepL smoke test with a real key (paused — provider may change).
- Sweep of hardcoded JSX strings on non-chrome pages + a `no-hardcoded-jsx-strings` ESLint rule (also gated on the MT-provider decision).
- Phase 5 — editor worklist (admin view of keys with `source_hash` drift or still-MT'd).
- Long-form / markdown-preview popover layout.
- Per-user permission gate beyond "logged-in".

---

## Phase 4 scope reminder (from design spec §Edit UX)

- A "Edit translations" toggle in the user menu, cookie-persisted.
- Global `<Translatable i18n-key="...">` wrapper → pencil-on-hover (absolutely positioned, no reflow).
- Click → inline popover with: Icelandic textarea, English reference, ICU placeholder chips (non-editable), last-N history, save/cancel/revert.
- Save path: PATCH to `/api/i18n/{locale}/{key}` → optimistic update to `NextIntlClientProvider` → Django webhook fires → other users see the change on next render.
- Concurrency: last-write-wins, with "edited N seconds ago by X" warning if `updated_at` changed since popover open.
- Missing-translation fallback handled by Phase 2's `deepMerge` in `request.ts`; edit mode marks fallback strings visually.

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

## Known open items

- **DeepL smoke not yet run with a real key.** Paused — provider may be swapped. Do it (or its replacement) before shipping.
- **`revalidateTag(tag, "max")`** — the `"max"` second arg is a Next 16 adaptation. Works end-to-end in dev; re-verify on a prod deploy.
- **`middleware.ts` vs `proxy.ts`** — Next 16 deprecation warning. Cosmetic; rename when the replacement path stabilizes.
- **Hardcoded strings on non-chrome pages** — deferred sweep; depends on MT-provider decision.
- **Playwright `e2e/i18n-edit.spec.ts`** — written but not executed. Run manually before shipping.
