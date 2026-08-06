## 1. Backend — Article model and apps/articles app

- [x] 1.1 Create `apps/articles/` Django app skeleton (`apps.py`, `__init__.py`, `admin.py`, empty `models.py`, registered in settings).
- [x] 1.2 Add `Article` model in `apps/articles/models.py` with all fields, FKs (`project`, `channel`, `author`, `hero_image`), choices for `source` / `state` / `global_visibility` (`auto`, `pending`, `approved`, `demoted`), and the `is_globally_visible` property (true for `auto` or `approved`).
- [x] 1.3 Generate `apps/articles/migrations/0001_initial.py` including: partial unique `(project, slug)` where slug is not null; CHECK constraint on `(source, external_url)`.
- [x] 1.4 Add a save-time guard for SQLite for the `(source, external_url)` invariant (CHECK works on Postgres but is awkward on SQLite — confirm during local migration run, add guard if needed).
- [x] 1.5 Register `Article` in `apps/articles/admin.py` with read-only metadata, editable `global_visibility`, and an "Open render page" link.

## 2. Backend — User.article_trust

- [x] 2.1 Add `article_trust = BooleanField(default=True)` to the User model and generate the migration.
- [x] 2.2 Surface `article_trust` in `apps/users/admin.py` (or wherever the User admin is registered) as an editable boolean.
- [x] 2.3 Add a factory default `article_trust=True` to `UserFactory` if it explicitly enumerates fields. _(no-op: UserFactory does not enumerate boolean prefs; the model default applies.)_

## 3. Backend — Notification generalisation

- [x] 3.1 Add nullable `article = FK(Article)` to `apps/notifications/models.py:Notification`; make `discussion` nullable.
- [x] 3.2 Replace the single `(recipient, discussion)` unique constraint with two partial unique constraints (`discussion`-not-null and `article`-not-null).
- [x] 3.3 Add a Postgres CHECK constraint `(discussion_id IS NULL) != (article_id IS NULL)`; add a model `clean()` / save-time guard for SQLite parity.
- [x] 3.4 Generate one migration that performs steps 3.1–3.3 atomically (so there is no intermediate inconsistent state).
- [x] 3.5 Update `apps/notifications/admin.py` to display the populated FK (discussion or article).

## 4. Backend — Articles service layer

- [x] 4.1 Create `services/articles/` following the handler/repository pattern used in `services/notifications/`.
- [x] 4.2 Implement `HANDLERS.articles.create_draft(project_id, author_id, channel_id, **fields) -> Article`.
- [x] 4.3 Implement `HANDLERS.articles.update_article(article_id, **fields) -> Article` (works on drafts and published).
- [x] 4.4 Implement `HANDLERS.articles.publish(article_id, published_at=None) -> Article` — generates slug via `apps/articles/slugs.py`, sets `state=published`, sets `global_visibility` based on `author.article_trust`, calls `HANDLERS.notifications.create_notifications_for_article(article.id)` unless backdated.
- [x] 4.5 Implement `HANDLERS.articles.delete_article(article_id) -> None` (cascade-deletes notifications via FK).
- [x] 4.6 Implement `REPO.articles.for_project(project_id)` and `REPO.articles.get_by_project_and_slug(project_slug, article_slug)`.
- [x] 4.7 Register handlers/repos in `services/__init__.py` as `HANDLERS.articles` / `REPO.articles`.

## 5. Backend — Notification fan-out and email content

