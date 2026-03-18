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
