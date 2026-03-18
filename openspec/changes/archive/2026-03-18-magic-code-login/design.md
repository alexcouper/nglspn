## Context

The app uses JWT auth with Django Ninja. Email verification already exists using 6-digit codes (`EmailVerificationCode` model), async email tasks, and the `PinInput` frontend component. The login page is a simple email/password form. There is no password recovery mechanism.

## Goals / Non-Goals

**Goals:**
- Self-service password reset via emailed 6-digit code
- Reuse existing code verification patterns (model shape, PinInput, email infra)
- Secure: don't leak whether an email exists, limit code attempts to 3
- After code verification, issue a scoped reset token for setting a new password

**Non-Goals:**
- Magic link (URL-based) login — we're using typed codes only
- "Change password" for users who know their current password (separate future feature)
- Account lockout after too many reset requests
- Password strength requirements beyond Django defaults

## Decisions

### 1. Separate `PasswordResetCode` model (not reusing `EmailVerificationCode`)

The password reset code needs an `attempts` counter (max 3 tries) that email verification codes don't have. Rather than adding a `purpose` discriminator and `attempts` column to the existing model, a separate model keeps concerns clean and avoids migrating existing data.

**`PasswordResetCode` fields:** `id`, `user` (FK), `code` (6 chars), `attempts` (int, default 0), `created_at`, `expires_at`, `used_at`.

**Alternative considered:** Adding `purpose` enum + `attempts` to `EmailVerificationCode`. Rejected because it complicates queries for the existing verification flow and mixes two distinct lifecycles.

### 2. Token-exchange pattern: code → reset token → set password

Three new endpoints on the auth router, all under `/api/auth/`:

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /forgot-password` | Anon | Accept email, generate code, send email. Always returns 200 (don't reveal if email exists). |
| `POST /forgot-password/verify` | Anon | Accept email + code. On success: return a short-lived **reset token** (JWT with `type: "reset"`, ~10 min expiry). On failure: increment attempts, reject after 3. |
| `POST /reset-password` | Reset token | Accept reset token + new password. Validates token, sets password, returns success message. |

The reset token is a purpose-scoped JWT — it can only be used to set a password. It uses the same `verify_token()` infrastructure but the endpoint checks `type == "reset"`. This means:

- **No `needs_password_reset` flag on User model** — no migration for a new field
- **No navigation guard changes** — the user is never logged in during the reset flow
- **No changes to `UserResponse`, `Token` schema, or `getPostAuthDestination()`**
- The entire flow is self-contained and stateless (beyond the code verification step)

A new `create_reset_token(user_id)` function in `jwt.py` produces the scoped token.

**Alternative considered:** Logging the user in on code verification and using a `needs_password_reset` flag to gate navigation. Rejected because the token-exchange approach is simpler — no User model changes, no navigation guards, no "half-logged-in" restricted state.

### 3. Frontend: login page state machine, not separate routes

The login page handles the forgot-password flow as internal states rather than separate pages:

- **`login`** — default email+password form with "Forgotten password?" link
- **`forgot`** — email-only form with "Continue" button
- **`code`** — PinInput (reused component), shows attempts remaining
- **`reset`** — single password field, no confirmation

The reset token returned from the `code` step is held in component state only — it never touches localStorage or auth context. After password is set, the form returns to the `login` state with a success message prompting the user to log in with their new password.

**Alternative considered:** Separate `/forgot-password` route. Rejected because the flow is short and linear — keeping it in one page avoids route boilerplate and feels more cohesive. The state machine is simple (4 states, linear progression).

### 4. Email template

New MJML template `password_reset_code.mjml` following the same structure as `verification_code.mjml`. Subject: "Reset your password - Naglasúpan". Variables: `code`, `expiry_minutes`, `user_name`.

### 5. Security: silent failure on unknown emails

`POST /forgot-password` always returns `{"message": "If an account exists..."}` regardless of whether the email is found. This prevents email enumeration. Rate limiting uses the same 60-second cooldown pattern as verification codes.

### 6. Attempt tracking

The `attempts` field on `PasswordResetCode` is incremented on each failed verification. After 3 failed attempts, the code is considered exhausted — the user must request a new one. The response includes `attempts_remaining` so the frontend can display it.

## Risks / Trade-offs

- **[Silent failure UX]** Users with typos in their email won't know it failed → Acceptable tradeoff for security. The "If an account exists..." message is standard practice.
- **[No account lockout]** Attackers can request unlimited codes for an email → Mitigated by 60-second rate limit on code generation. Full lockout is a non-goal for now.
- **[Reset token in component state]** If the user refreshes during the reset step, they lose the token and must restart → Acceptable since the flow is short. They can just request a new code.
- **[10-min reset token window]** User has 10 minutes from code verification to set their password → Generous for a single form field. If it expires, they restart the flow.
