## MODIFIED Requirements

### Requirement: Notification model

The system SHALL store notifications in a `Notification` model with: id (UUID), recipient (FK to User), discussion (FK to Discussion), email_cadence (CharField with choices: IMMEDIATE, HOURLY, DAILY, NEVER), email_sent (boolean, default false), email_sent_at (nullable datetime), in_app_read_at (nullable datetime), and created_at.

The email_cadence SHALL be snapshotted from the recipient's `notification_frequency` at the time of notification creation.

The model SHALL have a database index supporting access by `(recipient_id, in_app_read_at)` to keep unread-feed and summary queries cheap.

#### Scenario: Notification created with user's current cadence
- **WHEN** a notification is created for a user whose `notification_frequency` is HOURLY
- **THEN** the notification's `email_cadence` field SHALL be set to HOURLY

#### Scenario: Changing user preference does not affect existing notifications
- **WHEN** a user changes their `notification_frequency` from HOURLY to DAILY
- **THEN** existing notifications for that user SHALL retain their original `email_cadence` value

#### Scenario: New notification has unread in-app state
- **WHEN** a notification row is created
- **THEN** `in_app_read_at` SHALL be NULL (the user has not yet read it in-app)

### Requirement: Notifications service layer

The system SHALL expose notification operations through a service layer following the handler/repository pattern. The handler SHALL be registered in `services/__init__.py` as `HANDLERS.notifications`. Read-only queries SHALL be registered as `REPO.notifications`.

The handler interface SHALL support:
- `create_notifications_for_discussion(discussion_id)` — creates notifications for all relevant users
- `send_immediate_notifications()` — sends all unsent notifications with IMMEDIATE cadence
- `send_batch_notifications(cadence)` — sends all unsent notifications with the given cadence as a digest
- `list_unread_groups_for_user(user_id, limit)` — returns a list of `NotificationGroup` aggregates of the user's unread notifications
- `get_unread_summary_for_user(user_id)` — returns a `NotificationSummary` with `has_unread` and `unread_group_count`
- `mark_thread_read_for_user(user_id, root_discussion_id)` — marks all unread rows for the user belonging to the given root discussion as read; returns the count marked
- `delete_old_read_notifications()` — deletes rows where `in_app_read_at IS NOT NULL` and `in_app_read_at < now() - 30 days`; returns the count deleted

#### Scenario: Service is accessible via HANDLERS and REPO
- **WHEN** code imports `from services import HANDLERS, REPO`
- **THEN** `HANDLERS.notifications` and `REPO.notifications` are available

### Requirement: Immediate notification delivery

When a notification is created with IMMEDIATE cadence, the system SHALL send an email to the recipient as part of the notification creation flow. When the recipient's `notification_frequency` is NEVER, the notification row SHALL still be created (so it appears as an in-app notification) but no email SHALL be dispatched.

#### Scenario: Immediate notification sends email
- **WHEN** a notification with IMMEDIATE cadence is created
- **THEN** an email is sent to the recipient and the notification is marked with `email_sent=True` and `email_sent_at=now()`

#### Scenario: User with NEVER cadence receives in-app but no email
- **WHEN** a user has `notification_frequency` set to NEVER and an event eligible for them is created
- **THEN** a notification row IS created for them with `email_cadence=NEVER`, `email_sent=False`, `in_app_read_at=NULL`
- **AND** no email is sent

### Requirement: Hourly notification batch task

The system SHALL have a django-task that runs hourly, collects all unsent notifications with HOURLY cadence whose recipient has not already read them in-app, groups them by recipient, and sends a single digest email per user.

#### Scenario: Hourly batch sends digest
- **WHEN** the hourly task runs and user A has 3 unsent HOURLY notifications with `in_app_read_at IS NULL`
- **THEN** one digest email is sent to user A covering all 3 notifications, and all 3 are marked with `email_sent=True` and `email_sent_at=now()`