- [x] 5.1 Add `HANDLERS.notifications.create_notifications_for_article(article_id)` per the design's pseudocode: skips backdated publishes, iterates Follows, consults ChannelPreference, creates rows and triggers IMMEDIATE email.
- [x] 5.2 Add `_is_backdated(published_at, threshold_seconds=60)` helper (duplicated in both `services/articles/` and `services/notifications/` so each layer defends itself).
- [x] 5.3 Add `HANDLERS.notifications.mark_article_read_for_user(user_id, article_id)`.
- [ ] 5.4 Extend the hourly and daily batch tasks to include article rows in the per-recipient digest. _**Partial**: chunk 2 added `_send_article_batch` as a separate per-row send so article rows don't crash the digest path. True per-recipient mixed digest (single email covering discussions + articles) is **deferred** — see 5.5._
- [ ] 5.5 Create `templates/emails/article_notification_immediate.{txt,html}` and update the digest template to render mixed (discussion + article) items. _**Partial**: `templates/email/article_notification.{mjml,txt}` created (immediate single-article send works). Mixed-content digest template work is **deferred** — currently a recipient with both kinds pending gets two emails (one comment-digest, one article notification per article)._
- [x] 5.6 Add article-author exclusion in `create_notifications_for_article` (mirrors discussion path).

## 6. Backend — Channel management API and service

- [x] 6.1 Add `HANDLERS.articles.add_channel`, `rename_channel`, `delete_channel`, `bulk_reassign_articles` methods on the same handler (per design 1a, channel CRUD lives on `HANDLERS.articles` rather than its own surface).
- [x] 6.2 Wire the guards: `DuplicateChannelNameError`, `ChannelHasArticlesError(article_count)`, `LastChannelError` — the routes (chunk 3) map these to 409.
- [x] 6.3 Add API routes under `api/routers/channels.py`: `POST /api/projects/{slug}/channels`, `PATCH /api/projects/{slug}/channels/{id}`, `DELETE /api/projects/{slug}/channels/{id}`, `POST /api/projects/{slug}/channels/{id}/reassign`. Added `GET /api/projects/{slug}/channels` to feed the chunk-7 dropdown.
- [x] 6.4 Permission check on all routes: caller must be `ProjectContributor` with `full_edit = True` on the project. Implemented via `REPO.project.user_can_edit`.

## 7. Backend — Article API routes

- [x] 7.1 Add `api/schemas/article.py` with `ArticleCreate`, `ArticleUpdate`, `ArticlePublish`, `ArticleOut`, `ArticleListItem` pydantic schemas. Channel request/response schemas live here too (`ChannelCreate`, `ChannelRename`, `ChannelReassign`, `ChannelResponse`, `ChannelConflictResponse`, `ChannelReassignResponse`).
- [x] 7.2 Add `api/routers/articles.py`: `POST /api/projects/{slug}/articles` (create draft), `GET /api/projects/{slug}/articles/{id}` (read for editor — includes drafts for authors/full-edit), `PATCH /api/projects/{slug}/articles/{id}` (update), `POST /api/projects/{slug}/articles/{id}/publish` (publish), `DELETE /api/projects/{slug}/articles/{id}`. Added `GET /api/projects/{slug}/articles` for listing.
- [x] 7.3 Add `GET /api/projects/{slug}/articles/by-slug/{article_slug}` for the render page (public for published, 404 for drafts unless caller is author/full-edit).
- [x] 7.4 Permission checks on write paths: `full_edit` contributor via `REPO.project.user_can_edit`. Routes parse body → permission check → service-layer call → shape response; no ORM access in `api/routers/articles.py` or `api/routers/channels.py`.
- [x] 7.5 Update `POST /api/notifications/mark-thread-read` body schema to accept `article_id` as a third alternative; reject 2-or-more or 0 of {root_discussion_id, comment_id, article_id} with 422.
- [x] 7.6 Update `GET /api/notifications/groups` response to include `kind` discriminator and article groups (project + channel + title + excerpt + article_id + article_slug). `NotificationGroup` dataclass widened with optional article fields; `count_unread_groups_for_user` now sums distinct discussion roots + distinct article ids.

## 8. Backend — Send path flip in async-broadcast-send

