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

The recipient resolver for `BroadcastEmail` rows whose `email_type` is `competition_results` SHALL determine recipients by joining `Follow` and `FollowedChannel` on the Naglasúpan house project (the Project row with `is_house_project = True`).

Mapping:

- `email_type = "competition_results"` → users with a `Follow` on the house project AND a `FollowedChannel` row on the house project's "Competition Winners" channel AND `User.article_email_frequency != "never"`.

`platform_updates` is no longer a valid `email_type`. `BroadcastEmailType` SHALL expose only `competition_results`, so no new broadcast can target it. Historic `BroadcastEmail` rows retain the string `platform_updates` in the column; the resolver SHALL return an empty QuerySet for any unmapped `email_type` rather than raising.

There is no per-channel email switch any more — `FollowedChannel` existence replaces the prior `email_enabled` boolean, and `article_email_frequency` provides the global opt-out lever.

The resolver SHALL exclude:

- Inactive users (`is_active = False`).
- System users (`is_system_user = True`).
- The broadcast's `created_by` user (preserves the existing self-exclusion behaviour).

When no house project exists in the database (greenfield dev / test case), the resolver SHALL return an empty QuerySet and SHALL NOT raise.

The resolver continues to be the **recipient-set** entry point.

#### Scenario: Competition results broadcast resolves via Competition Winners channel

- **GIVEN** the house project H with channel "Competition Winners" C
- **AND** user U1 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = hourly`
- **AND** user U2 with a `Follow` on H, no `FollowedChannel(_, C)` row
- **AND** user U3 with no `Follow` on H
- **AND** user U4 with a `Follow` on H, a `FollowedChannel(_, C)` row, and `article_email_frequency = never`
- **WHEN** `resolve_broadcast_recipients` runs for a `BroadcastEmail` with `email_type = "competition_results"`
- **THEN** the resulting QuerySet SHALL include U1
- **AND** SHALL NOT include U2, U3, or U4

#### Scenario: Historic platform updates broadcast resolves to nobody

- **GIVEN** a `BroadcastEmail` row with `email_type = "platform_updates"`
- **WHEN** `resolve_broadcast_recipients` runs for it
- **THEN** the resulting QuerySet SHALL be empty
- **AND** the resolver SHALL NOT raise

#### Scenario: Platform updates cannot be selected for a new broadcast

- **WHEN** an admin creates a `BroadcastEmail` in the Django admin
- **THEN** `platform_updates` SHALL NOT be offered as an `email_type` choice

