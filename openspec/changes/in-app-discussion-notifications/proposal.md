## Why

Discussion bandwidth on the platform is constrained by email-only notifications. Users can't tell when there's something to engage with unless they check email. To make discussions feel "live" we need in-app notifications: a visible signal that something is happening, a single place to see recent activity, and one-click navigation to where they need to reply.

This change adds in-app notifications for **discussion events only**. Project state-change emails and competition-related emails remain email-only and are unchanged.

## What Changes

### Backend
- Rename existing `Notification` fields to clarify their email-specific purpose: `sent` → `email_sent`, `sent_at` → `email_sent_at`, `cadence` → `email_cadence`
- Add `in_app_read_at` (nullable datetime) to `Notification` to track when the recipient read the in-app version
- Move the `notification_frequency = NEVER` short-circuit so it skips email dispatch rather than skipping notification creation entirely; users with `NEVER` still receive in-app notifications
- Hourly and daily digest emails skip notifications already read in-app (`in_app_read_at IS NULL` filter); IMMEDIATE cadence is unchanged
- New service methods on `HANDLERS.notifications` and `REPO.notifications` for listing, marking read, and summary queries
- New thin API endpoints — never touch the ORM directly, all backed by services:
  - `GET /api/notifications/summary` (cheap badge poll)
  - `GET /api/notifications/groups` (coalesced unread feed)
  - `POST /api/notifications/mark-thread-read`
- New scheduled task `delete_old_read_notifications` that removes read rows older than 30 days; cron schedule defined externally
- Existing discussion notification email templates updated so their CTA link includes the comment id (same deep-link format as in-app)

### Web UI
- Bell icon with an unread dot in the top bar; visible to authenticated users
- Popover preview showing recent unread groups + "see all" link
- New `/notifications` full page (action-queue model: unread groups only for v1)
- Toaster on new arrivals, debounced per thread (~2 minute window)
- Clicking a notification deep-links to `/projects/<slug>?comment=<id>`; the project page scrolls the matching comment into view, highlights it, focuses the relevant reply input, and marks all unread notifications for that thread as read
- Stale targets (deleted discussion / unlisted project) toast "this discussion is no longer available" and still mark the thread read

## Capabilities

### Modified Capabilities
- `notifications`: schema field rename, new `in_app_read_at` column, in-app service methods, in-app API endpoints, retention task, `NEVER`-cadence behavior change, digest filter for read-in-app rows, email CTA includes comment id

### New Capabilities
- `in-app-notifications-ui`: bell with unread dot, popover preview, full notifications page, toaster, click-through deep-link UX

## Impact

- **Django backend**: model migration (column renames + new column + index), service handler additions, new API router for notifications, new django-task for retention
- **Web UI**: new bell component, popover, `/notifications` page, polling client, click-through routing on project pages, toaster behavior
- **Cron**: new entry to call `delete_old_read_notifications` daily (defined externally, outside this repo)
- **OpenAPI**: new endpoints require type regeneration
- **Email templates**: existing discussion notification templates updated to include `?comment=<id>` in CTA URLs
