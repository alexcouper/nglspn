# Proposal: keep users logged in

Investigation: [`docs/2026-09-23-frequent-relogin-causes.md`](../../../docs/2026-09-23-frequent-relogin-causes.md).
This change fixes its causes 1, 2 and 3.

## Why

A session ends exactly seven days after the user typed their password, however
active they were, because the refresh token carries a fixed expiry and the
refresh endpoint never extends it. On top of that, one failed request at page
load renders the logged-out header even though the tokens are fine, and Safari
purges the localStorage the tokens live in after seven days of not visiting.
The result is that a returning user lands on `/login` far more often than on
any comparable site.

## What Changes

- **Sliding sessions.** Refreshing now returns a new refresh token as well as a
  new access token, with the idle expiry pushed out again. Idle lifetime goes
  from 7 days to 30. A session still has an absolute cap of one year from the
  original login, after which the user must re-authenticate.
- **Password reset ends other sessions.** A refresh token issued before a
  password reset stops working after it. Today it keeps working for the rest
  of its seven days.
- **The refresh token moves into an `HttpOnly` cookie** set by the backend on
  the API host, scoped to the auth endpoints. Scripts can no longer read it,
  and it survives Safari's seven-day purge of script-writable storage. The
  access token stays in localStorage as today.
- **BREAKING**: the login response no longer includes `refresh_token` in its
  body; it arrives as a `Set-Cookie` header instead. The refresh endpoint reads
  the cookie and no longer requires a JSON body. The only client is the web
  UI, which changes in the same PR. For one release the refresh endpoint also
  accepts the old body form so that already-logged-in browsers migrate to the
  cookie instead of being logged out by the deploy.
- **New `POST /api/auth/logout`** that clears the cookie, since a script cannot
  delete an `HttpOnly` cookie itself.
- **The web UI keeps a valid session visible.** When the startup check for the
  current user fails for a transient reason (network error, 5xx), it retries
  with backoff and keeps retrying on reconnect and tab focus instead of showing
  the "Log in" button. Only a definitive rejection of the refresh token logs
  the user out.

Out of scope: rendering the logged-in shell before the current user is known,
server-side sessions or a session table, "log out everywhere", and letting
Next.js server components authenticate (the cookie is host-only on the API
host, so they still cannot).

## Capabilities

### New Capabilities

- `login-sessions`: how a session is issued, extended, stored and ended:
  token lifetimes, the refresh-token cookie, rotation on refresh, the absolute
  cap, logout, the legacy-body transition, and the web UI's handling of
  transient failures at startup.

### Modified Capabilities

- `password-reset`: setting a new password additionally invalidates refresh
  tokens issued before the reset.

`inactive-account-exclusion` and `system-users` are unchanged: their refresh
scenarios still hold when the token arrives as a cookie.

## Impact

**Backend** (`src/django-backend/`)

- `project_showcase/settings.py`: `JWT_REFRESH_TOKEN_EXPIRE_DAYS` 7 → 30; new
  absolute-cap and cookie settings.
- `api/auth/jwt.py`: refresh tokens carry the original login time and a
  password-version claim; verification checks both.
- `api/routers/auth.py`: login sets the cookie, refresh rotates it and reads it
  (falling back to the body during the transition), new logout endpoint.
- `api/schemas/auth.py`: `Token` loses `refresh_token`; `RefreshRequest`
  becomes optional.
- **OpenAPI**: `make extract-openapi` and commit `src/web-ui/backend-openapi.json`,
  or `make extra-tests` fails.
- No model change, so no migration.

**Web UI** (`src/web-ui/`)

- `src/lib/api/base.ts`: refresh, login and logout send credentials; the
  refresh token is no longer stored; a successful refresh is announced so the
  auth context can recover.
- `src/contexts/auth.tsx`: transient failures at startup retry instead of
  leaving the user null; logout calls the backend.
- Tests in `base.test.ts`, `auth.test.tsx`, `test/factories.ts` and
  `test/helpers.ts` that assert on `refresh_token` in localStorage.
- e2e specs read `access_token` from localStorage and keep working.

**Infra** (`naglasupan-hq`): none. `CORS_ALLOW_CREDENTIALS` is already on and
prod already lists the exact frontend origin in `CORS_ALLOWED_ORIGINS`.
