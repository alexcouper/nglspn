## Context

The existing `Notification` model in `apps/notifications/` is, despite its name, an email-dispatch queue. It tracks who to email, on what cadence, and whether the email has been sent; once `sent=True` it's done. Recipient resolution (project contributors with `full_edit=True` and `is_system_user=False` + thread root author + thread participants − the comment author) lives in `services/notifications/django_impl/handler.py:create_notifications_for_discussion` and is non-trivial.

The Django backend follows a layered pattern: `api/` routers are thin and never access ORM directly — they call `HANDLERS.<domain>` for business logic and `REPO.<domain>` for read-only queries. Tests live at the service layer.

To deliver in-app notifications for discussion events, we need a record of "this recipient was notified about this event" that persists past email send and supports a read/unread lifecycle.

## Goals

- Show users a visible signal when there's discussion activity affecting them
- Let them navigate to the exact comment with one click, with the reply box ready
- Cut digest-email redundancy when the user has already engaged in-app
- Reuse the existing recipient-resolution logic without forking it

## Non-Goals

- WebSocket / SSE delivery — polling is fine for v1; defer real-time push until traffic warrants it
- Notifications for non-discussion events — project state-change and competition emails remain email-only
- An inbox/history view of read notifications — action-queue only for v1; YAGNI inbox until users need it
- Per-channel preferences UI — in-app is always on; the existing email cadence (`notification_frequency`) is unchanged
- Browser/mobile push notifications
- Cross-tab toaster deduplication — accept the small chance a user gets the same toast in two open tabs

## Decisions

### 1. Single `Notification` row per event, multi-channel

Rather than create separate `EmailDispatch` and `InAppNotification` rows, the existing model is extended with `in_app_read_at`. Recipient resolution and row creation already happen at the right time (when a discussion is created); we get in-app for free. Coalescing for UX happens at read time, keyed by root discussion id.

The fields on `Notification` after this change:

```
id                  UUID, pk
recipient           FK User
discussion          FK Discussion
email_cadence       choice (immediate/hourly/daily/never)  ← was `cadence`
email_sent          bool, default false                    ← was `sent`
email_sent_at       datetime, nullable                     ← was `sent_at`
in_app_read_at      datetime, nullable                     ← NEW
created_at          datetime
```

Existing rows backfill `in_app_read_at = NULL` automatically; they represent historical email events.

**Alternative considered**: Two separate models sharing a recipient-resolution helper. Rejected because the work is identical and "did we email and did they read" is a single-row question — splitting forces a join.

### 2. `NEVER` becomes an email-only opt-out

Currently a recipient with `notification_frequency = NEVER` causes the notification row to be skipped entirely. Under the unified model, the row is created (so they get the in-app notification) but no email is dispatched. This matches user mental model — turning off email shouldn't blind you when you visit the app.

Concretely, in `create_notifications_for_discussion`, the `if recipient.notification_frequency == NotificationCadence.NEVER: continue` branch is removed. The row is always created. Email-send paths gain the `NEVER` filter:
- IMMEDIATE path: skip `_send_immediate` if cadence is NEVER
- Batch jobs already filter by cadence, so NEVER rows naturally don't show up

**Alternative considered**: Add a separate `in_app_enabled` user toggle. Rejected as YAGNI; in-app is always on for v1. Add the toggle later if anyone asks.

### 3. Coalescing computed at read time, grouped by root discussion

The unread feed groups notifications whose underlying discussions share the same root (`discussion.parent_id` chain → root). The aggregate "group" carries:

```
NotificationGroup
  root_discussion_id
  project { id, slug, name, image_url }
  headline_kind        # "started" | "replied"
  actor_names: list    # ordered, deduplicated, most recent first
  latest_body_excerpt  # truncated text from the most recent unread row
  latest_event_at
  unread_count
  latest_notification_id  # to enable comment-id deep link
```

Read groups disappear from the feed (we do not coalesce read with unread). When the user clicks a group, all underlying unread `Notification` rows for that root are marked read in one update.

API returns groups, not raw rows. Read-side joins live on `REPO.notifications`; the handler composes the group objects.

### 4. Polling for "live"

Frontend polls `GET /api/notifications/summary` on focus and on a 30-second interval. The summary returns just:

```json
{ "has_unread": true, "unread_group_count": 3 }
```

The badge updates from this. When `unread_group_count` increases, the popover/page (if open) refetches `GET /api/notifications/groups`, and the toaster diff logic runs (see decision 7).

WebSocket/SSE would deliver lower latency but adds infra. Defer until traffic warrants it.

### 5. Digest emails suppress already-read in-app

`send_batch_notifications` adds `in_app_read_at__isnull=True` to its filter:

