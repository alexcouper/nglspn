## Why

Phases 1 and 2 of the Articles, Following & News design landed the Follow primitive, per-channel preferences, and the settings UI — but the new notification path is not yet wired up and no one can actually publish anything. Naglasúpan still emails its subscribers through the legacy `email_opt_in_*` flags. Phase 3 closes the gap: project owners get to author and publish Articles, the publish event drives both email and in-app notifications via Follow preferences, and the legacy flags are removed.

## What Changes

- Add an `Article` primitive: title, markdown body, hero image, slug, source (internal/external), `published_at`, channel FK, project FK, author FK, approval state.
- Add a "Write article" entry point and a dedicated authoring page (`/projects/<slug>/articles/new`) for contributors with `full_edit`. Markdown editor with side-by-side preview, drag-to-insert images, hero-image upload.
- Add the article-render page at `/projects/<project-slug>/articles/<article-slug>` reusing the project-page header. Internal articles open in a new tab when linked from carousels.
- Add publish lifecycle: draft → published, with explicit publish action, slug generated on publish (reuses existing Icelandic transliteration helper), edit-after-publish allowed, hard delete allowed.
- Add **backdated publish**: author may set `published_at` to a past date at publish time. Backdated publishes skip notification fan-out. This is the mechanism Phase 4 content backfill will rely on.
- Add a "Channels" section in project settings: add / rename / delete channel (delete-with-articles guarded by a reassign step).
- Add `article_trust` boolean on `User` (default `True`). When `True`, an author's published articles are auto-approved globally; when `False`, articles render locally but stay out of global surfaces until an admin approves them. Admin can demote any individual article independently.
- **Wire notification firing on Article publish.** For each Follow on the project, look up the per-channel preference: if email switch on → enqueue email through the existing notification pipeline; if in-app switch on → create an in-app Notification row. `notification_frequency` (user-global) continues to govern cadence.
- Generalise the existing `Notification` model so it can point at either a `Discussion` or an `Article`. In-app surfaces (bell, popover, page, deep-link click-through, toaster) gain support for article notifications.
- **BREAKING:** Flip the Naglasúpan outbound email send path to consult Follow + per-channel email switches on the Naglasúpan house project instead of `User.email_opt_in_competition_results` / `User.email_opt_in_platform_updates`.
- **BREAKING:** Remove the legacy `email_opt_in_competition_results` and `email_opt_in_platform_updates` fields from `User`. Remove the Phase 2 mirror logic that kept those flags in sync with the new per-channel switches.

## Capabilities

### New Capabilities

- `articles`: Article model, authoring + edit UI, channel-management UI, publish lifecycle (including backdated publish), article render page, `article_trust` flag on User, approval flow, and the publish-event hook that drives notification fan-out.

### Modified Capabilities

- `notifications`: Generalise the `Notification` model to point at a `Discussion` or an `Article`; add article-publish recipient resolution (iterate Follows, consult per-channel preferences); drop the legacy `email_opt_in_*` code path.
- `in-app-notifications-ui`: Render article notifications in the bell, popover, page, and toaster; click-through navigates to the article-render page.
- `project-following`: Remove the Phase 2 mirror-to-legacy-flag scenarios (Competition Winners → `email_opt_in_competition_results`, Product Updates → `email_opt_in_platform_updates`, unfollow-house-mirrors-both). They become obsolete when the legacy flags are removed.
- `async-broadcast-send`: Recipient resolution for the Naglasúpan competition-results / product-updates broadcasts reads Follow + per-channel email switches on the house project, not the legacy `email_opt_in_*` flags.

## Impact

- **Code:** new `articles` Django app (model, migrations, admin, API, signals); changes to `notifications` (generic notifiable, publish handler), `in-app-notifications-ui` Next.js components (notification rendering, deep-link routing), broadcast recipient query; new Next.js routes for `/projects/<slug>/articles/new` and `/projects/<slug>/articles/<article-slug>`; new "Channels" + (re)used image-upload UI in project settings.
- **Migrations:** add `Article`, add `User.article_trust`, generalise `Notification` (nullable Discussion FK + nullable Article FK, or chosen alternative — design.md decides), drop `User.email_opt_in_*` fields. Ordering matters: send-path flip and field-drop must happen in the same deploy / migration to avoid a window where the broadcast pipeline reads a removed field.
- **APIs:** new `/api/projects/<slug>/articles` CRUD; new `/api/projects/<slug>/channels` CRUD; OpenAPI spec regenerated; web-ui types regenerated.
- **Existing callers:** any code or admin form referencing `email_opt_in_*` must be updated; admin user list and onboarding may surface the new `article_trust` toggle.
- **No data backfill** in this change — Phase 4 (separate, content-only) populates historical Naglasúpan articles via backdated publishes.
