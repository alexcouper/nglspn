## ADDED Requirements

### Requirement: Request password reset code
Any anonymous user SHALL be able to submit an email address to request a password reset code. The system SHALL generate a 6-digit numeric code, store it with a 15-minute expiry, and send it to the email address via an async email task. The system SHALL always return a success response regardless of whether the email exists in the system.

#### Scenario: Valid email receives code
- **WHEN** an anonymous user submits a registered email address to `POST /api/auth/forgot-password`
- **THEN** the system generates a 6-digit code with 15-minute expiry and enqueues a password reset email to that address
- **AND** returns HTTP 200 with message "If an account exists with that email, we've sent a reset code"

#### Scenario: Unknown email returns same response
- **WHEN** an anonymous user submits an unregistered email address to `POST /api/auth/forgot-password`
- **THEN** the system returns HTTP 200 with the same message as a valid email
- **AND** no email is sent

#### Scenario: Rate limited code generation
- **WHEN** an anonymous user requests a code for an email that had a code generated within the last 60 seconds
- **THEN** the system returns HTTP 200 with the same generic message (no error revealed)
- **AND** no new code is generated

### Requirement: Verify password reset code
Any anonymous user SHALL be able to submit an email address and 6-digit code to verify a password reset. On success, the system SHALL return a short-lived reset token (JWT with type "reset", 10-minute expiry). The system SHALL track failed attempts per code and reject after 3 failed attempts.

#### Scenario: Correct code returns reset token
- **WHEN** an anonymous user submits a valid email and correct 6-digit code to `POST /api/auth/forgot-password/verify`
- **THEN** the system marks the code as used
- **AND** returns HTTP 200 with a reset token (JWT, type "reset", 10-minute expiry)

#### Scenario: Wrong code increments attempts
- **WHEN** an anonymous user submits a valid email and incorrect code
- **THEN** the system increments the attempt counter on the most recent unused code for that email
- **AND** returns HTTP 400 with error message and `attempts_remaining` count

#### Scenario: Code exhausted after 3 failed attempts
- **WHEN** an anonymous user submits an incorrect code and the attempt counter reaches 3
- **THEN** the system returns HTTP 400 with error indicating the code is exhausted
- **AND** the code SHALL NOT accept further verification attempts
- **AND** the user must request a new code

#### Scenario: Expired code rejected
- **WHEN** an anonymous user submits a code that has passed its 15-minute expiry
- **THEN** the system returns HTTP 400 with error indicating the code is invalid or expired

#### Scenario: Already-used code rejected
- **WHEN** an anonymous user submits a code that has already been successfully verified
- **THEN** the system returns HTTP 400 with error indicating the code is invalid or expired

### Requirement: Set new password with reset token
A user SHALL be able to set a new password by providing a valid reset token and a new password. The system SHALL validate the reset token (type "reset", not expired), set the user's password, and return a success message. No current password is required.

#### Scenario: Valid reset token sets password
- **WHEN** a user submits a valid reset token and new password to `POST /api/auth/reset-password`
- **THEN** the system sets the user's password to the new value
- **AND** returns HTTP 200 with a success message

#### Scenario: Expired reset token rejected
- **WHEN** a user submits a reset token that has passed its 10-minute expiry
- **THEN** the system returns HTTP 400 with error indicating the token is invalid or expired

#### Scenario: Invalid token type rejected
- **WHEN** a user submits a JWT that is not of type "reset" (e.g., an access token or refresh token)
- **THEN** the system returns HTTP 400 with error indicating the token is invalid

### Requirement: Password reset code storage
The system SHALL store password reset codes in a dedicated `PasswordResetCode` model, separate from email verification codes. Each code SHALL track: user reference, 6-digit code, attempt count (default 0), creation time, expiry time, and used-at timestamp.

#### Scenario: Code created with correct fields
- **WHEN** a password reset code is generated for a user
- **THEN** it is stored with a 6-digit numeric code, attempts set to 0, expiry 15 minutes from creation, and used_at as null

#### Scenario: Previous unused codes for same user
- **WHEN** a new code is generated for a user who has existing unused codes
- **THEN** the new code is created independently (previous codes are not invalidated but will expire naturally)

### Requirement: Password reset email
The system SHALL send a password reset email using an MJML template, delivered via the async email task queue. The email SHALL contain the 6-digit code and expiry information.

#### Scenario: Email sent with correct content
- **WHEN** a password reset code is generated for a valid email
- **THEN** the system enqueues an email with subject "Reset your password - Naglasúpan"
- **AND** the email body contains the 6-digit code and states it expires in 15 minutes

### Requirement: Login page forgotten password flow
The login page SHALL include a "Forgotten password?" link that transitions the page through a state machine: login → forgot (email only) → code (6-digit PinInput) → reset (new password) → back to login with success message.

#### Scenario: User clicks forgotten password
- **WHEN** a user clicks "Forgotten password?" on the login page
- **THEN** the form changes to show only an email field and a "Continue" button
- **AND** the password field is hidden

#### Scenario: User submits email for reset
- **WHEN** a user enters their email and clicks "Continue" in the forgot state
- **THEN** the system calls `POST /api/auth/forgot-password` with the email
- **AND** transitions to the code entry state showing the PinInput component

#### Scenario: User enters correct code
- **WHEN** a user enters the correct 6-digit code in the PinInput
- **THEN** the system calls `POST /api/auth/forgot-password/verify`
- **AND** stores the returned reset token in component state
- **AND** transitions to the reset state showing a single password field

#### Scenario: User enters wrong code with attempts remaining
- **WHEN** a user enters an incorrect code and attempts remain
- **THEN** the system displays an error with the number of attempts remaining
- **AND** the PinInput is cleared for retry

#### Scenario: User sets new password
- **WHEN** a user enters a new password and submits in the reset state
- **THEN** the system calls `POST /api/auth/reset-password` with the reset token and new password
- **AND** transitions back to the login state with a success message "Password updated. Please log in."

#### Scenario: User navigates back from any state
- **WHEN** a user wants to go back during the forgot/code/reset flow
- **THEN** a "Back to login" link is available that returns to the default login state
