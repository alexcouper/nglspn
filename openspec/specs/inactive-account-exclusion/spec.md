## Purpose

Ensure users with `is_active=False` are fully excluded from authentication, broadcast emails, and discussion notifications, preventing inactive accounts from accessing the platform or receiving communications.

## Requirements

### Requirement: Inactive users cannot authenticate
The system SHALL reject authentication attempts from users with `is_active=False` at all entry points: login, token refresh, and access token validation.

#### Scenario: Inactive user attempts login
- **WHEN** a user with `is_active=False` submits valid credentials to the login endpoint
- **THEN** the system SHALL return a 401 response and NOT create a session or issue tokens

#### Scenario: Inactive user attempts token refresh
- **WHEN** a user with `is_active=False` attempts to refresh their access token using a valid refresh token
- **THEN** the system SHALL return a 401 response and NOT issue a new access token

#### Scenario: Inactive user's access token is validated
- **WHEN** the system validates a JWT access token belonging to a user with `is_active=False`
- **THEN** the system SHALL treat the token as invalid and deny access

### Requirement: Inactive users excluded from broadcast emails
The system SHALL NOT include users with `is_active=False` in any broadcast email recipient set.

#### Scenario: Platform update broadcast excludes inactive users
- **WHEN** a platform update broadcast email is sent
- **THEN** the recipient set SHALL only include users where `is_active=True` AND `email_opt_in_platform_updates=True`

#### Scenario: Competition results broadcast excludes inactive users
- **WHEN** a competition results broadcast email is sent
- **THEN** the recipient set SHALL only include users where `is_active=True` AND `email_opt_in_competition_results=True`

#### Scenario: Individual recipient broadcast excludes inactive users
- **WHEN** a broadcast email is sent to individually-selected recipients
- **THEN** the recipient set SHALL be filtered to only include users where `is_active=True`

### Requirement: Inactive users excluded from discussion notifications
The system SHALL NOT create notification records or send notification emails for users with `is_active=False`.

#### Scenario: Discussion reply does not notify inactive project owner
- **WHEN** a reply is posted to a discussion on a project whose owner has `is_active=False`
- **THEN** the system SHALL NOT create a Notification record for that owner

#### Scenario: Discussion reply does not notify inactive thread participant
- **WHEN** a reply is posted to a discussion thread where a previous participant has `is_active=False`
- **THEN** the system SHALL NOT create a Notification record for that participant

#### Scenario: Batch notification digest skips inactive users
- **WHEN** the system sends batch notification digests
- **THEN** it SHALL NOT send digest emails to users with `is_active=False`, even if unsent Notification records exist for them
