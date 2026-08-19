## Purpose

The system delivers user-visible notifications for discussion activity on projects. Notifications are stored in a model, dispatched on a cadence (immediate / hourly / daily / never), and addressed to project contributors plus discussion participants while excluding the triggering author.
## Requirements
### Requirement: Notification model

The system SHALL store notifications in a `Notification` model with: id (UUID), recipient (FK to User), discussion (FK to Discussion, nullable), article (FK to Article, nullable), email_cadence (CharField; choices defined per-kind — see below), email_sent (boolean, default false), email_sent_at (nullable datetime), in_app_read_at (nullable datetime), and created_at.

Exactly one of `discussion` and `article` SHALL be set on every row. This SHALL be enforced by a CHECK constraint (`(discussion_id IS NULL) != (article_id IS NULL)`) on Postgres and by a save-time guard on SQLite. The `(recipient, discussion)` and `(recipient, article)` partial unique constraints continue to apply.

`email_cadence` SHALL be snapshotted from the recipient's *kind-appropriate* User field at the time of notification creation:

- For a discussion notification: `recipient.discussion_email_frequency` (choices `immediate | hourly | daily | never`).
- For an article notification: `recipient.article_email_frequency` (choices `hourly | daily | weekly | never`).

The snapshot semantics are unchanged: changing the user's setting after a row is created does NOT mutate the row's `email_cadence`. A row's `email_cadence` controls only which digest worker picks it up; in-app rendering is unaffected.

The model SHALL have a database index supporting access by `(recipient_id, in_app_read_at)` to keep unread-feed and summary queries cheap.

#### Scenario: Discussion notification snapshots discussion_email_frequency

- **WHEN** a discussion notification is created for a user whose `discussion_email_frequency` is `hourly`
- **THEN** the notification's `email_cadence` SHALL be `hourly`

#### Scenario: Article notification snapshots article_email_frequency

- **WHEN** an article notification is created for a user whose `article_email_frequency` is `weekly`
- **THEN** the notification's `email_cadence` SHALL be `weekly`

#### Scenario: Changing user preference does not affect existing notifications

- **WHEN** a user changes their `discussion_email_frequency` from `hourly` to `daily`
- **THEN** existing notifications for that user SHALL retain their original `email_cadence` value

#### Scenario: New notification has unread in-app state

- **WHEN** a notification row is created
- **THEN** `in_app_read_at` SHALL be NULL

#### Scenario: Discussion notification has null article FK

- **WHEN** a Notification is created pointing at a Discussion D
- **THEN** the row's `discussion` SHALL be D
- **AND** the row's `article` SHALL be NULL

#### Scenario: Article notification has null discussion FK

- **WHEN** a Notification is created pointing at an Article A
- **THEN** the row's `article` SHALL be A
- **AND** the row's `discussion` SHALL be NULL

#### Scenario: Cannot save with both FKs set

- **WHEN** a Notification is saved with both `discussion` and `article` set
- **THEN** the save SHALL fail

#### Scenario: Cannot save with neither FK set

- **WHEN** a Notification is saved with both `discussion` and `article` NULL
- **THEN** the save SHALL fail

#### Scenario: Same user gets one Notification per Article

- **GIVEN** a user U and an Article A
- **WHEN** an attempt is made to insert two Notification rows with `recipient = U` and `article = A`
- **THEN** the second insert SHALL fail due to the partial unique constraint

### Requirement: Notifications Django app

The system SHALL have a dedicated Django app at `apps/notifications/` with its own models, admin registration, and migrations. The app SHALL be registered in Django settings.

#### Scenario: App is registered
- **WHEN** Django starts
- **THEN** the `apps.notifications` app is loaded and its models are available

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

### Requirement: User notification frequency setting

The User model SHALL provide two CharField cadence settings — one per notification kind — each with its own choice set and default:

- `discussion_email_frequency` — choices `immediate | hourly | daily | never`, default `hourly`.
- `article_email_frequency` — choices `hourly | daily | weekly | never`, default `hourly`.

