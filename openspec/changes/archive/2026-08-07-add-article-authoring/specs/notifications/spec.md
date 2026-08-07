## MODIFIED Requirements

### Requirement: Notification model

The system SHALL store notifications in a `Notification` model with: id (UUID), recipient (FK to User), discussion (FK to Discussion, **nullable**), **article (FK to Article, nullable)**, email_cadence (CharField with choices: IMMEDIATE, HOURLY, DAILY, NEVER), email_sent (boolean, default false), email_sent_at (nullable datetime), in_app_read_at (nullable datetime), and created_at.

Exactly one of `discussion` and `article` SHALL be set on every row. This SHALL be enforced by a CHECK constraint (`(discussion_id IS NULL) != (article_id IS NULL)`) on Postgres and by a save-time guard on SQLite. The single unique constraint `(recipient, discussion)` SHALL be replaced by two partial unique constraints: `(recipient, discussion)` where `discussion IS NOT NULL`, and `(recipient, article)` where `article IS NOT NULL`.

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
- **THEN** the save SHALL fail (CHECK constraint on Postgres; save-time guard on SQLite)

#### Scenario: Cannot save with neither FK set
- **WHEN** a Notification is saved with both `discussion` and `article` NULL
- **THEN** the save SHALL fail

#### Scenario: Same user gets one Notification per Article
- **GIVEN** a user U and an Article A
- **WHEN** an attempt is made to insert two Notification rows with `recipient = U` and `article = A`
- **THEN** the second insert SHALL fail due to the partial unique constraint

## ADDED Requirements

### Requirement: Article-publish notification creation service

The notifications service layer SHALL expose `create_notifications_for_article(article_id)` on `HANDLERS.notifications`. The handler SHALL:

1. Load the Article. Return early without creating notifications if the article does not exist (log a warning) or if `article.state != 'published'`.
2. For every `Follow` on `article.project`, look up the `FollowChannelPreference` for `(follow, article.channel)`.
3. For each follower that is not `article.author`: create a Notification row with `recipient = follow.user`, `article = article`, `email_cadence = follow.user.notification_frequency`. Existing rows (matching the partial unique constraint) SHALL be left alone. The row is created when `in_app_enabled = True` OR `email_enabled = True` — when both are off, no row is created.
4. The row's `in_app_read_at` SHALL be `NULL` when `in_app_enabled = True` and set to `now()` (pre-read) when `in_app_enabled = False AND email_enabled = True` — this keeps the row out of in-app surfaces while still letting the email-send bookkeeping live on it.
5. For each newly-created row where `ChannelPreference.email_enabled = True` and `follow.user.notification_frequency != NEVER`: trigger the existing immediate / hourly / daily email path so the email is sent according to cadence. (For IMMEDIATE this fires now; for HOURLY/DAILY the row is picked up by the existing batch task because it has `email_sent = False`.)

Backdated-publish suppression is **not** the responsibility of this method — that decision lives in `HANDLERS.articles.publish`, which only invokes `create_notifications_for_article` for non-backdated publishes. Calling this method directly with a backdated article will fan out notifications. See the corresponding requirement in the `articles` capability for the gating rule.

#### Scenario: Service is accessible via HANDLERS
- **WHEN** code imports `from services import HANDLERS`
- **THEN** `HANDLERS.notifications.create_notifications_for_article` is callable

#### Scenario: Channel preference drives row creation
- **GIVEN** an Article in channel C; followers U1 (`in_app = True, email = True`), U2 (`in_app = True, email = False`), U3 (`in_app = False, email = True`), U4 (`in_app = False, email = False`)
- **WHEN** `create_notifications_for_article` runs
- **THEN** Notification rows SHALL be created for U1, U2 and U3
- **AND** U1's and U2's rows SHALL have `in_app_read_at = NULL` (they surface in-app)
- **AND** U3's row SHALL have `in_app_read_at` set to the current time (it does not surface in-app)
- **AND** no Notification row SHALL be created for U4

#### Scenario: Author of the article is not notified
- **GIVEN** an Article authored by U who also follows their own project with `in_app = True, email = True`
- **WHEN** `create_notifications_for_article` runs
- **THEN** no Notification row SHALL be created for U

#### Scenario: Article in draft state is a no-op
- **GIVEN** an Article with `state = draft` and followers with switches on
- **WHEN** `create_notifications_for_article` is invoked
- **THEN** no Notification rows SHALL be created (defensive check; publish handler never invokes this for drafts in normal operation)

### Requirement: Hourly and daily batch tasks include article notifications

The hourly and daily notification batch tasks SHALL include both discussion-notification rows and article-notification rows in their digest. Per-recipient digest emails SHALL render mixed digests (discussions and articles in one email).

#### Scenario: Mixed digest
- **GIVEN** user U with HOURLY cadence has 1 unsent discussion notification and 2 unsent article notifications, all with `in_app_read_at IS NULL`
- **WHEN** the hourly batch runs
- **THEN** a single digest email SHALL be sent to U covering all 3 notifications
- **AND** all 3 rows SHALL be marked `email_sent = True`

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

## REMOVED Requirements

### Requirement: Notification recipient determination

**Reason**: Recipient resolution is no longer a single concept covering only discussions. The discussion-side rules continue to exist (now scoped under the discussion-publish path) and the article-publish path adds its own recipient resolution via Follow + ChannelPreference. Splitting the single requirement into two source-specific requirements makes both clearer; the discussion-specific scenarios move into the `discussions` capability's spec where they belong.

**Migration**: Discussion-notification recipient rules (system-user exclusion, contributor + author + previous-participant union, dedup) continue to be enforced by `HANDLERS.notifications.create_notifications_for_discussion`. The article-notification recipient rules are specified in the new `Article-publish notification creation service` requirement above (this capability) and in the `Article publish event fans out notifications` requirement in the `articles` capability. The system-user exclusion still applies to the discussion path; for the article path, Follow rows for system users do not exist by construction (see `project-following` spec's `Auto-follow the house project on user creation` requirement, which excludes system users).