```python
unsent = Notification.objects.filter(
    email_cadence=cadence,
    email_sent=False,
    in_app_read_at__isnull=True,        # ← new
    recipient__is_active=True,
)
```

IMMEDIATE cadence is unchanged — it fires synchronously, no opportunity to read first. A user who keeps the app open and reads in-app before the next hourly/daily fire never gets the digest for those threads.

### 6. Deep-link with comment id

In-app notifications and discussion emails both link to `/projects/<slug>?comment=<id>` where `<id>` is the comment that should anchor the user's attention.

The project page reads the param on load:
- scrolls the matching comment into view (UI scroll only — does not reorder the discussion list)
- applies a brief highlight class
- focuses the appropriate reply box:
  - if the comment is a root discussion, focus its own reply input (so the user can reply to the new discussion)
  - if the comment is a reply, focus its thread's reply input
- calls `POST /api/notifications/mark-thread-read` with the comment's root discussion id

Stale targets (deleted discussion, unlisted project, comment-id not present on the page): toast "this discussion is no longer available" and still call mark-thread-read so the notification clears from the feed. We do not 404.

The browser back button returns to the prior page (notifications page or wherever the user came from); we don't manipulate history specially.

### 7. Toaster: per-thread debounce

On each poll, the client diffs the new unread group set against the previous one. For each group that newly contains unread rows since the last toast for that thread, show one toaster matching the coalesced feed text. Suppress further toasts for the same thread within a 2-minute window.

This avoids a barrage when bursts arrive while the user is away from the page.

### 8. UI shape: bell with dot, popover preview, full page

A bell icon in the top bar shows a small unread dot (no count) when `has_unread` is true. Clicking opens a popover with the most recent ~5 unread groups and a "See all" link. The user dropdown also has a "Notifications" entry. The full feed lives at `/notifications` and shows unread groups only for v1 (action-queue model).

When/if the inbox view is needed, add a tab and surface read items dimmed. The schema already supports it via `in_app_read_at`; only the UI changes.

### 9. Retention: delete read rows after 30 days

A daily django-task `delete_old_read_notifications` deletes `Notification` rows where:

```
in_app_read_at IS NOT NULL AND in_app_read_at < now() - 30 days
```

Unread rows are not deleted regardless of age — if the user hasn't read it, we keep it. Email-only historical rows (`in_app_read_at IS NULL`, sent long ago) are also retained; that's a separate concern out of scope.

The cron schedule that calls this task is defined outside this repo; this change ships only the task.

### 10. Thin API, services do the work

API endpoints translate request → handler call → response and never touch the ORM. Read-only joins live on `REPO.notifications`; the handler composes them into group objects. Tests target the service layer.

API endpoints introduced:

| Method | Path                                     | Returns                                |
| ------ | ---------------------------------------- | -------------------------------------- |
| GET    | `/api/notifications/summary`             | `{ has_unread, unread_group_count }`   |
| GET    | `/api/notifications/groups?limit=N`      | `[ NotificationGroup, ... ]`            |
| POST   | `/api/notifications/mark-thread-read`    | `{ marked: <count> }` — body `{ root_discussion_id }` |

All endpoints require authentication. `mark-thread-read` is idempotent; calling it for an already-read thread is a no-op returning `marked: 0`.

## Risks / Trade-offs

- **Risk**: Coalescing-at-read-time means high-traffic threads do per-page-load aggregation. → Mitigation: the unread set is small (only the requesting user's unread rows); index on `(recipient_id, in_app_read_at)` keeps it cheap. If we later need read-aggregation we can revisit with a materialized view or denormalized group table.
- **Risk**: Field rename migration on `notifications.cadence/sent/sent_at` could break in-flight code paths during deploy. → Mitigation: the renames + reference updates ship as a single change. These fields aren't on hot paths (notification creation runs from a background task; digest jobs run hourly/daily), so a brief migration window is acceptable.
- **Risk**: Polling load — 30s interval × every authenticated tab. → Mitigation: summary endpoint is a small COUNT query; index supports it. Long-poll / SSE alternatives are deferred. Consider raising the interval if real-world load proves higher than expected.
- **Risk**: A user who reads notifications in-app and then opens the email digest (sent before they read in-app) sees a stale email mentioning items they've already handled. → Acceptable; emails are point-in-time snapshots and this is rare for HOURLY (small window) and slightly more likely for DAILY but tolerable.
- **Trade-off**: Action-queue only feed loses the "remind me what I read yesterday" affordance. → Decision: ship without it; add inbox view if/when users ask. Schema already supports the future tab.
- **Trade-off**: 30-day retention quietly loses old read rows. → Acceptable; the source of truth (the discussion itself) lives on the project page, and notifications are inherently ephemeral.
