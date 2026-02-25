## Context

The platform has projects, users, and an established service layer (handler/query interfaces with Django implementations). Background work uses `django-tasks` with `DatabaseBackend` in production. Email delivery uses Django's `EmailMultiAlternatives` via Scaleway SMTP. The frontend is a Next.js app that consumes a Django Ninja API.

Currently, project pages render all content in a single boxed layout via `ReadOnlyProjectDetail`. User settings live on the User model. There is no discussion, commenting, or notification infrastructure.

## Goals / Non-Goals

**Goals:**

- Threaded discussion model that supports tree-structured replies in the backend
- Flat discussion UI on the frontend (replies shown as children of root discussion, not nested)
- Notification system that respects user-chosen frequency (immediate / hourly / daily / never)
- User-level notification frequency setting applying to all projects
- Reworked project page with title banner and Info/Discussions navigation
- Discussions at a separate dynamic route (auth-gated, dynamic content)

**Non-Goals:**

- Per-project notification settings (deferred)
- Project-level settings model (deferred)
- Moving `opt_in_to_external_promotions` to project level (deferred)
- Nested/threaded reply rendering in the frontend (backend supports it, UI doesn't yet)
- Rich text or markdown in discussions (plain text only for now)
- Real-time updates via WebSockets (page refresh or polling is fine)
- Moderation tools beyond basic delete-own-comment
- Push notifications or in-app notification inbox
- Discussion reactions, voting, or pinning

## Decisions

### 1. Discussion model: adjacency list with `parent` self-FK

Store discussions and replies in a single `Discussion` model with a nullable `parent` foreign key and a required `project` foreign key. Root discussions have `parent=NULL`. Replies point to their parent.

**Why over materialised path or nested sets:** Adjacency list is simplest, the dataset is small (per-project discussions), and we only need one level of nesting in the UI right now. Django's ORM handles self-referential FKs well. If we ever need deep tree queries, we can add `django-tree-queries` later.

### 2. New `discussions` Django app with separate service

Discussions get their own app at `apps/discussions/` with their own models, keeping the projects app focused. The service layer follows the established pattern: `services/discussions/handler_interface.py`, `query_interface.py`, and `django_impl/`.

**Why not extend projects:** Separation of concerns. Discussions have their own lifecycle, permissions, and query patterns. Co-locating would bloat the projects app.

### 3. New `notifications` Django app with separate service

A `Notification` model tracks: recipient, source discussion, notification type, delivery status, and the user's cadence preference at creation time. The notifications service handles creation and delivery.

**Why snapshot cadence at creation:** If a user changes their frequency preference, in-flight notifications should honour the preference at the time they were generated, not the new one.

### 4. Notification frequency as an enum: IMMEDIATE / HOURLY / DAILY / NEVER

Stored as a CharField with choices on the User model. The frontend renders this as a sticky sliding scale in user settings.

**Why not a numeric interval:** The delivery is batch-based (immediate on event, hourly cron, daily cron), so discrete buckets map directly to implementation. A freeform interval would complicate batching.

**Why user-level only:** Keeps the initial implementation simple. Per-project overrides can be added later when project settings are introduced.

### 5. Notification deduplication: one notification per user per comment

When a comment is created, the discussions service enqueues a task that collects the set of users to notify (project owner + discussion creator + participants), deduplicates, excludes the comment author, and creates one `Notification` row per user.

**Why at creation time, not delivery time:** Deduplicating at creation avoids storing redundant rows and simplifies the batch delivery queries.

### 6. Discussions at a separate route, not a query param

Discussions live at `/projects/[id]/discussions` as a separate Next.js page. The project info page remains statically generated at `/projects/[id]`. Both pages share the reworked title banner layout, with navigation links between Info and Discussions.

**Why separate routes:** Discussions are dynamic, auth-gated content. Mixing dynamic content into a statically generated page would either require client-side fetching within a static shell (defeating SSG benefits) or force the entire page to be dynamically rendered. A separate route lets each page use the rendering strategy that fits its content.

### 7. API authentication: discussions require login

All discussion endpoints (`GET /projects/{id}/discussions`, `POST`, etc.) require JWT authentication. Unauthenticated users see a "sign up to join the conversation" prompt in the frontend.

**Why require auth for reading too:** Discussions are community content for members. Requiring auth for reads encourages sign-ups and keeps the content within the community.

## Risks / Trade-offs

**[Performance] Notification fan-out on popular discussions** → For now, discussions are per-project with a small user base. If a discussion gets many participants, the notification creation task could be slow. Mitigation: the task is async, so it doesn't block the comment API response. Monitor task queue depth.

**[UX] Flat reply rendering loses threading context** → Mitigate by showing "replying to @user" text on replies so readers can follow the conversation. The backend stores the tree, so threaded rendering can be added later.

**[Delivery] Email rate limiting** → Scaleway SMTP has rate limits. Immediate notifications send one email per notification. Hourly/daily batches send digest emails (one per user). Monitor bounce rates and delivery failures.

**[Data] Cascade deletes** → If a user deletes their account, their discussions remain (author set to null or marked as deleted user). If a project is deleted, cascade deletes handle discussions and notifications.

## Migration Plan

1. Deploy backend changes with new apps, models, and migrations (discussions, notifications)
2. Deploy API changes (new routers for discussions, user schema updated with notification frequency)
3. Deploy frontend changes (project page rework, discussions route, user settings UI)
4. Deploy scheduled tasks (hourly and daily notification batch jobs)

**Rollback:** Each step is independently reversible. No breaking migrations — only additive changes.

## Open Questions

- Should discussion deletion be soft-delete (mark as deleted, hide from UI) or hard-delete? Soft-delete preserves reply context but adds complexity.
- Should project owners be able to lock/close discussions on their project?
- What should the notification email template look like? Simple text summary, or styled HTML matching the platform brand?
