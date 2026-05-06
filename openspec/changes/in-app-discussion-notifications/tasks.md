## 1. Schema migration

- [x] 1.1 Rename `Notification.sent` → `email_sent`, `Notification.sent_at` → `email_sent_at`, `Notification.cadence` → `email_cadence` via a single `RenameField` migration
- [x] 1.2 Add `Notification.in_app_read_at: DateTimeField(null=True, blank=True)` in the same migration (or a follow-on)
- [x] 1.3 Add a database index on `(recipient_id, in_app_read_at)` to support the unread-feed and summary queries
- [x] 1.4 Update `Notification.__str__`, admin classes, and any direct field references throughout the codebase to use the new names
- [x] 1.5 Tests: existing notification tests still pass after the rename

## 2. Service layer — handler additions

- [x] 2.1 Add to `NotificationHandlerInterface`:
  - `list_unread_groups_for_user(user_id, limit) -> list[NotificationGroup]`
  - `get_unread_summary_for_user(user_id) -> NotificationSummary`
  - `mark_thread_read_for_user(user_id, root_discussion_id) -> int`
  - `delete_old_read_notifications() -> int`
- [x] 2.2 Define `NotificationGroup` and `NotificationSummary` dataclasses in the service module (the API serializers map from these)
- [x] 2.3 Implement the four methods in `DjangoNotificationHandler`, delegating read-side joins to `REPO.notifications`
- [x] 2.4 Move the `NEVER`-cadence check in `create_notifications_for_discussion`: still create the row; only skip `_send_immediate` and rely on the existing batch filter for digests
- [x] 2.5 Update `send_batch_notifications` digest filter to add `in_app_read_at__isnull=True`
- [x] 2.6 Tests: `list_unread_groups_for_user` (empty, multiple groups, mixed read/unread, ordering by latest event)
- [x] 2.7 Tests: `get_unread_summary_for_user` (zero, non-zero, dedup across rows of same thread)
- [x] 2.8 Tests: `mark_thread_read_for_user` (marks all unread rows for the thread, idempotent, scoped to the calling user, returns count)
- [x] 2.9 Tests: `delete_old_read_notifications` (deletes only rows with `in_app_read_at` older than 30 days; leaves unread rows alone regardless of age)
- [x] 2.10 Tests: NEVER cadence still creates row, no email sent, in-app delivery still works
- [x] 2.11 Tests: hourly + daily digest filters exclude rows with `in_app_read_at IS NOT NULL`

## 3. Service layer — repository (REPO.notifications)

- [x] 3.1 Add a `notifications` repository module exposing read-only queries:
  - `list_unread_for_user(user_id)` — raw rows with `select_related` for project/discussion/author
  - `count_unread_groups_for_user(user_id)` — distinct root-discussion count
  - `unread_rows_for_thread(user_id, root_discussion_id)` — used by mark-read
- [x] 3.2 Register `REPO.notifications` in `services/__init__.py`
- [x] 3.3 Tests: each repo query (matches expected rows, respects user scope)

## 4. API endpoints

- [x] 4.1 Add notification routes to the API (new router or extend existing). All routes call `HANDLERS.notifications.*` — no ORM access.
  - `GET  /api/notifications/summary`
  - `GET  /api/notifications/groups?limit=N`
  - `POST /api/notifications/mark-thread-read`
- [x] 4.2 All endpoints require authentication; return 401 otherwise
- [x] 4.3 Tests: `summary` shape and auth
- [x] 4.4 Tests: `groups` shape, auth, default and explicit limit, only the calling user's notifications
- [x] 4.5 Tests: `mark-thread-read` updates expected rows, idempotent, scoped to caller, 200 on already-read

## 5. Retention task

- [x] 5.1 Add `delete_old_read_notifications` django-task that calls `HANDLERS.notifications.delete_old_read_notifications`
- [x] 5.2 Document the task name in this change so the externally-defined cron can schedule it daily
- [x] 5.3 Tests: task invokes handler

