## 1. Backend Model & Migration

- [x] 1.1 Create `PasswordResetCode` model in `apps/users/models.py` with fields: id (UUID), user (FK), code (6 chars), attempts (int, default 0), created_at, expires_at, used_at
- [x] 1.2 Generate and run the migration

## 2. Backend Password Reset Handler

- [x] 2.1 Add `create_password_reset_code(email, expires_minutes)` to user handler — looks up user by email, enforces 60s rate limit, generates 6-digit code, returns code object. Returns None if email not found (no error).
- [x] 2.2 Add `verify_password_reset_code(email, code)` to user handler — finds latest unused/unexpired code for user, checks attempts < 3, compares code. On match: marks used_at, returns user. On mismatch: increments attempts, returns None with attempts_remaining. On exhausted/expired: returns error.
- [x] 2.3 Add `reset_password(user, new_password)` to user handler — sets the user's password via `user.set_password()` and saves.
- [x] 2.4 Add handler interface methods to `UserHandlerInterface`

## 3. Backend Reset Token

- [x] 3.1 Add `create_reset_token(user_id)` to `api/auth/jwt.py` — creates a JWT with `type: "reset"` and 10-minute expiry

## 4. Backend Email

- [x] 4.1 Create `password_reset_code.mjml` and `password_reset_code.txt` email templates (subject: "Reset your password - Naglasúpan", variables: code, expiry_minutes, user_name)
- [x] 4.2 Add `send_password_reset_email` async task in `api/tasks/email.py`

## 5. Backend API Endpoints

- [x] 5.1 Add `ForgotPasswordRequest` (email), `ForgotPasswordResponse` (message), `ForgotPasswordVerifyRequest` (email, code), `ForgotPasswordVerifyResponse` (reset_token), `ResetPasswordRequest` (reset_token, new_password), `ResetPasswordResponse` (message) schemas in `api/schemas/auth.py`
- [x] 5.2 Add `POST /forgot-password` endpoint — accepts email, calls handler, enqueues email, always returns 200 with generic message
- [x] 5.3 Add `POST /forgot-password/verify` endpoint — accepts email + code, calls handler, on success returns reset token via `create_reset_token()`, on failure returns 400 with attempts_remaining
- [x] 5.4 Add `POST /reset-password` endpoint — accepts reset_token + new_password, validates reset token (type "reset", not expired), extracts user_id, calls handler, returns 200

## 6. Backend Tests

- [x] 6.1 Test `POST /forgot-password` — valid email sends code, unknown email returns same 200, rate limiting suppresses silently
- [x] 6.2 Test `POST /forgot-password/verify` — correct code returns reset token, wrong code increments attempts, 3 failures exhausts code, expired code rejected
- [x] 6.3 Test `POST /reset-password` — valid reset token sets password, expired token rejected, wrong token type rejected
- [x] 6.4 Test end-to-end flow: request code → verify → reset password → login with new password

## 7. OpenAPI & Type Generation

- [x] 7.1 Run `make extract-openapi` from django-backend
- [x] 7.2 Run `npm run generate-types` from web-ui

## 8. Frontend Login Page State Machine

- [x] 8.1 Add state type (`"login" | "forgot" | "code" | "reset"`) and state variables (email, resetToken, attemptsRemaining, successMessage) to login page
- [x] 8.2 Add "Forgotten password?" link below the password field that transitions to `forgot` state
- [x] 8.3 Build `forgot` state UI — email-only field (pre-filled if already entered), "Continue" button, "Back to login" link. On submit: call forgot-password API, transition to `code` state
- [x] 8.4 Build `code` state UI — reuse PinInput component, show "code sent to {email}" message, display attempts remaining on error, "Back to login" link. On complete: call forgot-password/verify API, store reset token in state, transition to `reset` state
- [x] 8.5 Build `reset` state UI — single password field, submit button, "Back to login" link. On submit: call reset-password API with reset token, transition to `login` state with success message "Password updated. Please log in."
- [x] 8.6 Show success message banner in `login` state when returning from password reset

## 9. Frontend API Client

- [x] 9.1 Add `forgotPassword(email)`, `forgotPasswordVerify(email, code)`, `resetPassword(resetToken, newPassword)` methods to auth client in `src/lib/api/auth.ts`

## 10. Linting & CI

- [x] 10.1 Run backend lint (`make lint` from django-backend) and fix issues
- [x] 10.2 Run frontend lint (`npm run lint` from web-ui) and fix issues
- [x] 10.3 Run full CI check (`make ci` from project root)
