## ADDED Requirements

### Requirement: Notification model

The system SHALL store notifications in a `Notification` model with: id (UUID), recipient (FK to User), discussion (FK to Discussion), cadence (CharField with choices: IMMEDIATE, HOURLY, DAILY, NEVER), sent (boolean, default false), created_at, and sent_at (nullable).

The cadence SHALL be snapshotted from the recipient's `notification_frequency` at the time of notification creation.

#### Scenario: Notification created with user's current cadence
- **WHEN** a notification is created for a user whose `notification_frequency` is HOURLY
- **THEN** the notification's cadence field SHALL be set to HOURLY

#### Scenario: Changing user preference does not affect existing notifications
- **WHEN** a user changes their `notification_frequency` from HOURLY to DAILY
- **THEN** existing unsent notifications for that user SHALL retain their original cadence value

### Requirement: Notifications Django app

The system SHALL have a dedicated Django app at `apps/notifications/` with its own models, admin registration, and migrations. The app SHALL be registered in Django settings.

#### Scenario: App is registered
- **WHEN** Django starts
- **THEN** the `apps.notifications` app is loaded and its models are available

### Requirement: Notifications service layer

The system SHALL expose notification operations through a service layer following the handler/query pattern. The service SHALL be registered in `services/__init__.py`.

The handler interface SHALL support:
- `create_notifications_for_discussion(discussion_id)` — creates notifications for all relevant users
- `send_immediate_notifications()` — sends all unsent notifications with IMMEDIATE cadence
- `send_batch_notifications(cadence)` — sends all unsent notifications with the given cadence as a digest

#### Scenario: Service is accessible via HANDLERS
- **WHEN** code imports `from services import HANDLERS`
- **THEN** `HANDLERS.notifications` is available

### Requirement: Notification recipient determination

When creating notifications for a discussion, the system SHALL notify:
1. The owner of the project the discussion belongs to
2. The author of the root discussion (if the trigger is a reply)
3. All users who have previously replied to the same root discussion

The system SHALL exclude the author of the triggering discussion/reply from the notification list. The system SHALL create at most one notification per user per triggering comment.

#### Scenario: New root discussion notifies project owner
- **WHEN** user A creates a discussion on a project owned by user B
- **THEN** one notification is created for user B

#### Scenario: Root discussion by project owner creates no notifications
- **WHEN** user A creates a discussion on their own project and no other participants exist
- **THEN** no notifications are created

#### Scenario: Reply notifies project owner and discussion creator
- **WHEN** user C replies to a discussion created by user A on a project owned by user B
- **THEN** notifications are created for user A and user B (not user C)

#### Scenario: Reply notifies previous participants
- **WHEN** user D replies to a discussion where users A, B, and C have previously replied
- **THEN** notifications are created for users A, B, C, and the project owner (deduplicated, excluding user D)

#### Scenario: Deduplication across roles
- **WHEN** user A is both the project owner and the discussion creator, and user B replies
- **THEN** exactly one notification is created for user A (not two)

### Requirement: User notification frequency setting

The User model SHALL have a `notification_frequency` CharField with choices: IMMEDIATE, HOURLY, DAILY, NEVER. The default SHALL be IMMEDIATE.

The user update API and frontend settings page SHALL allow users to change this value.

#### Scenario: Default notification frequency
- **WHEN** a new user registers
- **THEN** their `notification_frequency` SHALL be IMMEDIATE

#### Scenario: User updates notification frequency
- **WHEN** a user updates their `notification_frequency` to DAILY via the API
- **THEN** the value is persisted and future notifications for that user are created with DAILY cadence

### Requirement: Immediate notification delivery

When a notification is created with IMMEDIATE cadence, the system SHALL send an email to the recipient as part of the notification creation flow.

#### Scenario: Immediate notification sends email
- **WHEN** a notification with IMMEDIATE cadence is created
- **THEN** an email is sent to the recipient and the notification is marked as sent with sent_at timestamp

#### Scenario: User with NEVER cadence receives no notification
- **WHEN** a user has `notification_frequency` set to NEVER
- **THEN** no notification row is created for that user

### Requirement: Hourly notification batch task

The system SHALL have a django-task that runs hourly, collects all unsent notifications with HOURLY cadence, groups them by recipient, and sends a single digest email per user.

#### Scenario: Hourly batch sends digest
- **WHEN** the hourly task runs and user A has 3 unsent HOURLY notifications
- **THEN** one digest email is sent to user A covering all 3 notifications, and all 3 are marked as sent

#### Scenario: Hourly batch with no pending notifications
- **WHEN** the hourly task runs and there are no unsent HOURLY notifications
- **THEN** no emails are sent

### Requirement: Daily notification batch task

The system SHALL have a django-task that runs daily, collects all unsent notifications with DAILY cadence, groups them by recipient, and sends a single digest email per user.

#### Scenario: Daily batch sends digest
- **WHEN** the daily task runs and user A has 5 unsent DAILY notifications
- **THEN** one digest email is sent to user A covering all 5 notifications, and all 5 are marked as sent

### Requirement: Notification email content

Notification emails SHALL identify the project, the discussion, and the comment body. Digest emails SHALL list all new comments grouped by discussion.

#### Scenario: Immediate notification email content
- **WHEN** an immediate notification email is sent for a reply by user B on project "MyApp"
- **THEN** the email SHALL include the project name, a link to the discussion, the comment author's name, and the comment body

#### Scenario: Digest notification email content
- **WHEN** a digest email is sent with notifications across 2 discussions on 2 projects
- **THEN** the email SHALL group comments by project and discussion, showing each comment's author and body
