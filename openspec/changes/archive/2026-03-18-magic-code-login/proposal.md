## Why

Users who forget their passwords have no way to recover their accounts. We need a self-service password reset flow using a one-time code sent via email — matching the verification code pattern users already encounter during registration.

## What Changes

- Add a "Forgotten password?" link on the login page that switches to an email-only form
- Backend endpoint for anonymous users to request a password reset code (sends 6-digit code via email)
- Reuse the `PinInput` component for code entry (max 3 attempts per code)
- On correct code, backend logs the user in but sets a `needs_password_reset` flag on their profile
- Frontend navigation guard: users with `needs_password_reset` are locked to a "set new password" screen (single field, no confirmation, no current password required)
- Backend endpoint for flagged users to set a new password (clears the flag)
- New email template for password reset codes

## Capabilities

### New Capabilities
- `password-reset`: Forgotten password flow — request code, verify code, force password change before normal site use

### Modified Capabilities

## Impact

- **User model**: New `needs_password_reset` boolean field (migration required)
- **API**: New endpoints — `POST /api/auth/forgot-password`, `POST /api/auth/forgot-password/verify`, `POST /api/auth/reset-password`
- **Frontend**: New pages/states in login flow, navigation guard changes in auth routing
- **Email**: New MJML template for password reset codes
- **Existing code reuse**: `EmailVerificationCode` model (or similar), `PinInput` component, email task infrastructure
- **Security**: Rate limiting on code requests, 3-attempt max on code verification, flag-gated password reset