## 6. Email link alignment

- [ ] 6.1 Update the discussion notification email templates (immediate + digest) so the CTA URL points at `/projects/<slug>?comment=<id>` using the relevant comment id (the triggering comment for immediate, the latest for digest entries)
- [ ] 6.2 Tests: emitted email body contains the deep-link format

## 7. OpenAPI & types

- [ ] 7.1 Regenerate OpenAPI spec (`make extract-openapi`)
- [ ] 7.2 Regenerate TypeScript types (`npm run generate-types`)

## 8. Web UI — Bell, popover, polling

- [ ] 8.1 Add a bell icon + unread dot to the top bar; visible to authenticated users only
- [ ] 8.2 Implement summary-poll client (on focus + 30s interval); update dot from `has_unread`
- [ ] 8.3 Bell click opens popover with up to 5 most recent unread groups and a "See all" link to `/notifications`
- [ ] 8.4 Add "Notifications" entry to the user dropdown menu
- [ ] 8.5 Popover items render: project image, headline ("X started a discussion on Y" / "A and N others replied to <thread title> on Y"), truncated body, relative time
- [ ] 8.6 Popover item click navigates to the deep link

## 9. Web UI — Notifications page

- [ ] 9.1 Create `/notifications` page (authenticated users)
- [ ] 9.2 Render the unread-groups feed (action-queue model — no read items in v1)
- [ ] 9.3 Each group renders the same visual layout as the popover, with a checkbox for selection
- [ ] 9.4 Clicking a group navigates to `/projects/<slug>?comment=<id>` for that group's `latest_notification_id`
- [ ] 9.5 "Mark selected as read" button calls `mark-thread-read` for each selected group's root discussion
- [ ] 9.6 "Mark all as read" button iterates current visible unread groups
- [ ] 9.7 Empty state when no unread groups

## 10. Web UI — Toaster

- [ ] 10.1 On each poll, diff the new unread groups vs the previous set
- [ ] 10.2 For each group with new unread activity since the last shown toast for that thread, show one toaster (matching coalesced text)
- [ ] 10.3 Per-thread debounce: suppress further toasts for that thread within a 2-minute window
- [ ] 10.4 Toast click → same deep-link as feed click

## 11. Web UI — Project page click-through

- [ ] 11.1 On project page load, read `?comment=<id>` from the URL
- [ ] 11.2 If the matching comment is in the loaded discussion data, scroll it into view (UI scroll, not reorder) and apply a brief highlight class
- [ ] 11.3 Focus the appropriate reply input:
  - root discussion → its own reply input
  - reply → its thread's reply input
- [ ] 11.4 Call `POST /api/notifications/mark-thread-read` with the comment's root discussion id
- [ ] 11.5 If the comment id is not found (deleted discussion / unlisted / removed), show a toast "This discussion is no longer available" and still call `mark-thread-read`
- [ ] 11.6 Browser back returns to the prior page; no special history manipulation

## 12. Verification

- [ ] 12.1 Backend lint clean (`make lint`)
- [ ] 12.2 Backend tests clean (`make test`) — including all new tests in sections 2, 3, 4, 5, 6
- [ ] 12.3 Frontend lint clean (`npm run lint`)
- [ ] 12.4 Manual: log in as two users in two browsers; user A creates a discussion on user B's project; within 30s user B sees the red dot and a toast; B clicks → lands on the comment with the reply input focused; the dot disappears
- [ ] 12.5 Manual: a user with `notification_frequency = NEVER` still receives in-app notifications but no email arrives
- [ ] 12.6 Manual: read an unread group in-app before the next hourly digest fires; verify the digest email omits that thread
- [ ] 12.7 Manual: navigate to `/projects/<slug>?comment=<deleted-id>`; verify the "no longer available" toast appears and the notification is marked read