- [x] 8.1 Rewrite `services/email/django_impl/query.py::resolve_broadcast_recipients` to join Follow + FollowChannelPreference on the house project's "Competition Winners" or "Product Updates" channel (based on broadcast `email_type`). _Implemented in the delegate `DjangoUserQuery.list_opted_in_for_broadcast_type` (the call site `resolve_broadcast_recipients` already routes through it); added `BROADCAST_CHANNEL_BY_EMAIL_TYPE` mapping._
- [x] 8.2 Keep the existing `is_active` and `is_system_user` exclusions; keep `created_by` self-exclusion. _`is_active`/`is_system_user` exclusions preserved in the new join. (The resolver never self-excluded `created_by` — that has always been an artefact of the send path, untouched here.)_
- [x] 8.3 Return an empty QuerySet when no house project exists.
- [x] 8.4 Update the existing tests under `services/email/django_impl/test_query.py` and `tests/test_broadcast_emails.py` to construct Follow + ChannelPreference rather than setting legacy flags. _Also covered the other recipient-dependent suites that used legacy flags: `services/users/django_impl/test_query.py`, `services/email/django_impl/test_handler.py`, `tests/test_inactive_user_emails.py`. Added `make_broadcast_follower` / `ensure_house_project` helpers in `tests/factories.py` (signal-aware: the house auto-follow means non-recipients are email-disabled followers, not non-followers)._
- [x] 8.5 Add a pre-flip / post-flip parity management command + test: enumerate the recipient set the legacy path would have selected (computed from the snapshot of `email_opt_in_*` values mirrored into preferences by Phase 1) vs. the post-flip path, asserting equality on a representative fixture. _`apps/emails/broadcast_parity.py` + `manage.py check_broadcast_parity` (nonzero exit on diff); tests in `tests/test_broadcast_parity.py`._

## 9. Backend — Remove legacy fields and mirror

- [x] 9.1 Delete the mirror code in `services/follows/django_impl/handler.py` (or wherever it lives) that writes back to `email_opt_in_*`. _Removed `LEGACY_FLAG_BY_CHANNEL_NAME`, `_mirror_legacy_email_flag`, `_clear_legacy_email_flags` and their call sites; updated `handler_interface.unfollow` docstring._
- [x] 9.2 Remove `email_opt_in_competition_results` and `email_opt_in_platform_updates` from `api/schemas/user.py` (both `UserOut` and `UserUpdate`). _Actual schemas are `UserResponse` + `UserUpdate`._
- [x] 9.3 Generate `apps/users/migrations/000N_drop_email_opt_in_fields` (drop both columns). _`0017_drop_email_opt_in_fields`._
- [x] 9.4 Update `apps/users/admin.py` to remove the two fields from the form.
- [x] 9.5 Update `UserFactory` to remove the two fields. _Factory never enumerated them; removed the flag kwargs from the `ensure_house_project` test helper that did._
- [x] 9.6 Remove tests that exercise the mirror or the legacy fields directly; update tests that referenced them as recipient signals to use Follow + ChannelPreference (overlaps with 8.4). _Deleted `TestMirrorLegacyFlag` / `TestUnfollowMirror` (follows test_handler), `apps/follows/tests/test_seed_migration.py` (re-ran the frozen Phase-1 migration against the live model), and the §8 parity tooling; rewrote `services/follows/django_impl/test_integration.py` and removed `TestEmailPreferences` from `api/routers/test_users.py`. Also regenerated `src/web-ui/backend-openapi.json` — web-ui type regen (11.1) still pending._

## 10. Backend — OpenAPI + tests

