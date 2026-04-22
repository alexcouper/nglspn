# Dynamic Translations Design

**Date:** 2026-04-22
**Status:** Design — not yet implemented

## Problem

Naglasúpan should support Icelandic as the default language, with English as a secondary locale. Because the primary author's Icelandic is not strong enough to catch machine-translation errors, the platform must lean on its high-trust user base: any logged-in user should be able to correct translations inline, anywhere they appear, and corrections should propagate to other users within seconds — without requiring a redeployment.

## Goals

- Icelandic is the default locale; English is a secondary locale under `/en/...`.
- Every piece of system-authored visible text on the site is editable inline by logged-in users.
- Edits land visibly for other users within a few seconds (not a minute; not a deploy).
- Every edit is auditable (who, when, previous value, current value) with a revert path.
- The developer workflow for adding/changing English strings is low-friction and cannot silently drift from what's in the database.
- Local developers can run the project with realistic Icelandic text without talking to a machine-translation API.

## Non-goals (v1)

- Translation of user-generated content (UGC): project descriptions, discussion posts, etc. The key scheme is designed so this can be added later without a schema change, but it is not part of v1.
- RTL locales.
- Glossary/term-consistency enforcement, translation memory, or approval workflows.
- Translating URL slugs or route segments themselves.
- Per-user server-stored locale preference (cookie is sufficient for v1).

## High-level shape

- **Django owns a unified translation catalog** in two tables: `Translation` and `TranslationAudit`.
- **Web-UI uses `next-intl`** on top of the catalog. The English source catalog lives in the repo (`en.json`-style); the Icelandic catalog lives in the database.
- **Delivery:** server components fetch the full catalog per locale through `unstable_cache` tagged `i18n:<locale>`. On edit, Django webhooks the web-ui to call `revalidateTag`, which causes the next render to fetch the fresh catalog.
- **Edit UX:** a global "edit translations" toggle reveals a pencil-on-hover on every translated string; clicking opens an inline popover with the English reference, placeholder chips, and edit/save/history controls.
- **Authoring flow:** developers edit English strings in the codebase; a helper command (run locally, pre-push) generates a Django data migration containing machine-translated Icelandic rows for any new or changed keys. The migration is committed in the same PR as the code change.

## Data model

### `Translation`

| field | notes |
|---|---|
| `id` | pk |
| `locale` | e.g. `is`, `en`. Indexed. |
| `key` | dotted string, e.g. `home.hero.title`, `tag.42.name`. Indexed. |
| `text` | TEXT, no length cap. |
| `source_hash` | hash of the English source text at the moment this translation was written. Used to flag "source changed — this translation may be stale." For `en` rows this equals a hash of the row's own text. |
| `updated_by` | FK to user who last edited (nullable — seeded rows have null). |
| `updated_at` | timestamp. |
| `is_machine_translated` | bool. True on seed; flips to False once a human edits the row and stays False thereafter. |
| `retired` | bool. Set True by the sync step when a key disappears from the English source. Rows are never deleted — the audit trail references them. |

Uniqueness: `(locale, key)`.

### `TranslationAudit`

| field | notes |
|---|---|
| `id` | pk |
| `translation_id` | FK to Translation (not CASCADE). |
| `locale`, `key` | denormalized so audit survives translation deletion. |
| `old_text`, `new_text` | before/after. |
| `changed_by` | FK to user. Non-null for human edits; a system pseudo-user is used for MT seeds. |
| `changed_at` | timestamp. |

### Key naming convention

- UI chrome: `<area>.<component>.<purpose>` — e.g. `nav.profile.link`, `form.signup.submit`.
- Static pages: `page.<slug>.<block>` — e.g. `page.about.intro`.
- Email: `email.<template>.<part>` — e.g. `email.welcome.subject`.
- Domain-record fields (reserved for future UGC extension): `<model>.<id>.<field>` — e.g. `tag.42.name`, `project.17.description`.

## Delivery pipeline

### Django endpoints

- `GET /api/i18n/<locale>` — returns the full catalog for a locale as `{ key: text, ... }`. Excludes `retired` rows. Single indexed query, no auth required (public read).
- `GET /api/i18n/<locale>/version` — returns `{ version: <int-or-hash> }`. Version is the max `updated_at` (or a monotonic counter). Cheap probe; not required for correctness, useful for diagnostics.
- `PATCH /api/i18n/<locale>/<key>` — edit endpoint. Requires logged-in user. Writes the row, writes an audit entry, fires the revalidation webhook.

