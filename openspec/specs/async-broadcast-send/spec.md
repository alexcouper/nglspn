## Purpose

Asynchronous broadcast email sending via background tasks, replacing synchronous in-request email delivery with a queued workflow that tracks send status.
## Requirements
### Requirement: Broadcast email status tracking

The `BroadcastEmail` model SHALL have a `status` field with values: `draft`, `queued_for_sending`, `sending`, `sent`, `failed`. New broadcasts SHALL default to `draft`. The existing `sent_at` and `sent_by` fields SHALL continue to be set upon successful completion.

#### Scenario: New broadcast defaults to draft
- **WHEN** a new `BroadcastEmail` is created
- **THEN** its `status` SHALL be `draft`

#### Scenario: Status displayed in admin list
- **WHEN** an admin views the broadcast email list
- **THEN** the `status` field SHALL be visible with appropriate badge styling

### Requirement: Admin send enqueues background task

The admin send action SHALL set the broadcast status to `queued_for_sending` and enqueue a background task, then return immediately with a confirmation message. The send action SHALL NOT send emails within the HTTP request cycle.

#### Scenario: Admin clicks send on a draft broadcast
- **WHEN** an admin confirms sending a broadcast with status `draft`
- **THEN** the system SHALL set status to `queued_for_sending`
- **AND** enqueue a `send_broadcast_email` task with the broadcast ID and sending user ID
- **AND** redirect the admin with a message indicating the send has been queued

#### Scenario: Admin attempts to send a non-draft broadcast
- **WHEN** an admin attempts to send a broadcast with status other than `draft`
- **THEN** the system SHALL reject the request with an error message
- **AND** the broadcast status SHALL remain unchanged

### Requirement: Background task claims and sends broadcast

The background task SHALL transition the broadcast from `queued_for_sending` to `sending` before delivering emails. On completion, it SHALL transition to `sent` or `failed`.

#### Scenario: Task picks up a queued broadcast
- **WHEN** the `send_broadcast_email` task executes for a broadcast with status `queued_for_sending`
- **THEN** the system SHALL transition status to `sending`
- **AND** deliver emails to all resolved recipients
- **AND** record each delivery result in `BroadcastEmailRecipient`

#### Scenario: Task completes successfully
- **WHEN** all recipient emails have been attempted (regardless of individual failures)
- **THEN** the system SHALL set status to `sent`
- **AND** set `sent_at` to the current timestamp
- **AND** set `sent_by` to the user who initiated the send

#### Scenario: Task encounters a broadcast not in queued_for_sending state
- **WHEN** the task executes but the broadcast status is not `queued_for_sending`
- **THEN** the task SHALL abort without sending any emails

#### Scenario: Task fails with an unhandled exception
- **WHEN** the task raises an unhandled exception during execution
- **THEN** the system SHALL set status to `failed`

### Requirement: Admin UI reflects async send states

The admin change form SHALL disable the send button for broadcasts that are not in `draft` status. The admin SHALL show appropriate messaging for each status.

#### Scenario: Broadcast is queued or sending
- **WHEN** an admin views a broadcast with status `queued_for_sending` or `sending`
- **THEN** the send button SHALL NOT be available
- **AND** the admin SHALL display the current status

#### Scenario: Broadcast has been sent
- **WHEN** an admin views a broadcast with status `sent`
- **THEN** the send button SHALL NOT be available
- **AND** the admin SHALL display recipient delivery results

### Requirement: Broadcast recipient resolution via Follow preferences

The recipient resolver for `BroadcastEmail` rows whose `email_type` is `competition_results` or `platform_updates` SHALL determine recipients by joining `Follow` and `FollowedChannel` on the Naglasúpan house project (the Project row with `is_house_project = True`).

Mapping:

- `email_type = "competition_results"` → users with a `Follow` on the house project AND a `FollowedChannel` row on the house project's "Competition Winners" channel AND `User.article_email_frequency != "never"`.
- `email_type = "platform_updates"` → users with a `Follow` on the house project AND a `FollowedChannel` row on the house project's "Product Updates" channel AND `User.article_email_frequency != "never"`.

There is no per-channel email switch any more — `FollowedChannel` existence replaces the prior `email_enabled` boolean, and `article_email_frequency` provides the global opt-out lever.

The resolver SHALL exclude:

- Inactive users (`is_active = False`).
- System users (`is_system_user = True`).
- The broadcast's `created_by` user (preserves the existing self-exclusion behaviour).

When no house project exists in the database (greenfield dev / test case), the resolver SHALL return an empty QuerySet and SHALL NOT raise.

The resolver continues to be the **recipient-set** entry point. Broadcast emails are sent through the per-user article-digest path on each recipient's cadence; there is no longer a synchronous send-to-everyone behaviour (see Decision in `simplify-follow-and-cadence/design.md`). Practically, the broadcast task fans each resolved recipient into the article-digest queue and the digest workers deliver them on each user's chosen cadence.

#### Scenario: Competition results broadcast resolves via Competition Winners channel

- **GIVEN** the house project H with channel "Competition Winners" C
- **AND** user U1 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = hourly`
- **AND** user U2 with a `Follow` on H, no `FollowedChannel(_, C)` row
- **AND** user U3 with no `Follow` on H
- **AND** user U4 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = never`
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "competition_results"`
- **THEN** the resulting QuerySet SHALL include U1
- **AND** SHALL NOT include U2, U3, or U4

#### Scenario: Platform updates broadcast resolves via Product Updates channel

- **GIVEN** the house project H with channel "Product Updates" C
- **AND** user U1 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = weekly`
- **AND** user U2 with a `Follow` on H, no `FollowedChannel(_, C)` row
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "platform_updates"`
- **THEN** U1 is included
- **AND** U2 is not included

#### Scenario: Inactive users excluded

- **GIVEN** user U with a `Follow` on H, a `FollowedChannel(_, the relevant channel)` row, and `article_email_frequency = hourly`, but `is_active = False`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: Broadcast author excluded

- **GIVEN** a `BroadcastEmail` with `created_by = U` and `email_type = "platform_updates"`
- **AND** U has a `Follow` on H, a `FollowedChannel` on the relevant channel, and `article_email_frequency = daily`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: Users on never excluded

- **GIVEN** user U with a `Follow` on H, a `FollowedChannel` on the relevant channel, and `article_email_frequency = never`
- **WHEN** `resolve_broadcast_recipients` runs
- **THEN** U is not included

#### Scenario: No house project returns empty

- **GIVEN** a database with no Project where `is_house_project = True`
- **WHEN** `resolve_broadcast_recipients` runs for any `BroadcastEmail`
- **THEN** the resulting QuerySet is empty and no exception is raised

