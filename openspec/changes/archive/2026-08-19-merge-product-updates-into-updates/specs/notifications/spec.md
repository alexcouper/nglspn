## MODIFIED Requirements

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