### Web-UI caching

```ts
// pseudocode
const getMessages = unstable_cache(
  async (locale: Locale) =>
    fetch(`${DJANGO}/api/i18n/${locale}`).then((r) => r.json()),
  ['i18n'],
  { tags: [`i18n:${locale}`], revalidate: 60 },
);
```

The 60-second `revalidate` is a safety net in case a webhook is dropped; correctness does not depend on it.

The catalog is passed into `next-intl`'s provider at the root layout. Server components render translations directly from the payload; client components pull from the same provider via context, hydrated from the server-rendered catalog. No client-side refetch on initial load.

### Invalidation

On successful edit, Django posts to `POST https://<web-ui>/api/revalidate-i18n` with body `{ locale: 'is' }` and a shared-secret header. The route calls `revalidateTag('i18n:' + locale)`. The next server render fetches a fresh catalog.

For the editor themselves, the edit UI optimistically updates the in-memory provider so they see their own change instantly. Other users see the change on their next navigation, which on an active site is typically a few seconds later.

### Payload size note (fast follow)

Shipping the full catalog to every client is fine at v1 scale but will eventually bloat the client bundle. Fast follow (not v1): split messages into "server-only" (used only by server components, never sent to browser) and "client" (hydrated into the browser). `next-intl` supports this pattern directly.

## Edit UX

### Trust model

Any logged-in user can edit any translation. This matches the platform's stated high-trust nature. Mitigations: full audit trail, one-click revert from history, and the existing ability to deactivate a user account. If abuse emerges, the trust model can be tightened (e.g. add a `can_edit_translations` flag) without schema change.

### Entering edit mode

- A "Edit translations" toggle lives in the user menu. It is off by default.
- The toggle state is stored in a cookie so it persists per-session.
- When on, every translated string is wrapped in a small client component (`<Translatable i18n-key="...">...</Translatable>`) that exposes a pencil icon on hover. The icon is absolutely positioned and does not reflow layout.
- When edit mode is off, the wrapper renders as a plain text node — zero runtime overhead for normal visitors.

### Edit flow

1. Click pencil → inline popover opens at the string's position.
2. Popover shows: the current Icelandic text in a textarea, the English original below as reference, and last-N history entries collapsed.
3. Interpolation placeholders (e.g. `{name}`) are rendered in the textarea as non-editable chips. Deleting or mangling a chip produces a warning and disables save.
4. Save → PATCH to Django → optimistic update to local provider (user sees edit immediately) → Django webhook revalidates the Next.js cache for other users.
5. Cancel or Esc closes without changes.

### History and revert

Each popover has a "history" disclosure showing the last N edits (who, when, previous text). Clicking an old entry offers "revert to this," which writes a new edit whose `new_text` matches the chosen historic entry.

### Concurrency

Last-write-wins. If the current row's `updated_at` has changed since the popover was opened, a "this was edited N seconds ago by X — review first" warning appears before save. The audit log makes any mis-overwrite recoverable.

### Long-form text

For long strings (paragraphs of prose), the popover grows to a wider layout with a live markdown preview. No WYSIWYG in v1.

### Missing-translation fallback

- If a key has a row in the requested locale → render it.
- Else fall back to the `en` row. When edit mode is on, fallback strings are visually marked (e.g. a faint underline) so editors can find them.
- Raw keys (`home.hero.title`) are never shown to users — that is a dev-mode-only behavior triggered by a missing `en` row, which should never happen in practice because the pre-push step guarantees it.

## Locale selection and routing

### URL strategy

- `/` = Icelandic (default).
- `/en/...` = English.
- First-visit detection: middleware inspects `Accept-Language`; if the preferred language is English, redirects to `/en/...`; otherwise serves Icelandic.
- A locale switcher in the header/footer navigates to the equivalent URL in the other locale and sets a `NEXT_LOCALE` cookie, which overrides `Accept-Language` thereafter.
- `hreflang` link tags on every page for SEO.

### Library