#### Scenario: Hourly batch skips notifications already read in-app
- **WHEN** the hourly task runs and user A has 3 unsent HOURLY notifications, 2 of which have `in_app_read_at IS NOT NULL`
- **THEN** the digest covers only the 1 unread-in-app notification
- **AND** the 2 already-read-in-app notifications remain `email_sent=False` (no email is sent for them)

#### Scenario: Hourly batch with no eligible notifications
- **WHEN** the hourly task runs and there are no unsent HOURLY notifications with `in_app_read_at IS NULL`
- **THEN** no emails are sent

### Requirement: Daily notification batch task

The system SHALL have a django-task that runs daily, collects all unsent notifications with DAILY cadence whose recipient has not already read them in-app, groups them by recipient, and sends a single digest email per user.

#### Scenario: Daily batch sends digest
- **WHEN** the daily task runs and user A has 5 unsent DAILY notifications with `in_app_read_at IS NULL`
- **THEN** one digest email is sent to user A covering all 5 notifications, and all 5 are marked with `email_sent=True` and `email_sent_at=now()`

#### Scenario: Daily batch skips notifications already read in-app
- **WHEN** the daily task runs and user A has 5 unsent DAILY notifications, 4 of which have `in_app_read_at IS NOT NULL`
- **THEN** the digest covers only the 1 unread-in-app notification
- **AND** the 4 already-read-in-app notifications remain `email_sent=False`

### Requirement: Notification email content

Notification emails SHALL identify the project, the discussion, and the comment body. Digest emails SHALL list all new comments grouped by discussion. The CTA link in each email SHALL deep-link to `/projects/<slug>?comment=<id>` where `<id>` is the relevant comment id (the triggering comment for IMMEDIATE; for digest, the latest comment in each grouped discussion).

#### Scenario: Immediate notification email content
- **WHEN** an immediate notification email is sent for a reply by user B on project "MyApp" with discussion comment id `c-123`
- **THEN** the email SHALL include the project name, the comment author's name, the comment body, and a CTA URL of the form `/projects/<slug-for-MyApp>?comment=c-123`

#### Scenario: Digest notification email content
- **WHEN** a digest email is sent with notifications across 2 discussions on 2 projects
- **THEN** the email SHALL group comments by project and discussion, showing each comment's author and body, and the CTA link for each grouped discussion SHALL deep-link to that discussion's most recent comment id

## ADDED Requirements

### Requirement: Notification summary endpoint

The system SHALL provide `GET /api/notifications/summary` that returns the calling user's unread-notification summary as `{ has_unread: bool, unread_group_count: int }`. The endpoint SHALL require authentication. The endpoint SHALL be implemented in the API layer as a thin pass-through to `HANDLERS.notifications.get_unread_summary_for_user` and SHALL NOT access ORM models directly.

The `unread_group_count` SHALL be the number of distinct root discussions across the user's unread notifications (i.e. coalesced count, not raw row count).

#### Scenario: User has no unread notifications
- **WHEN** an authenticated user with no unread notifications requests `GET /api/notifications/summary`
- **THEN** the response is `{ "has_unread": false, "unread_group_count": 0 }`

#### Scenario: User has unread notifications across two threads
- **WHEN** an authenticated user has 4 unread notifications belonging to 2 distinct root discussions
- **THEN** `GET /api/notifications/summary` returns `{ "has_unread": true, "unread_group_count": 2 }`

#### Scenario: Authentication required
- **WHEN** an unauthenticated request hits `GET /api/notifications/summary`
- **THEN** the system returns 401 Unauthorized

### Requirement: Notification groups endpoint

The system SHALL provide `GET /api/notifications/groups` that returns the calling user's unread notifications coalesced by root discussion, ordered by latest event time descending. The endpoint SHALL accept an optional `limit` query parameter (default reasonable, e.g. 50). The endpoint SHALL require authentication.

Each group SHALL include: root discussion id, project (id, slug, name, image), `headline_kind` ("started" or "replied"), an ordered deduplicated list of actor display names, the latest comment body excerpt (truncated), the latest event timestamp, the unread count, and the latest notification's comment id (for deep-linking).