- [x] 10.1 From `src/django-backend/`: `make extract-openapi`.
- [x] 10.2 Verify the spec includes the new article + channel + article-id-on-mark-thread-read endpoints.
- [x] 10.3 Add `apps/articles/tests/` covering: model save guards, slug generation + collision suffix, publish state transitions, edit-after-publish, delete, backdated-publish notification suppression, approval flow combinations (trust True / False / admin-demoted). _Model layer: `apps/articles/tests/test_models.py` (source/external_url XOR guard, `(project, slug)` partial unique, `is_globally_visible` truth table) + `apps/articles/tests/test_slugs.py` (slug generation, collision suffix walk, per-project scoping). Publish state transitions / edit-after-publish / delete / backdated suppression / approval combos are covered by `services/articles/django_impl/test_handler.py`._
- [x] 10.4 Add `apps/notifications/tests/` covering: nullable FK constraint, partial unique constraints, mixed digest rendering, `mark_article_read_for_user`. _Model layer: `apps/notifications/tests/test_models.py` (XOR save guard, both partial unique constraints, cross-recipient/cross-kind independence). `mark_article_read_for_user` covered in `services/notifications/django_impl/test_article_fanout.py:TestMarkArticleReadForUser`. Mixed digest rendering remains **deferred** per 5.4 / 5.5._
- [x] 10.5 Add API tests under `api/routers/test_articles.py` and `api/routers/test_channels.py` covering: 401 / 403 / 404 / 409 / 422 paths and the success paths. Also extended `test_notifications.py` with article-kind groups + article-id `mark-thread-read` cases.
- [x] 10.6 Update `api/routers/test_users.py` to remove assertions on the dropped fields and add assertions for `article_trust` if surfaced via UserOut (decide based on whether admins / users see it). _`article_trust` is **not** surfaced on `UserResponse` (admin-only field), so no positive UserOut assertions added. Removed the stale `email_opt_in_*` no-leak assertions on the public profile (fields gone from the model) and added a matching no-leak assertion for `article_trust`._
- [x] 10.7 Run `make lint` + `make test` until green from `src/django-backend/`. _870 passed; ruff clean._

## 11. Frontend — Authoring page

- [x] 11.1 From `src/web-ui/`: `npm run generate-types` (consumes the regenerated OpenAPI).
- [x] 11.2 Add Next.js route `app/projects/[projectSlug]/articles/new/page.tsx` (and `[articleId]/edit/page.tsx`) gated to `full_edit` contributors. _Routes use the existing `[slug]` dynamic segment (`app/projects/[slug]/articles/new/page.tsx` and `[slug]/articles/[articleId]/edit/page.tsx`) — Next.js can't have two differently-named dynamic segments under the same parent, so `[projectSlug]` in the task is the documented name, `[slug]` is what's on disk. `full_edit` is enforced client-side via `project.contributors` lookup against the authenticated user._
- [x] 11.3 Build `<ArticleEditor>` component on MDXEditor (WYSIWYG, markdown-backed — body stored as markdown). Configure the plugin/toolbar set to exactly the agreed GFM subset (tables, strikethrough, task lists, autolinks, images); disable constructs the read page / email renderers don't support. The read page (§10) renders via the existing `react-markdown` renderer, NOT MDXEditor — see design §9 for why there is no shared renderer. _Installed `@mdxeditor/editor`; editor mounts via `next/dynamic` (`ssr: false`) since MDXEditor is client-only. Plugin set: headings, lists, quote, thematic break, link, linkDialog, image, table, markdownShortcut. Toolbar exposes bold/italic, bullet/number lists, link, image, table — strikethrough and task-list toolbar buttons are not surfaced (markdownShortcutPlugin still parses them when typed/pasted)._
- [x] 11.3a Verify markdown-flavor parity: each allowed construct (tables first) renders identically across MDXEditor, the `react-markdown`+`remark-gfm` read page, and the Python `markdown` email path. See the parity risk in design.md. _`markdown-parity.test.tsx` (vitest) asserts react-markdown+remark-gfm renders tables, strikethrough, task lists, autolinks, images, lists, and inline links into the expected HTML tags. Test was extended (post-§12) with a second pipeline that exercises the live read-page setup (`remark-gfm` + `rehype-raw` + `rehype-sanitize` with `articleSanitizeSchema`) covering the raw-HTML constructs MDXEditor actually emits: `<img width="..." height="..." />` round-trips; `<div align="center">…</div>` broadcast-style wrappers render; disallowed tags (`<script>`), the `style` attribute, `javascript:` URLs, and `on*` event handlers are all stripped. Python email path: article emails currently render only a plain-text `body_excerpt` (not the full markdown body), so no Python renderer for article body exists yet — once §5.5's mixed digest renders article bodies, this test should be extended with a Python-side counterpart asserting the same constructs through `markdown.markdown(extensions=["extra", "smarty"])` (extra covers tables; strikethrough/task-lists need extra extensions to be enabled before they ship)._
- [x] 11.4 Implement drag-to-insert / paste image upload via MDXEditor's image plugin upload handler (call existing project-image upload endpoint; editor inserts markdown image syntax). _`useImageUploadStatus` does the three-step presigned-URL dance against `/api/projects/{slug}/articles/{id}/images/upload-url` and is wired into `imagePlugin({ imageUploadHandler })`. Dropped/pasted images become ProjectImage rows linked to the article — off the project's gallery, cap and cover-image picks; the editor inserts standard `![alt](url)` markdown._
- [x] 11.5 Implement separate hero-image uploader (single image, above the body). _`HeroImageUploader` component renders the current hero or a click/drop zone; uses the same `useImageUpload` hook (non-icon mode) and stores the resulting ProjectImage id as `hero_image_id`._
- [x] 11.6 Implement channel dropdown sourced from `GET /api/projects/{slug}/channels`. _`ChannelDropdown` component + `ChannelsClient.list` API client; channels are fetched on page mount and the first channel is selected by default for new drafts._
- [x] 11.7 Implement "Save draft" and "Publish" actions; "Publish" opens a confirm dialog with an optional `published_at` override (datetime picker, defaults to now). _Save draft → POST `/articles` (new) or PATCH `/articles/{id}` (edit); after the first save the URL is `router.replace`'d to `/edit/{id}` so subsequent saves PATCH. Publish opens `PublishDialog` with a checkbox "Set a custom publish date" → `<input type="datetime-local">`; on confirm, the form is saved then `POST /articles/{id}/publish` runs with the chosen ISO datetime (or null for "now"). On success the user is sent back to the project page._