`next-intl` is used for provider wiring, ICU message format (pluralization, formatting), and locale-prefix routing. The catalog still lives in Django; `next-intl` just consumes the JSON we hand it.

## Authoring flow

### English as source of truth in code

English strings live in the codebase as an `en.json`-style catalog (exact form determined at implementation time — either a single `en.json` file, or inline `defineMessages()`-style declarations colocated with components; both are compatible with this design).

Developers add or change English strings in PRs like any other code change. Lint rules forbid hardcoded strings in JSX and forbid `t('key')` calls referencing keys not present in the English catalog. Linting runs in CI and locally.

### Translation migrations (developer-run, pre-push)

Each time the English catalog is modified, the developer runs a local helper command (e.g. `make translate-new-keys`) before pushing. The command:

1. Reads the new `en.json` and compares against the current state recorded in existing translation migrations.
2. Diffs: new keys, changed source text, removed keys.
3. For new keys, calls the MT provider (DeepL or Google — DeepL preferred for Icelandic, validated against a sample at implementation time) to get Icelandic text.
4. For changed source keys, does **not** replace existing human-edited Icelandic — it only bumps `source_hash` on those rows. For rows that are still machine-translated (`is_machine_translated=True`), it re-translates.
5. For removed keys, generates a migration step marking those rows `retired=True`.
6. Writes the result as a conventional Django data migration file, which the developer commits in the same PR as the code change. The reviewer sees the English change alongside the generated Icelandic before merging.

This approach means:
- **Atomic PRs:** the code introducing a new `t('new.key')` and the migration creating the row ship together.
- **Reviewable MT output:** the Icelandic text is in the diff.
- **No CI/prod DB coupling:** migrations run at normal deploy time.
- **Local dev parity:** running `migrate` locally populates the dev DB with the same translations as prod (minus human edits made in prod after the migration).
- **Deterministic deploys:** MT runs once, at PR authoring time, not per-deploy.
- **MT credentials stay local.** Developers hold the keys; no MT credentials in CI for v1.

### Developer lifecycle of a new string

1. Developer adds `t('new.key')` to a component and adds `"new.key": "..."` to `en.json`.
2. Developer runs `make translate-new-keys`, which generates `apps/translations/migrations/NNNN_translate_new_keys.py` containing inserts for the new `en` row and corresponding MT'd `is` row.
3. Lint and tests pass locally (including a check that every `t()` call matches an `en.json` key).
4. PR merges → deploy runs `migrate` → rows land in prod → next page render shows Icelandic.
5. A trusted user later notices the Icelandic is wrong → edits inline → audit logged → `is_machine_translated` flips to False → webhook revalidates → other users see the correction within seconds.
6. Developer rewords the English later → runs the helper again → generates a new migration that bumps `source_hash` on the `is` row. Edit-mode editors see a "source changed" marker on that key in their worklist.

### Editor worklist

A small admin/editor view lists keys needing attention: (i) keys whose `source_hash` no longer matches the current English row, (ii) keys still marked `is_machine_translated=True` and never human-reviewed. This gives Icelandic editors a prioritized queue rather than requiring them to find errors by browsing.

## Open questions deferred to implementation

- Whether the English catalog is a single `en.json` or inline `defineMessages()` declarations. Either works.
- Specific MT provider (DeepL vs. Google) — decide at implementation time after testing a representative sample of Naglasúpan content.
- Exact rate-limit / permission checks on the PATCH endpoint beyond "logged-in."
- Webhook shared-secret rotation and storage.

## Out of scope but designed for

- **UGC translation.** When ready, a background job mints `project.<id>.title` / `project.<id>.description` keys into the same table, and the same inline edit UX works on them. No schema change, no new subsystem.
- **Additional locales beyond `is` and `en`.** Adding a third locale is a config change plus an MT run; the data model is already multi-locale.

## Summary

One unified translation catalog in Django, consumed by `next-intl` on the web-ui with `unstable_cache`/`revalidateTag` for seconds-fresh invalidation. English lives in code as the source of truth; Icelandic lives in the DB and is seeded via developer-run-generated Django data migrations per PR. Any logged-in user can edit inline via a global toggle; every edit is audited and revertable. The key-naming scheme and synthetic-key convention leave a clean door open for translating user-generated content in a future iteration.