The endpoint SHALL be implemented as a thin pass-through to `HANDLERS.notifications.list_unread_groups_for_user` and SHALL NOT access ORM models directly.

#### Scenario: User with unread notifications sees coalesced groups
- **GIVEN** user A has unread notifications: one for a new discussion D1 by Bob on project P, and three for replies by Carol, Dave, and Eve on a separate discussion D2 on project Q
- **WHEN** A requests `GET /api/notifications/groups`
- **THEN** the response contains two group objects: one for D1 (headline_kind "started", actors [Bob], unread_count 1) and one for D2 (headline_kind "replied", actors [Eve, Dave, Carol] in latest-first order, unread_count 3)

#### Scenario: Read notifications are excluded from groups
- **GIVEN** user A has 2 unread notifications and 5 read notifications
- **WHEN** A requests `GET /api/notifications/groups`
- **THEN** the response only reflects unread notifications

#### Scenario: Authentication required
- **WHEN** an unauthenticated request hits `GET /api/notifications/groups`
- **THEN** the system returns 401 Unauthorized

### Requirement: Mark thread read endpoint

The system SHALL provide `POST /api/notifications/mark-thread-read` that marks all of the calling user's unread notifications belonging to a given root discussion as read. The body SHALL accept `{ root_discussion_id: UUID }`. The endpoint SHALL require authentication and SHALL be idempotent. The response SHALL be `{ marked: <int> }`.

The endpoint SHALL be implemented as a thin pass-through to `HANDLERS.notifications.mark_thread_read_for_user` and SHALL NOT access ORM models directly.

The handler SHALL set `in_app_read_at = now()` on every unread row belonging to the given user and root discussion. Other users' rows SHALL NOT be affected.

#### Scenario: Marks all unread rows for the thread
- **GIVEN** user A has 3 unread notifications all for root discussion R, and 2 unread notifications for an unrelated thread S
- **WHEN** A sends `POST /api/notifications/mark-thread-read` with `root_discussion_id = R`
- **THEN** all 3 R-rows have `in_app_read_at` set to the current time
- **AND** the 2 S-rows are unaffected
- **AND** the response is `{ "marked": 3 }`

#### Scenario: Idempotent on already-read thread
- **GIVEN** user A has no unread notifications for root discussion R (all already read)
- **WHEN** A sends `POST /api/notifications/mark-thread-read` with `root_discussion_id = R`
- **THEN** no rows change
- **AND** the response is `{ "marked": 0 }` with HTTP 200

#### Scenario: Scoped to caller
- **GIVEN** user A and user B both have unread notifications for root discussion R
- **WHEN** A sends `POST /api/notifications/mark-thread-read` with `root_discussion_id = R`
- **THEN** A's R-rows are marked read
- **AND** B's R-rows are unaffected

#### Scenario: Authentication required
- **WHEN** an unauthenticated request hits `POST /api/notifications/mark-thread-read`
- **THEN** the system returns 401 Unauthorized

### Requirement: Notification retention task

The system SHALL provide a django-task `delete_old_read_notifications` that deletes `Notification` rows where `in_app_read_at IS NOT NULL` AND `in_app_read_at < now() - 30 days`. Rows with `in_app_read_at IS NULL` SHALL NOT be deleted by this task regardless of their age.

The task SHALL delegate to `HANDLERS.notifications.delete_old_read_notifications`. The cron schedule that invokes the task is defined outside this repository.

#### Scenario: Deletes old read rows
- **GIVEN** a notification row with `in_app_read_at = now() - 31 days`
- **WHEN** `delete_old_read_notifications` runs
- **THEN** the row is deleted

#### Scenario: Preserves recent read rows
- **GIVEN** a notification row with `in_app_read_at = now() - 10 days`
- **WHEN** `delete_old_read_notifications` runs
- **THEN** the row is retained

#### Scenario: Preserves unread rows of any age
- **GIVEN** a notification row with `in_app_read_at IS NULL` created 90 days ago
- **WHEN** `delete_old_read_notifications` runs
- **THEN** the row is retained
