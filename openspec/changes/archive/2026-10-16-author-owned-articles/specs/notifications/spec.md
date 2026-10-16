# Spec Delta

## MODIFIED Requirements

### Requirement: Article-publish notification creation service

The notifications service layer SHALL expose `create_notifications_for_article(article_id)` on `HANDLERS.notifications`. The handler SHALL:

1. Load the Article. Return early without creating notifications if the article does not exist (log a warning) or if `article.state != 'published'`.
2. For every `FollowedChannel(_, article.channel)` row, create a `Notification` row with `recipient = follow.user`, `article = article`, `email_cadence = follow.user.article_email_frequency`. Rows that match the partial unique constraint are left alone (no duplicate). The channel is the project's channel for a project article and the author's personal channel for an author-owned one; the selection is by channel alone, not by the follow's project.
3. The author of the article SHALL be excluded from fan-out (even if they follow the channel via the auto-follow path).
4. The created row's `in_app_read_at` SHALL be `NULL` (unread, surfaces in-app) — no preference check.
5. The row is enqueued for the email digest worker on the user's cadence bucket. **No `immediate` path exists for article notifications.** When `article_email_frequency = never`, the row is created (so in-app surfaces work) but no digest task SHALL ever send the email.
6. When the article's channel belongs to the house project (the channel has a project and `project.is_house_project = True`), the handler SHALL emit a structured `logger.info` line per recipient row created (see `House-channel article fan-out observability` requirement below). A person's channel has no project and is never a house channel.

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

#### Scenario: Author-owned article reaches the person's followers

- **GIVEN** an author-owned Article by U published in U's personal channel C; V has a `FollowedChannel(_, C)` row
- **WHEN** `create_notifications_for_article` runs
- **THEN** a Notification row exists for V
- **AND** no `house_channel_article_enqueued` log line is emitted

### Requirement: Notification groups endpoint exposes article groups

The `GET /api/notifications/groups` response SHALL include article-notification groups in addition to discussion groups. Article notifications coalesce per Article (one group per Article — not per channel or per project).

Each article group SHALL include: a `kind` field with value `article`, the Article id, the project (id, slug, name, image) — null for an author-owned article — the author (id, display name, avatar URL), the channel name, the Article title, an excerpt of the Article body (truncated), the latest event timestamp, and an unread count (always 1 for article notifications, since they coalesce 1:1 per Article). The in-app rendering SHALL head an author-owned group with the author's name and avatar and deep-link to the article's `/users/{id}/articles/{slug}` URL.

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

#### Scenario: Author-owned article group
- **GIVEN** user U has 1 unread notification for an author-owned Article A by V
- **WHEN** U calls `GET /api/notifications/groups`
- **THEN** the article group has `project = null` and `author` carrying V's id, name and avatar URL
- **AND** the bell renders it headed by V's name, linking to A's `/users/{V.id}/articles/{slug}` URL