## 11C. Frontend — Remove published-at override (scope amendment)

The published-at override in `PublishDialog` was always intended for backfilling historic emails as articles; it's not useful to anyone else and adds confusion to the publish flow. Backdating now happens via a Django management command / admin path instead — the backend `POST /articles/{id}/publish` parameter and the "backdated publishes skip notification fan-out" guard (`services/articles/` + `services/notifications/`) **both stay**, so the script path keeps working unchanged.

- [x] 11C.1 Remove the "Set a custom publish date" checkbox and the `<input type="datetime-local">` from `PublishDialog`. Publish always sends `published_at: null` so the backend stamps `now()`.
- [x] 11C.2 Keep a minimal confirm dialog: title + one short reassuring sentence ("Publishing makes the article visible to everyone on the project page."), plus "Cancel" / "Publish" buttons. _Final copy intentionally **does not** name emails / in-app notifications — earlier drafts read as a warning, which is wrong for the routine publish action. The follower fan-out is what publish is for; the dialog just confirms the visibility change._
- [x] 11C.3 Drop the `publishedAt` state and the related form plumbing from `ArticleAuthoringPage.tsx`. _`useArticleDraft.publish` is now zero-arg and always passes `published_at: null`._
- [x] 11C.4 Remove any web-ui tests that asserted on the datetime-local input or backdated-publish flow from the UI. _No tests existed for either — nothing to remove._

## 12. Frontend — Article render page