Both fields SHALL be editable via the user-update API and the frontend settings page.

Each field SHALL govern only email delivery. In-app notifications SHALL be created regardless of either field's value (when the recipient is in scope for a fan-out path), so the bell, popover, feed, and toaster surfaces are not gated by these settings.

`discussion_email_frequency` SHALL replace the prior `notification_frequency` field. The data migration that introduces the new field SHALL copy each user's existing `notification_frequency` value into `discussion_email_frequency` 1:1 (all four choice labels are preserved). A follow-up migration drops `notification_frequency` from the schema after the code stops reading it.

`article_email_frequency` SHALL be added with default `hourly` for new and existing users. There is no per-user backfill of a meaningful value — every user receives the default.

#### Scenario: Default cadences for a new user

- **WHEN** a new user registers
- **THEN** `discussion_email_frequency` SHALL be `hourly`
- **AND** `article_email_frequency` SHALL be `hourly`

#### Scenario: User updates discussion cadence

- **WHEN** a user updates `discussion_email_frequency` to `daily` via the API
- **THEN** the value is persisted
- **AND** future discussion notifications for that user are created with `email_cadence = daily`

#### Scenario: User updates article cadence

- **WHEN** a user updates `article_email_frequency` to `weekly` via the API
- **THEN** the value is persisted
- **AND** future article notifications for that user are created with `email_cadence = weekly`

#### Scenario: Migration copies prior notification_frequency to discussion_email_frequency

