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

- [ ] 11.1 From `src/web-ui/`: `npm run generate-types` (consumes the regenerated OpenAPI).
- [ ] 11.2 Add Next.js route `app/projects/[projectSlug]/articles/new/page.tsx` (and `[articleId]/edit/page.tsx`) gated to `full_edit` contributors.
- [ ] 11.3 Build `<ArticleEditor>` component on MDXEditor (WYSIWYG, markdown-backed — body stored as markdown). Configure the plugin/toolbar set to exactly the agreed GFM subset (tables, strikethrough, task lists, autolinks, images); disable constructs the read page / email renderers don't support. The read page (§10) renders via the existing `react-markdown` renderer, NOT MDXEditor — see design §9 for why there is no shared renderer.
- [ ] 11.3a Verify markdown-flavor parity: each allowed construct (tables first) renders identically across MDXEditor, the `react-markdown`+`remark-gfm` read page, and the Python `markdown` email path. See the parity risk in design.md.
- [ ] 11.4 Implement drag-to-insert / paste image upload via MDXEditor's image plugin upload handler (call existing project-image upload endpoint; editor inserts markdown image syntax).
- [ ] 11.5 Implement separate hero-image uploader (single image, above the body).
- [ ] 11.6 Implement channel dropdown sourced from `GET /api/projects/{slug}/channels`.
- [ ] 11.7 Implement "Save draft" and "Publish" actions; "Publish" opens a confirm dialog with an optional `published_at` override (datetime picker, defaults to now).

## 12. Frontend — Article render page

- [ ] 12.1 Add Next.js route `app/projects/[projectSlug]/articles/[articleSlug]/page.tsx`.
- [ ] 12.2 Reuse the project-page header component so the article is visually anchored to its project.
- [ ] 12.3 Render hero image, title, optional byline, markdown body.
- [ ] 12.4 Return 404 on draft articles unless the viewer is the author or a `full_edit` contributor.
- [ ] 12.5 On mount, if a query param indicates click-through from a notification (or we have an article id in the URL), call `POST /api/notifications/mark-thread-read` with `{"article_id": <id>}`.

## 13. Frontend — Channel management UI

- [ ] 13.1 Add a "Channels" section in project settings (route or tab — design.md decision: standalone route `/projects/[slug]/settings/channels`).
- [ ] 13.2 Render the project's channels as a list with rename in-place + delete buttons.
- [ ] 13.3 "Add channel" form with name validation; show 409 errors inline.
- [ ] 13.4 Delete flow: when API returns 409 (channel has articles), show a "Reassign articles to…" picker and call the bulk-reassign endpoint, then re-attempt delete.
- [ ] 13.5 Disable delete on the only remaining channel; show tooltip.

## 14. Frontend — In-app notifications surface updates

- [ ] 14.1 Update `<NotificationGroup>` / popover item rendering to branch on `kind`: article headline + article excerpt + project image.
- [ ] 14.2 Update click-through: article items navigate to `/projects/{projectSlug}/articles/{articleSlug}` instead of `/projects/{slug}?comment=…`.
- [ ] 14.3 Update the toaster component to render article-kind toasters with article headline format.
- [ ] 14.4 Ensure the toaster debounce keys on article id for article items.
- [ ] 14.5 Handle the article-stale case (article render page returns 404): on the parent feed, still call `mark-thread-read` with the known article id so the stale row clears.

## 15. Frontend — Write article entry point

- [ ] 15.1 Add the "Write article" button to the project page top bar / actions area, visible only when the viewer is a `full_edit` contributor on the project.
- [ ] 15.2 Wire it to navigate to `/projects/{slug}/articles/new`.

## 16. End-to-end verification

- [ ] 16.1 Run `make ci` from project root — fix any lint, type, or test failures.
- [ ] 16.2 Boot the stack locally (`docker compose up` or the project's run path), log in with the test account from `.env.claude`, and walk through: create a project channel, write a draft, publish at "now" (verify a follower receives both an email and an in-app notification + bell dot), publish backdated (verify no notifications), edit the article, delete the article.
- [ ] 16.3 With Playwright, run the scenario as a regression: it should be a recorded fixture covering create → publish → notification → delete.
- [ ] 16.4 Verify the Naglasúpan broadcast pipeline post-flip: queue a `platform_updates` BroadcastEmail and observe that recipients match the new Follow-based query (use the parity tool from 8.5).
- [ ] 16.5 Verify no references to `email_opt_in_competition_results` or `email_opt_in_platform_updates` remain anywhere in the codebase (`rg email_opt_in_` returns nothing).
- [ ] 16.6 Verify no direct ORM access in the new route modules: `rg -n 'Article\.objects|Channel\.objects|FollowChannelPreference\.objects' src/django-backend/api/` returns nothing. Every database operation in `api/routers/articles.py` and `api/routers/channels.py` should be a call into `HANDLERS.articles` / `REPO.articles` (or the channel handler if separated).

## 17. Deploy preparation

- [ ] 17.1 Re-read the migration plan in `design.md` and confirm migration ordering is correct in the generated migration files.
- [ ] 17.2 Confirm that the broadcast-resolver change ships in the same commit / deploy as the column drop, so there is no window where the resolver reads a removed column.
- [ ] 17.3 Run the parity management command against a recent prod snapshot (offline) and review the diff before deploy.