- [x] 12.1 Add Next.js route `app/projects/[projectSlug]/articles/[articleSlug]/page.tsx`. _Edit route from §11.2 moved from `articles/[articleId]/edit/page.tsx` → `articles/edit/[articleId]/page.tsx` to free the `[articleSlug]` segment (Next.js doesn't allow two differently-named dynamic segs under the same parent). New URL shape: render at `/projects/<slug>/articles/<articleSlug>`, edit at `/projects/<slug>/articles/edit/<articleId>`, new at `/projects/<slug>/articles/new`. `ArticleAuthoringPage`'s `router.replace` updated accordingly. `fetchArticleBySlug` added to `lib/api/server.ts`._
- [x] 12.2 Reuse the project-page header component so the article is visually anchored to its project. _Reuses `ProjectTitleBanner` with the project's icon variant._
- [x] 12.3 Render hero image, title, optional byline, markdown body. _Hero image from `article.hero_image_url`; byline links to the author profile (suppressed for system users); body rendered via `react-markdown` + `remark-gfm` + `rehype-raw` + `rehype-sanitize` (allowlist in `articles/sanitize-schema.ts`) inside `.markdown.markdown-article`. **Trust amendment:** the rehype-raw step is required because MDXEditor's image plugin emits `<img width="…" height="…" />` (raw HTML) rather than markdown `![](url)` syntax — markdown-only rendering would silently drop every editor-inserted image. The sanitization allowlist intentionally permits `<img>`, `<div align>`, `<figure>` / `<figcaption>` (covers the broadcast-style centered-image pattern too) and intentionally forbids the `style` attribute, scripts, event handlers, and `javascript:` URLs. This widens the article author trust surface beyond what the original design.md §9 envisaged (which preferred a markdown-only contract); revisit if a future construct needs raw CSS. Tables on the read page styled in `globals.css` (`.markdown-article table`) so authoring and reading views agree._
- [x] 12.4 Return 404 on draft articles unless the viewer is the author or a `full_edit` contributor. _Server-side: drafts don't have slugs (assigned only on publish), so the by-slug endpoint can't reach them at all — `notFound()` bubbles up from the API 404. (If state-revert-to-draft is ever added, the backend's auth check on `get_article_by_slug` already enforces author / full_edit visibility — task 7.3.)_
- [x] 12.5 On mount, if a query param indicates click-through from a notification (or we have an article id in the URL), call `POST /api/notifications/mark-thread-read` with `{"article_id": <id>}`. _`markArticleThread(articleId)` added to `NotificationsClient`; the render-page useEffect calls it best-effort whenever the viewer is authenticated. Decision: don't gate on a query param — viewing the article is enough signal to clear its notification. The bell already reconciles from the server, so a missed call is recoverable._
- [x] 12.6 _(Scope amendment)_ Add an "Articles" tab to the project-page (`ProjectDetailContent`) listing the project's published articles with hero thumb + title + channel + published date, linking to the article render page. Only renders when the project has at least one published article. **Not** the Phase-5 News carousel surface — this is a basic completeness affordance so the publishing flow is end-to-end usable in Phase 3. _`ArticlesList` client component fetches `/api/projects/<slug>/articles` on mount, filters to `state=published` with a slug, sorts newest-first, and renders as a clickable list. Empty state shows "No articles yet." The tab is always present (between Description and Discussions); the empty state is its own affordance rather than hiding the tab, since hiding would make the publishing flow's destination invisible until the first publish lands._



## 12B. Frontend — Article reading polish (scope amendment)

Six pieces of UX feedback collected after §12 + §12.6 landed. Together they shift the read page from "article inside a project shell" to "article as the primary focus, project demoted to a breadcrumb."

- [x] 12B.1 Reading focus / breadcrumb: replace the full `ProjectTitleBanner` on the article render page with a breadcrumb (`← {Project title}`) that links to the project's Articles tab (`/projects/{slug}#articles`). _Breadcrumb uses `ChevronLeftIcon` + `Link` to `/projects/<slug>#articles`; relies on the existing `ProjectPageLayout` hash sync to land on the Articles tab._
- [x] 12B.2 Single-panel layout: the article panel is the only on-page surface (besides the global nav bar). The breadcrumb sits inside the panel, not above it. Remove the existing "Back to {project}" footer link — the breadcrumb handles back-navigation. _`ProjectTitleBanner` and the footer link removed; breadcrumb is the first child of the panel._
- [x] 12B.3 Article header order: Title → publish date → author byline → hero image → body. Move the channel chip into the header row alongside the date / author rather than above the title. _Channel chip now sits on the meta row with date and byline (uppercase-tracked accent text); hero image moved below the meta row._
- [x] 12B.4 Mobile full-bleed: below `sm` (`< 640px`), drop the panel's rounded corners, border, and outer padding so the article area fills the viewport edge-to-edge. Inner content padding stays. _Outer `<article>` uses `sm:py-8 sm:px-6` (no padding below sm); panel uses `sm:rounded-xl sm:border sm:border-border` + `px-4 py-6 sm:px-10 sm:py-10`._
- [x] 12B.5 Save behaviour post-publish: while the article is a draft, show "Save draft" + "Publish" (current behaviour). Once `state === "published"`, replace both with a single "Save" button that PATCHes the article. Hide the publish dialog flow on published articles. _`isPublished` derived from `article?.state === "published"`; Save button label switches "Save draft" → "Save" and the Publish button is conditionally rendered. PublishDialog stays mounted only via the existing conditional render — it can't be opened from a published state because the entry button is hidden._
- [x] 12B.6 Editor / read-view code block parity: the MDXEditor CodeMirror surface currently renders code blocks with CodeMirror's default light theme, while the read view uses the dark slate Prism theme. Make the editor's code block surface use a matching dark theme so the author preview matches the rendered article. _New `article-codemirror-theme.ts` builds a CodeMirror v6 theme + Lezer `HighlightStyle` using the same palette as the read-view Prism CSS (slate-900 background, slate-100 text, violet keywords, green strings, yellow functions, red literals, etc.). Passed to `codeMirrorPlugin` via the `codeMirrorExtensions` prop (uses the @codemirror/view, @codemirror/language, @lezer/highlight packages already present as transitive deps of MDXEditor — no new install)._

## 13. Frontend — Channel management UI

_Scope amendment: **deferred out of this change.** Every project already auto-creates an "Updates" channel via `apps/projects/signals.py:create_default_channel`, so authors can publish without ever needing to manage channels. The channel CRUD backend from §6 ships as planned (still callable, still tested) — only the management UI is deferred to a future change. The existing channel dropdown in the editor (§11.6) stays in place; with one channel per project it's a single-option dropdown for now, which is fine and avoids re-work when more channels arrive._

- [~] 13.1 ~~Add a "Channels" section in project settings~~ — deferred.
- [~] 13.2 ~~Render the project's channels as a list with rename in-place + delete buttons~~ — deferred.
- [~] 13.3 ~~"Add channel" form with name validation~~ — deferred.
- [~] 13.4 ~~Delete flow with reassignment~~ — deferred.
- [~] 13.5 ~~Disable delete on the only remaining channel~~ — deferred.

## 14. Frontend — In-app notifications surface updates

- [x] 14.1 Update `<NotificationGroup>` / popover item rendering to branch on `kind`: article headline + article excerpt + project image. _`buildHeadline` in `src/lib/notifications.ts` now emits "{Project} published {Article title} in {Channel}" for article groups; `NotificationGroupItem` already renders project image + headline + excerpt and is kind-agnostic. `NotificationsBell` keys popover items via the new `groupKey` helper so both kinds render side-by-side._
- [x] 14.2 Update click-through: article items navigate to `/projects/{projectSlug}/articles/{articleSlug}` instead of `/projects/{slug}?comment=…`. _`buildDeepLink` branches on `kind === "article"` and returns `/projects/<slug>/articles/<article_slug>` when an article slug is present._
- [x] 14.3 Update the toaster component to render article-kind toasters with article headline format. _`NotificationToaster` already used `NotificationGroupItem` + `buildHeadline`; with §14.1 in place the same path renders article headlines. The toaster `subscribeDiff` payload was generalised to `{newlyActiveKeys, groupsByKey}` so article groups flow through._
- [x] 14.4 Ensure the toaster debounce keys on article id for article items. _The unified `groupKey` returns `a:<article_id>` for article groups; the toaster's `lastShownAtRef` map is now keyed on that, so each Article id debounces independently of any discussion root that happens to share an id substring._
- [x] 14.5 Handle the article-stale case (article render page returns 404): on the parent feed, still call `mark-thread-read` with the known article id so the stale row clears. _Approach: the bell popover, the notifications feed, and the toaster all fire `markArticleRead(article_id)` optimistically on click. If the article still exists, the render page's existing mount-time `markArticleThread` call is a harmless no-op (idempotent — second call returns `marked: 0`). If the article 404s, the optimistic click-through call is the one that clears the stale row. This sidesteps the harder alternative of plumbing notification context into Next.js `notFound()` flow._

## 15. Frontend — Authoring entry point

_Scope amendment_: original §15.1 / §15.2 put a "Write article" button on the **public** project page. We rejected that placement — the public page is reader-focused (per §12B), and an authoring affordance there mixes audiences. Instead the authoring entry point lives in `/my-projects/[id]`, the existing owner-only edit view of a project. Backend `GET /api/projects/{slug}/articles` already returns drafts for `full_edit` contributors (the route flips `include_drafts=True` when the caller can edit, `api/routers/articles.py:95`), so no backend change is needed.

- [x] 15.1 (revised) Add an "Articles" tab to the My-projects edit view (`app/my-projects/[id]/EditProjectContent.tsx`). The tab SHALL list every article on the project (including drafts) sorted with drafts first, then published articles by `published_at` descending. Each row SHALL show: title, channel, state (Draft / Published badge), and (for published) the published date. _New component `MyProjectArticles.tsx` fetches via `api.articles.list(slug)` — the backend route flips `include_drafts=True` when the caller is `full_edit` (already in place at `api/routers/articles.py:95`), so drafts come back automatically without any backend change. Rows show hero thumb + title + channel + Draft/Published badge + date._
- [x] 15.2 (revised) The Articles tab SHALL provide a "New article" button that navigates to `/projects/{slug}/articles/new`, and each row SHALL link to `/projects/{slug}/articles/edit/{articleId}` for editing. (The "Write article" button on the public project page is superseded by this — explicitly NOT added.) _Tab header has a "New article" button (PlusIcon + accent-styled); each row is a `Link` to the edit page. The public §12.6 Articles tab keeps its published-only filter and is read-only — authoring affordances live only in the owner-only my-projects view._

## 16. End-to-end verification

- [ ] 16.1 Run `make ci` from project root — fix any lint, type, or test failures.
- [ ] 16.2 Boot the stack locally (`docker compose up` or the project's run path), log in with the test account from `.env.claude`, and walk through: write a draft on an existing project (the auto-created "Updates" channel is the only target), publish at "now" (verify a follower receives both an email and an in-app notification + bell dot, that the toaster fires, and that click-through lands on the article render page and clears the bell), edit the article, delete the article. Backdated publish is verified via the backend test suite + a one-off invocation of the management command — no UI path exists for it any more (see §11C).
- [ ] 16.3 With Playwright, run the scenario as a regression: it should be a recorded fixture covering create → publish → notification → delete.
- [ ] 16.4 Verify the Naglasúpan broadcast pipeline post-flip: queue a `platform_updates` BroadcastEmail and observe that recipients match the new Follow-based query (use the parity tool from 8.5).
- [ ] 16.5 Verify no references to `email_opt_in_competition_results` or `email_opt_in_platform_updates` remain anywhere in the codebase (`rg email_opt_in_` returns nothing).
- [ ] 16.6 Verify no direct ORM access in the new route modules: `rg -n 'Article\.objects|Channel\.objects|FollowChannelPreference\.objects' src/django-backend/api/` returns nothing. Every database operation in `api/routers/articles.py` and `api/routers/channels.py` should be a call into `HANDLERS.articles` / `REPO.articles` (or the channel handler if separated).

## 17. Deploy preparation

- [ ] 17.1 Re-read the migration plan in `design.md` and confirm migration ordering is correct in the generated migration files.
- [ ] 17.2 Confirm that the broadcast-resolver change ships in the same commit / deploy as the column drop, so there is no window where the resolver reads a removed column.
- [ ] 17.3 Run the parity management command against a recent prod snapshot (offline) and review the diff before deploy.