- **GIVEN** an existing user U with `notification_frequency = daily`
- **WHEN** the field-rename migration runs
- **THEN** `U.discussion_email_frequency` SHALL be `daily`
- **AND** `U.article_email_frequency` SHALL be `hourly` (the new field's default)

#### Scenario: In-app fan-out is independent of cadence fields

- **GIVEN** a user U with `discussion_email_frequency = never` and `article_email_frequency = never`
- **WHEN** an article in a channel U follows is published
- **THEN** an in-app Notification row is still created for U
- **AND** the row's `email_cadence` is `never` so no email is ever sent

### Requirement: Immediate notification delivery

When a discussion notification is created with `email_cadence = immediate`, the system SHALL send a single-thread email to the recipient as part of the fan-out flow. Row state transitions to `email_sent = True`, `email_sent_at = now()` at send time.

The `immediate` value is only available on `discussion_email_frequency`. There is **no** immediate-email path for article notifications — every article notification flows through one of the digest workers (or is never emailed, when `email_cadence = never`).

When the recipient's `discussion_email_frequency` is `never`, the discussion notification row is still created (so it appears in-app) but no email is dispatched.

#### Scenario: Immediate discussion notification sends an email

- **WHEN** a discussion notification with `email_cadence = immediate` is created
- **THEN** an email is sent to the recipient
- **AND** the row is marked `email_sent = True`, `email_sent_at = now()`

#### Scenario: User with never receives in-app but no email (discussion)

- **WHEN** a user has `discussion_email_frequency = never` and a discussion event eligible for them fires
- **THEN** a Notification row IS created with `email_cadence = never`, `email_sent = False`, `in_app_read_at = NULL`
- **AND** no email is sent

#### Scenario: Article notifications never send via the immediate path

- **WHEN** an article notification is created (any cadence)
- **THEN** no synchronous email send is invoked for that row at fan-out time

### Requirement: Hourly notification batch task

The system SHALL run two hourly digest tasks, one per kind:

- The hourly discussion digest collects all unsent discussion notifications with `email_cadence = hourly` whose recipient has not already read them in-app, groups them by recipient, and sends one discussion-digest email per user.
- The hourly article digest collects all unsent article notifications with `email_cadence = hourly` whose recipient has not already read them in-app, groups them by recipient, and sends one article-digest email per user.

Each task marks the rows it sends `email_sent = True`, `email_sent_at = now()`. A user on hourly-for-both with new rows of both kinds in the same window SHALL receive two emails (one per kind). The system SHALL NOT coalesce kinds into a single email.

#### Scenario: Hourly discussion batch sends a discussion digest

- **WHEN** the hourly discussion task runs and user A has 3 unsent discussion notifications with `email_cadence = hourly` and `in_app_read_at IS NULL`
- **THEN** one discussion-digest email is sent to user A covering all 3 notifications
- **AND** all 3 are marked `email_sent = True`

#### Scenario: Hourly article batch sends an article digest

- **WHEN** the hourly article task runs and user A has 2 unsent article notifications with `email_cadence = hourly` and `in_app_read_at IS NULL`
- **THEN** one article-digest email is sent to user A covering both notifications
- **AND** both are marked `email_sent = True`

#### Scenario: Hourly batches skip notifications already read in-app

- **WHEN** the hourly task of either kind runs and user A has 3 unsent eligible notifications, 2 of which have `in_app_read_at IS NOT NULL`
- **THEN** the digest covers only the 1 unread-in-app notification
- **AND** the 2 already-read-in-app notifications remain `email_sent = False`

#### Scenario: Same hour, two distinct emails when both kinds have content

- **GIVEN** user A has unsent eligible discussion notifications AND unsent eligible article notifications on the same hourly tick
- **WHEN** the hourly tasks run
- **THEN** A receives one discussion-digest email AND one article-digest email
- **AND** the system SHALL NOT combine them into a single email

### Requirement: Daily notification batch task

The system SHALL run two daily digest tasks, one per kind. The discussion daily task collects unsent discussion notifications with `email_cadence = daily`. The article daily task collects unsent article notifications with `email_cadence = daily`. Both behave like their hourly counterparts otherwise.

#### Scenario: Daily discussion batch sends a discussion digest

- **WHEN** the daily discussion task runs and user A has 5 unsent discussion notifications with `email_cadence = daily` and `in_app_read_at IS NULL`
- **THEN** one discussion-digest email is sent to user A covering all 5

#### Scenario: Daily article batch sends an article digest

- **WHEN** the daily article task runs and user A has 4 unsent article notifications with `email_cadence = daily` and `in_app_read_at IS NULL`
- **THEN** one article-digest email is sent to user A covering all 4

### Requirement: Notification email content

Discussion notification emails (immediate and digest) SHALL identify the project, the discussion, and the comment body. Digest discussion emails SHALL list all new comments grouped by discussion. The CTA link SHALL deep-link to `/projects/<slug>?comment=<id>` where `<id>` is the relevant comment id.

Article digest emails SHALL list new articles. Each article entry SHALL include the project name, the article title, the channel name, and a short body excerpt (one paragraph or less), with a CTA link of the form `/projects/<project-slug>/articles/<article-slug>`.

Discussion and article emails SHALL be separate emails — there SHALL NOT be a "mixed" digest that combines both kinds.

#### Scenario: Immediate discussion email content

- **WHEN** an immediate discussion notification email is sent for a reply by user B on project "MyApp" with comment id `c-123`
- **THEN** the email SHALL include the project name, the comment author's name, the comment body, and a CTA URL of `/projects/<slug-for-MyApp>?comment=c-123`

#### Scenario: Discussion digest content

- **WHEN** a discussion digest email is sent containing notifications across 2 discussions on 2 projects
- **THEN** the email SHALL group comments by project and discussion
- **AND** each grouped discussion's CTA SHALL deep-link to its most recent comment id

#### Scenario: Article digest content

- **WHEN** an article digest email is sent containing 3 article notifications across 2 projects
- **THEN** the email SHALL list each article with project name, title, channel, and a short body excerpt
- **AND** each article entry's CTA SHALL be `/projects/<project-slug>/articles/<article-slug>`

#### Scenario: Discussion and article content are not mixed

- **WHEN** a user receives both digest types on the same tick
- **THEN** the discussion digest email SHALL NOT contain article content
- **AND** the article digest email SHALL NOT contain discussion content

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

The system SHALL provide `POST /api/notifications/mark-thread-read` that marks all of the calling user's unread notifications belonging to a given root discussion as read. The body SHALL be a one-of: exactly one of `root_discussion_id: UUID` or `comment_id: UUID`. When `comment_id` is given, the backend SHALL resolve the comment's root discussion (the comment itself if it is a root, otherwise the comment's parent) and mark that thread. When neither or both fields are provided, the request SHALL be rejected with HTTP 422. The endpoint SHALL require authentication and SHALL be idempotent. The response SHALL be `{ marked: <int> }`.

The endpoint SHALL be implemented as a thin pass-through to `HANDLERS.notifications.mark_thread_read_for_user` (or `mark_thread_read_for_comment` for the comment-id path) and SHALL NOT access ORM models directly.

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

#### Scenario: Marks thread when only comment id is known
- **GIVEN** user A has 2 unread notifications, one for root discussion R and one for its reply C
- **WHEN** A sends `POST /api/notifications/mark-thread-read` with `comment_id = C` (no `root_discussion_id`)
- **THEN** the backend resolves C's root (R) and marks both rows read
- **AND** the response is `{ "marked": 2 }`

#### Scenario: Rejects request with both fields or neither field
- **WHEN** an authenticated client sends a request body containing both `root_discussion_id` and `comment_id`, or neither
- **THEN** the system returns 422 Unprocessable Entity

#### Scenario: Authentication required
- **WHEN** an unauthenticated request hits `POST /api/notifications/mark-thread-read`
- **THEN** the system returns 401 Unauthorized

### Requirement: Mark all read endpoint

The system SHALL provide `POST /api/notifications/mark-all-read` that marks every one of the calling user's unread in-app notifications as read in a single request. The endpoint SHALL require authentication and SHALL be idempotent. The response SHALL be `{ marked: <int> }`.

The endpoint SHALL be implemented as a thin pass-through to `HANDLERS.notifications.mark_all_read_for_user` and SHALL NOT access ORM models directly.

The handler SHALL set `in_app_read_at = now()` on every unread row belonging to the calling user. Other users' rows SHALL NOT be affected.

#### Scenario: Marks every unread row for the caller
- **GIVEN** user A has 5 unread notifications spread across multiple threads
- **WHEN** A sends `POST /api/notifications/mark-all-read`
- **THEN** all 5 of A's rows have `in_app_read_at` set to the current time
- **AND** the response is `{ "marked": 5 }`

#### Scenario: Idempotent when nothing is unread
- **GIVEN** user A has no unread notifications
- **WHEN** A sends `POST /api/notifications/mark-all-read`
- **THEN** no rows change
- **AND** the response is `{ "marked": 0 }` with HTTP 200

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

### Requirement: Article-publish notification creation service

The notifications service layer SHALL expose `create_notifications_for_article(article_id)` on `HANDLERS.notifications`. The handler SHALL:

1. Load the Article. Return early without creating notifications if the article does not exist (log a warning) or if `article.state != 'published'`.
2. For every `FollowedChannel(_, article.channel)` row, create a `Notification` row with `recipient = follow.user`, `article = article`, `email_cadence = follow.user.article_email_frequency`. Rows that match the partial unique constraint are left alone (no duplicate).
3. The author of the article SHALL be excluded from fan-out (even if they follow the channel via the auto-follow path).
4. The created row's `in_app_read_at` SHALL be `NULL` (unread, surfaces in-app) — no preference check.
5. The row is enqueued for the email digest worker on the user's cadence bucket. **No `immediate` path exists for article notifications.** When `article_email_frequency = never`, the row is created (so in-app surfaces work) but no digest task SHALL ever send the email.
6. When the article's channel belongs to the house project (`article.channel.project.is_house_project = True`), the handler SHALL emit a structured `logger.info` line per recipient row created (see `House-channel article fan-out observability` requirement below).

Backdated-publish suppression is **not** the responsibility of this method — `HANDLERS.articles.publish` decides whether to invoke it for a given publish.

#### Scenario: Followers of the channel receive notifications

- **GIVEN** an Article published in channel C; followers U1 and U2 both have a `FollowedChannel(_, C)` row
- **WHEN** `create_notifications_for_article` runs
- **THEN** a Notification row exists for U1 and U2
- **AND** each row has `in_app_read_at = NULL`
- **AND** each row's `email_cadence` is set from the respective user's `article_email_frequency`

#### Scenario: Users not following the channel get no notification

- **GIVEN** an Article published in channel C; user U3 has a `Follow` on the project but no `FollowedChannel(_, C)` row
- **WHEN** `create_notifications_for_article` runs
- **THEN** no Notification row is created for U3

#### Scenario: Article author is not notified

- **GIVEN** an Article authored by U; U has a `FollowedChannel` on the article's channel
- **WHEN** `create_notifications_for_article` runs
- **THEN** no Notification row SHALL be created for U

#### Scenario: Recipient on never still gets the in-app row

- **GIVEN** an Article published in channel C; user U has a `FollowedChannel(_, C)` row and `article_email_frequency = never`
- **WHEN** `create_notifications_for_article` runs
- **THEN** a Notification row exists for U with `email_cadence = never`
- **AND** the row's `in_app_read_at` is NULL (it appears in the bell)
- **AND** no digest task SHALL ever mark this row `email_sent = True`

#### Scenario: Article in draft state is a no-op

- **GIVEN** an Article with `state = draft`
- **WHEN** `create_notifications_for_article` is invoked
- **THEN** no Notification rows SHALL be created

### Requirement: Article notification email content

Immediate and digest notification emails SHALL include rendered article notifications alongside discussion notifications. For each article notification, the email SHALL include the project name, the article title, the channel name, and a CTA link of the form `/projects/<project-slug>/articles/<article-slug>`.

#### Scenario: Immediate article email content
- **WHEN** an immediate notification email is sent for an Article titled "Spring update" on channel "Updates" in project "MyApp" with slug "spring-update"
- **THEN** the email SHALL include the project name, the article title, the channel name
- **AND** the CTA link SHALL be `/projects/<slug-for-MyApp>/articles/spring-update`

#### Scenario: Digest article and discussion content
- **WHEN** a digest email is sent containing 1 article notification and 2 discussion notifications across 2 projects
- **THEN** the email SHALL render both types
- **AND** each article notification SHALL link to the article page
- **AND** each discussion notification SHALL link as previously specified

### Requirement: Notification groups endpoint exposes article groups

The `GET /api/notifications/groups` response SHALL include article-notification groups in addition to discussion groups. Article notifications coalesce per Article (one group per Article — not per channel or per project).

Each article group SHALL include: a `kind` field with value `article`, the Article id, the project (id, slug, name, image), the channel name, the Article title, an excerpt of the Article body (truncated), the latest event timestamp, and an unread count (always 1 for article notifications, since they coalesce 1:1 per Article).

The existing discussion groups SHALL gain a `kind` field with value `discussion` for symmetry.

Ordering across mixed groups SHALL be by latest event timestamp descending.

#### Scenario: Mixed groups returned
- **GIVEN** user U has 1 unread article notification for Article A on project P and 1 unread discussion notification for discussion D on project Q
- **WHEN** U calls `GET /api/notifications/groups`
- **THEN** the response contains two groups
- **AND** one has `kind = "article"` and references A
- **AND** the other has `kind = "discussion"` and references D

#### Scenario: Article notifications coalesce per Article
- **GIVEN** user U has somehow ended up with 2 unread notification rows for the same Article A (e.g. a re-fire path bug) — though the partial unique constraint prevents this in normal operation
- **WHEN** U calls `GET /api/notifications/groups`
- **THEN** one article group is returned with `unread_count = 2`

### Requirement: Mark-thread-read endpoint handles article notifications

The `POST /api/notifications/mark-thread-read` endpoint SHALL accept `article_id: UUID` as a third alternative to `root_discussion_id` and `comment_id`. When `article_id` is given, the handler SHALL mark every unread Notification row belonging to the caller with that `article` FK as read.

The body SHALL remain a one-of: exactly one of `root_discussion_id`, `comment_id`, or `article_id`. Requests with zero or more than one of these keys SHALL be rejected with HTTP 422.

The handler interface SHALL expose `mark_article_read_for_user(user_id, article_id)`.

#### Scenario: Mark article notification read
- **GIVEN** user U has 1 unread Notification row pointing at Article A
- **WHEN** U sends `POST /api/notifications/mark-thread-read` with body `{"article_id": "<A>"}`
- **THEN** the row's `in_app_read_at` SHALL be set
- **AND** the response SHALL be `{ "marked": 1 }`

#### Scenario: Two of {root_discussion_id, comment_id, article_id} returns 422
- **WHEN** a request body contains both `article_id` and `root_discussion_id`
- **THEN** the response SHALL be HTTP 422

### Requirement: Weekly article notification batch task

The system SHALL run a weekly article digest task that collects all unsent article notifications with `email_cadence = weekly` whose recipient has not already read them in-app, groups them by recipient, and sends one article-digest email per user. Rows sent are marked `email_sent = True`, `email_sent_at = now()`.

No weekly task exists for discussions — `discussion_email_frequency` has no `weekly` value.

The exact wall-clock tick (e.g. Monday 09:00 UTC) is a scheduling choice defined in the project's celery / cron configuration, not in this spec.

#### Scenario: Weekly article batch sends a digest

- **WHEN** the weekly article task runs and user A has 12 unsent article notifications with `email_cadence = weekly` and `in_app_read_at IS NULL`
- **THEN** one article-digest email is sent to user A covering all 12
- **AND** all 12 are marked `email_sent = True`

#### Scenario: Weekly batch skips read-in-app rows

- **WHEN** the weekly task runs and user A has 12 unsent eligible rows, 4 of which have `in_app_read_at IS NOT NULL`
- **THEN** the digest covers only the 8 unread-in-app rows

### Requirement: House-channel article fan-out observability

When `create_notifications_for_article` creates a `Notification` row whose article's channel belongs to the house project (`article.channel.project.is_house_project = True`), the handler SHALL emit a structured `logger.info` line with the following fields:

- `event = "house_channel_article_enqueued"`
- `article_id` (UUID)
- `user_id` (UUID — the recipient)
- `channel_id` (UUID)
- `recipient_frequency` (one of `hourly | daily | weekly | never`)
- `article_published_at` (ISO timestamp)

The log line SHALL be emitted regardless of cadence — including `never`. This is the signal used to retrospectively answer "of N expected recipients of a house-channel article, how many had a cadence that would surface it within the first hour?"

The log line SHALL NOT be emitted for non-house-channel articles. The log line SHALL NOT replace or duplicate any other notification-creation log.

The house project's channels are "Updates" and "Competition Winners"; both are house channels for the purposes of this requirement.

#### Scenario: Log line emitted per recipient for a house-channel article

- **GIVEN** an article published on the house project's "Competition Winners" channel; 5 users have a `FollowedChannel` row on that channel
- **WHEN** `create_notifications_for_article` runs
- **THEN** the log SHALL contain 5 `event=house_channel_article_enqueued` lines
- **AND** each line SHALL include the recipient's `user_id` and `recipient_frequency`

#### Scenario: Log line emitted for never-cadence recipients

- **GIVEN** an article published on the house project's "Updates" channel; user U has a `FollowedChannel` row on that channel and `article_email_frequency = never`
- **WHEN** `create_notifications_for_article` runs
- **THEN** the log SHALL contain a `event=house_channel_article_enqueued` line for U
- **AND** the line SHALL include `recipient_frequency=never`

#### Scenario: Non-house-channel articles do not emit the log line

- **GIVEN** an article published on a non-house project's channel
- **WHEN** `create_notifications_for_article` runs
- **THEN** the log SHALL NOT contain any `event=house_channel_article_enqueued` lines for that article

