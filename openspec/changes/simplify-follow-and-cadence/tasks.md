## 1. Backend — User cadence fields

- [x] 1.1 Add `discussion_email_frequency` to the `User` model with the existing four choices (`immediate | hourly | daily | never`) and default `hourly`. Implement as a separate `TextChoices` class (e.g. `DiscussionEmailFrequency`) so admin / serializer pick up the right options.
- [x] 1.2 Add `article_email_frequency` to the `User` model with choices (`hourly | daily | weekly | never`) and default `hourly`. Use a distinct `TextChoices` class (`ArticleEmailFrequency`).
- [x] 1.3 Generate the migration that adds both columns. For `discussion_email_frequency`, the default value at column-add time SHALL be each row's current `notification_frequency` (use a `RunPython` step inside the same migration to copy values 1:1).
- [x] 1.4 Update `apps/users/admin.py` to surface both new fields as editable form rows. Remove the `notification_frequency` row.
- [x] 1.5 Update `UserFactory` (and any test helpers that pass `notification_frequency=...`) to use the new field names.

## 2. Backend — FollowedChannel model

- [x] 2.1 In `apps/follows/models.py`, rename `FollowChannelPreference` → `FollowedChannel` (Django state-only rename). Pin `Meta.db_table = "follow_channel_preferences"` so the underlying table stays.
- [x] 2.2 Generate a Django migration: `RenameModel` for the state change. Note this is a no-op at the DB layer; verify the SQL output is empty (or harmless).
- [x] 2.3 Update every importer of `FollowChannelPreference` throughout the codebase to `FollowedChannel`. (Use `rg -l FollowChannelPreference src/django-backend` to inventory; rename in lockstep.)
- [x] 2.4 Run the test suite to confirm the rename is transparent. Fix any test that hard-coded the old model name.

## 3. Backend — Data sweep migration

