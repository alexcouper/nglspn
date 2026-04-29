## Purpose

Provide a way to mark `User` accounts as platform-internal identities (e.g. the Community/Unowned placeholder used for community-submitted projects). System users own data on the platform like any other user, but cannot authenticate, and are excluded from any flow whose addressee must be a real human (notifications, emails, etc.).

## Requirements

### Requirement: User accounts may be flagged as system users

The system SHALL persist a boolean field `is_system_user` on `User` with default `False`. A user with `is_system_user = True` represents a platform-internal identity (e.g. the Community/Unowned placeholder) rather than a real human account.

#### Scenario: Default value is False

- **WHEN** a user is created via the existing registration flow
- **THEN** their `is_system_user` is `False`

#### Scenario: System users coexist with regular users

- **GIVEN** the database contains both regular and system users
- **WHEN** any query that does not specifically filter by `is_system_user` runs
- **THEN** both regular and system users are visible to that query (no implicit filtering)

### Requirement: System users cannot authenticate

The system SHALL reject any authentication attempt for a user whose `is_system_user = True`. This applies uniformly to every code path that issues an authenticated session or token, including but not limited to:

- Password-based login
- Email-verification-code submission
- Password-reset-code submission
- JWT issuance during or after registration

A rejection SHALL produce the same generic failure response a regular user would receive for an invalid credential, with no information disclosure that distinguishes "system user" from "wrong password".

#### Scenario: Password login is rejected for a system user

- **GIVEN** a user with `is_system_user = True` and any password set (or unusable password)
- **WHEN** a client submits the password-login endpoint with that user's email and any password
- **THEN** the response is the same authentication failure as for an unknown user
- **AND** no JWT is issued
- **AND** no session is created

#### Scenario: Email verification code is rejected for a system user

- **GIVEN** a row in `EmailVerificationCode` would otherwise be valid for a user with `is_system_user = True`
- **WHEN** a client submits the verification endpoint with that code
- **THEN** the response is the same generic failure used for invalid or expired codes
- **AND** the user is not marked verified
- **AND** no token is issued

#### Scenario: Password reset code is rejected for a system user

- **GIVEN** a `PasswordResetCode` exists for a user with `is_system_user = True`
- **WHEN** a client submits the reset endpoint with that code
- **THEN** the response is the same generic failure used for invalid or expired codes
- **AND** the user's password is not changed

#### Scenario: JWT issuance helper rejects system users

- **WHEN** internal code calls the JWT-issuance helper with a `User` whose `is_system_user = True`
- **THEN** the helper raises (or returns a sentinel that callers treat as failure)
- **AND** no token is produced

### Requirement: Community/Unowned seed user exists

The system SHALL ensure exactly one `User` row exists with all of the following properties, created by either a data migration or an idempotent management command (or both, with consistent semantics):

- `email`: a stable reserved address (final value chosen during implementation; defaulted to `community@naglasupan.is`)
- `kennitala`: `"7777777777"` (a sentinel that cannot collide with a real Icelandic kennitala)
- `is_system_user`: `True`
- `is_active`: `True`
- `is_verified`: `True`
- Password set via Django's "unusable password" sentinel
- `info`: `"Projects submitted by community members but owned by people outside of Naglasúpan."`

The creation step SHALL be idempotent: running it multiple times SHALL NOT create duplicate rows or change a row that already exists with these properties.

#### Scenario: Migration creates the seed user on a fresh database

- **GIVEN** the database has no system users
- **WHEN** the change's migrations run
- **THEN** exactly one `User` row exists with `is_system_user = True`, `kennitala = "7777777777"`, the documented email, and unusable password

#### Scenario: Re-running creation is a no-op

- **GIVEN** the seed user already exists with the documented properties
- **WHEN** the seed migration or management command runs again
- **THEN** no new row is created
- **AND** the existing row's fields are not modified

#### Scenario: Login attempts against the seed user fail

- **GIVEN** the seed user exists
- **WHEN** any login or token-issuance flow is attempted with the seed user's email
- **THEN** authentication fails by the rules described in the system-user authentication-rejection requirement
