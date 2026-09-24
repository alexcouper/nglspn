# Spec Delta

## ADDED Requirements

### Requirement: Password reset invalidates existing refresh tokens
Setting a new password through the reset flow SHALL invalidate every refresh
token issued before the reset. A refresh attempted with such a token SHALL be
rejected with HTTP 401. Access tokens already issued SHALL remain valid until
their own 30-minute expiry; no attempt is made to revoke them early.

#### Scenario: Old refresh token rejected after reset
- **WHEN** a user completes a password reset and a browser then refreshes with a refresh token issued before the reset
- **THEN** the refresh is rejected with HTTP 401 and that browser is logged out

#### Scenario: Login after reset issues a working refresh token
- **WHEN** the user logs in with the new password
- **THEN** the refresh token from that login refreshes successfully