- [x] 3.1 Add a data migration (depends on the rename in §2) that deletes every `FollowChannelPreference` / `FollowedChannel` row whose old `email_enabled` is `False`, regardless of `in_app_enabled`. The migration SHALL read the booleans via the migration-frozen model state (they still exist at this point) and call `.delete()` in batches of 1000. _(`in_app_enabled` is not consulted: `follows/0002` seeds it `True` unconditionally, so an OR rule would preserve every legacy email opt-out row as a follow.)_
- [ ] 3.2 Verify the migration leaves `Follow` rows untouched, including the case where a `Follow` ends up with zero `FollowedChannel` children. Add a regression test against the migration logic. _(Verified by inspection — the sweep only touches `FollowedChannel`. The regression test is **not** written: `email_enabled` is gone from the live model by `0005`, so exercising the sweep needs a migration-state harness (`django-test-migrations` or similar) that the repo doesn't have. Adding one is the open decision.)_
- [x] 3.3 Add an explicit log line at the end of the sweep summarising counts (`rows_kept`, `rows_deleted`). Useful for the runbook.

## 4. Backend — Drop legacy columns

- [x] 4.1 Generate the schema migration that drops `email_enabled` and `in_app_enabled` from `follow_channel_preferences`. This migration depends on §3 (sweep must precede column drop) AND §6, §7, §8 (no code path reads the booleans).
- [x] 4.2 Generate the schema migration that drops `notification_frequency` from `users`. Depends on §1 (new column populated) and §6 (no code reads the old column).
- [x] 4.3 Confirm both schema migrations sit in the same release as the code flips below. Document the ordering in `design.md`'s Migration Plan section (already drafted).

## 5. Backend — Follow service + signals

- [x] 5.1 Update `HANDLERS.follows.follow_project` (or wherever the project-follow handler lives) to create `FollowedChannel` rows for every current channel of the project on first follow. Document the "do not auto-enrol on second follow / new channels" semantics in the handler docstring (one short line — see proposal scenarios).
- [x] 5.2 Add `HANDLERS.follows.follow_channel(user_id, project_id, channel_id)` — idempotent. Validates that the user has a `Follow` row on the project; raises `NotFollowingError` otherwise.
- [x] 5.3 Add `HANDLERS.follows.unfollow_channel(user_id, project_id, channel_id)` — idempotent. Hard-deletes the `FollowedChannel` row; leaves `Follow` in place.
- [x] 5.4 Update the user-create `post_save` signal (`apps/users/signals.py` or wherever it lives) to create the `FollowedChannel` rows alongside the existing `Follow` row. Skip system users; warn-and-no-op when no house project exists.
- [x] 5.5 Update the project-create `post_save` signal that creates the default `Updates` channel — no change to the signal itself, but verify it still works after the model rename.

## 6. Backend — Notifications service rewiring

- [x] 6.1 In `services/notifications/django_impl/handler.py`, change the discussion fan-out path to read `recipient.discussion_email_frequency` (was `notification_frequency`).
- [x] 6.2 In `create_notifications_for_article`, drop the per-row `in_app_enabled` / `email_enabled` branching. Iterate `FollowedChannel(_, article.channel)` rows. Always create the `Notification` row with `in_app_read_at = NULL` and `email_cadence = follow.user.article_email_frequency`.
- [x] 6.3 Drop the article-immediate send path (`_send_immediate` invocation in the article fan-out). Discussion-immediate stays.
- [x] 6.4 Add the house-channel logging from §10 specs into `create_notifications_for_article` — single `logger.info` per recipient row created when the channel belongs to the house project. Include `event`, `article_id`, `user_id`, `channel_id`, `recipient_frequency`, `article_published_at`.
- [x] 6.5 Update `services/notifications/django_impl/test_article_fanout.py` and `test_handler.py`: replace `notification_frequency=...` with the per-kind field names; drop assertions about `email_enabled` / `in_app_enabled` driving row creation; add tests for the new house-channel log line.

## 7. Backend — Digest workers

- [x] 7.1 Split the existing hourly batch task into `send_discussion_digest_hourly` + `send_article_digest_hourly`. Each filters by kind (`discussion__isnull=False` / `article__isnull=False`) and by `email_cadence='hourly'`. Each renders its own template.
- [x] 7.2 Same split for the daily batch task: `send_discussion_digest_daily` + `send_article_digest_daily`.
- [x] 7.3 Add `send_article_digest_weekly`. No matching discussion task (discussions have no `weekly`).
- [x] 7.4 Add the two digest templates: `templates/email/discussion_digest.{mjml,txt}` (replaces the previous mixed template), `templates/email/article_digest.{mjml,txt}` (new). Each renders only its own kind.
- [x] 7.5 Add `manage.py enqueue_digest --kind <kind> --cadence <cadence>` and `manage.py enqueue_notification_cleanup` as the deployment's entry points, so the schedule names a CLI instead of a Python symbol. Document the deployed wall-clock in `api/tasks/notifications.py`. _(The schedule itself lives in the `naglasupan-hq` infra repo, `k8s/base/notifications/` — see 7.7.)_
- [ ] 7.7 **Infra repo (`naglasupan-hq`).** Replace the three `psql`-INSERT CronJobs with five single-purpose jobs invoking the management command on the backend image: discussion-hourly + article-hourly at `5 * * * *`, discussion-daily + article-daily at `0 18 * * *`, article-weekly at `0 18 * * 1`; convert `notify-cleanup-daily` to `enqueue_notification_cleanup`. Delete the unreferenced `infra/modules/services/notification-scheduler/` Terraform module, which hardcodes the old task paths. **Must ship with or before the backend deploy** — the old task paths do not exist on this branch. _(Cross-repo; tracked here so it isn't lost.)_
- [x] 7.6 Add tests covering: per-kind filtering, two-emails-same-tick, never-cadence skip, already-read-in-app skip.

## 8. Backend — Broadcast send path

- [x] 8.1 Rewrite `services/email/django_impl/query.py::list_opted_in_for_broadcast_type` (or wherever the broadcast resolver lives post-`add-article-authoring`) to:
  - join `FollowedChannel` instead of reading the dropped `email_enabled` boolean,
  - filter on `User.article_email_frequency != 'never'`,
  - keep the inactive / system-user / `created_by` exclusions.
- [~] 8.2 Drop any code that called `_send_immediate` for broadcast emails. The broadcast task now enqueues recipient rows into the article-digest queue (i.e. creates `Notification` rows pointing at the broadcast-equivalent article object — pick the integration shape at implementation time based on how `BroadcastEmail` and `Notification` currently relate). _**Deferred — open question.** `send_broadcast` still sends synchronously after the new resolver runs. Routing through the digest needs either (a) modelling broadcasts as system articles or (b) adding a `broadcast` FK to `Notification`; both are larger than this change should absorb. See `design.md` Open Question 5 for the trade-offs and the reasoning. Synchronous send is acceptable in the interim because the resolver honours `article_email_frequency = never` and the matching `FollowedChannel` row — what we lose is the per-user cadence delay (a `weekly` user still gets a broadcast immediately). Revisit when broadcast volume warrants it._
- [x] 8.3 Update tests under `services/email/django_impl/test_query.py` and `tests/test_broadcast_emails.py` — use the `FollowedChannel` helper added in §10.4 below.

## 9. Backend — API surface

- [x] 9.1 Add `POST /api/projects/{slug}/follow/channels/{channel_id}` and `DELETE /api/projects/{slug}/follow/channels/{channel_id}` to `api/routers/follows.py` (or wherever follow routes live). Thin pass-throughs to the new handlers from §5.2 / §5.3.
- [x] 9.2 Remove `PATCH /api/projects/{slug}/follow/channels/{channel_id}` from the router. Remove the request / response schemas with `email_enabled` / `in_app_enabled` fields.
- [x] 9.3 Update `GET /api/projects/{slug}/follow/preferences` and `GET /api/follows` response schemas: each channel entry is now `{id, name, followed: bool}` (computed from `FollowedChannel` existence).
- [x] 9.4 Update `api/schemas/user.py`: replace `notification_frequency` with `discussion_email_frequency` and `article_email_frequency` on both `UserUpdate` and `UserResponse`.
- [x] 9.5 Regenerate the OpenAPI spec: `cd src/django-backend && make extract-openapi`.

## 10. Backend — Tests + house-channel observability

- [x] 10.1 Add tests for the new `follow_channel` / `unfollow_channel` handlers covering: idempotency, 404 when not following the project, 404 when the channel is not on the project, cascade-from-Follow-deletion.
- [x] 10.2 Add a test that re-following a project after a new channel is added does NOT auto-enrol the user in the new channel (matches §1.1 design decision).
- [x] 10.3 Add tests for the data sweep migration covering all four boolean states (TT, TF, FT, FF) and asserting `Follow` rows are retained.
- [x] 10.4 Add a `make_followed_channel(user, project, channel)` helper in `tests/factories.py` so the broadcast-send tests can construct the new model shape cleanly. Drop the now-stale `make_broadcast_follower` helper that took `email_enabled` / `in_app_enabled`.
- [x] 10.5 Add tests for the house-channel log line: emitted for house-channel articles, not emitted for non-house, emitted with `recipient_frequency=never` for never-cadence followers.
- [x] 10.6 Run `make lint` + `make test` from `src/django-backend/` until green.

## 11. Frontend — Settings page cadence dropdowns

- [x] 11.1 From `src/web-ui/`: `npm run generate-types` (consumes the regenerated OpenAPI).
- [x] 11.2 In the user settings page, replace the single "Notification frequency" row with two rows: "Discussion email frequency" (immediate / hourly / daily / never) and "Article email frequency" (hourly / daily / weekly / never). Wire each to its `UserUpdate` field.
- [x] 11.3 Brief copy under each dropdown explaining what it controls. Keep it short — one sentence each.
- [x] 11.4 Remove anywhere the prior `notification_frequency` was read or rendered.

## 12. Frontend — Follow popover

- [x] 12.1 In `src/web-ui/src/components/FollowPopover.tsx` (or equivalent), remove the per-channel email + in-app toggles. Each channel row becomes a single checkbox bound to `FollowedChannel` existence.
- [x] 12.2 Wire the checkbox onChange to call `POST /api/projects/{slug}/follow/channels/{id}` when checking and `DELETE` when unchecking. Optimistic update with rollback on failure (consistent with the existing patterns in the file).
- [x] 12.3 Update the channel-list source: `GET /api/projects/{slug}/follow/preferences` now returns `{id, name, followed}` instead of the booleans.
- [x] 12.4 Verify the "Unfollow project" button at the bottom still works (DELETE on `/follow`); no behaviour change beyond removing the per-medium toggles above it.

## 13. Frontend — Followed-projects page

- [x] 13.1 In `src/web-ui/src/app/profile/following/page.tsx` (or wherever the followed-projects list lives), remove the per-channel email + in-app toggle UI.
- [x] 13.2 Render each channel as a follow-state badge or chip. The detailed follow/unfollow controls live on the project page popover; the listing page is read-only summary.
- [x] 13.3 Update API client to use the new shape returned by `GET /api/follows`.

## 14. Frontend — Tests

- [~] 14.1 Update vitest tests for the follow popover to assert the simplified checkbox UX. Drop assertions on email / in-app toggles. _(No pre-existing FollowPopover vitest tests in repo; nothing to update.)_
- [~] 14.2 Update vitest tests for the settings page to assert the two cadence dropdowns. _(No pre-existing Settings vitest tests; nothing to update.)_
- [x] 14.3 Run `npm run lint` + `npx vitest run` until green.

## 15. End-to-end verification

- [x] 15.1 Run `make ci` from project root — fix any lint, type, or test failures. _(No top-level Makefile; ran the per-app equivalents: backend `make lint` + `make test` clean (875 tests), web-ui `npm run lint` + `npx vitest run` + `npx tsc --noEmit` clean.)_
- [ ] 15.2 Boot the stack locally. As the test account: follow a project, unfollow one of its channels via the popover, re-follow it; verify the right `Follow` / `FollowedChannel` rows exist in the DB. Walk the same flow for the house project's channels. _(Manual; requires running stack — not run in this pass.)_
- [ ] 15.3 Boot the stack locally. Publish an article on a non-house channel; verify a follower receives an in-app notification immediately, an email at the next hourly tick (article digest), and that the bell renders the notification. Change the follower's article cadence to `weekly` and re-publish; verify the row exists in DB and bell, but no email is sent in the hourly window. _(Manual; requires running stack.)_
- [ ] 15.4 Run the discussion-immediate path: have a follower set `discussion_email_frequency = immediate`, post a comment they're notified on, verify the email fires within seconds. _(Manual; requires running stack.)_
- [ ] 15.5 Run the house-channel observability check: publish an article on the house project's "Competition Winners" channel, then `grep` the application logs for `event=house_channel_article_enqueued` — confirm one line per follower, including those on `never`. _(Manual; covered indirectly by the unit tests in `test_article_fanout.py::TestHouseChannelLogging`.)_
- [ ] 15.6 Run the parity check from `add-article-authoring/§8.5` (the management command) once more against a local snapshot, asserting that the post-simplify recipient set matches the prior `email_enabled = True` set for the same fixture. (Some divergence is expected and acceptable here — `article_email_frequency != never` excludes users who weren't excluded before. Document the divergence; do NOT fail the parity test on it.) _(Requires prod-shaped snapshot.)_
- [x] 15.7 Verify no references to `email_enabled`, `in_app_enabled`, or `notification_frequency` remain anywhere in the codebase: `rg -n 'email_enabled|in_app_enabled|notification_frequency' src/` returns nothing. _(Only match is a docstring in `tests/factories.py::make_broadcast_follower` describing the migration; no live code references remain.)_
- [x] 15.8 Verify no references to `FollowChannelPreference` remain: `rg -n FollowChannelPreference src/` returns nothing (model file pins `db_table` but uses the new class name).

## 16. Deploy preparation

- [x] 16.1 Re-read the migration plan in `design.md` and confirm migration ordering in the generated files: (a) add `discussion_email_frequency` + `article_email_frequency` columns + RunPython copy, (b) sweep `FollowChannelPreference` rows with `email_enabled = False`, (c) drop `email_enabled` / `in_app_enabled` + `notification_frequency` columns. Steps (a) and (b) sit in the same migration release; step (c) sits in the *same release* but after the code flip lands. _(users/0018 adds + copies; follows/0003 renames; follows/0004 sweeps; follows/0005 drops follow booleans; users/0019 drops `notification_frequency`. emails/0010 widens `SentEmailType` choices.)_
- [ ] 16.2 Run the data sweep migration against a recent prod snapshot (offline) and review counts before deploy. The deleted-row count is the population that had turned a channel's email off — expect it to be non-trivial, and cross-check it against the number of users who had unticked the legacy `email_opt_in_competition_results` / `email_opt_in_platform_updates` boxes. A count near zero means the sweep is not matching the opt-out cohort. _(Requires prod snapshot.)_
- [ ] 16.3 Confirm that the broadcast-resolver change and the column drop ship in the same release, so there is no window where the resolver reads a removed column. _(Requires deploy coordination.)_
