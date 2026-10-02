# Tasks

Specs: [`specs/login-sessions/spec.md`](specs/login-sessions/spec.md),
[`specs/password-reset/spec.md`](specs/password-reset/spec.md).
Design: [`design.md`](design.md).

## 1. Backend: token lifetimes and claims

- [x] 1.1 In `project_showcase/settings.py` set `JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30`,
  add `JWT_SESSION_ABSOLUTE_DAYS = 365`, and add the cookie settings
  (`REFRESH_COOKIE_NAME`, `REFRESH_COOKIE_PATH = "/api/auth"`,
  `REFRESH_COOKIE_SECURE = not DEBUG`). Verify with `uv run python -c` that the
  values load.
- [x] 1.2 In `api/auth/jwt.py` extend `create_refresh_token(user, *, auth_time=None)`
  to take the user (for `pwv = user.get_session_auth_hash()`) and carry
  `auth_time` forward, defaulting to now. Add `verify_refresh_token(token, user)`
  that checks type, idle expiry, absolute cap and `pwv`; both claims are
  required. Unit tests in `api/auth/test_jwt.py`: idle expiry, absolute cap
  with a fresh `iat`, `pwv` mismatch, token without either claim rejected,
  `auth_time` preserved across re-issue.
- [x] 1.3 Add `api/auth/cookies.py` with `set_refresh_cookie(response, token)` and
  `clear_refresh_cookie(response)` owning name, path, `HttpOnly`, `SameSite=Lax`,
  `Secure` and `Max-Age`. Unit test that the emitted `Set-Cookie` carries every
  attribute and that clearing uses the same name and path.

## 2. Backend: endpoints

- [x] 2.1 `api/schemas/auth.py`: remove `refresh_token` from `Token`; remove
  `RefreshRequest`. Verify `make lint` passes.
- [x] 2.2 `api/routers/auth.py` login: set the cookie via the helper, drop
  `refresh_token` from the body. Update `TestLogin` in `api/routers/test_auth.py`
  to assert the cookie attributes and the absence of `refresh_token` in JSON.
- [x] 2.3 `api/routers/auth.py` refresh: read the cookie, verify with
  `verify_refresh_token`, respond with a new access token and set a new refresh
  cookie. Rewrite `TestRefreshToken`: cookie path, body token ignored, no token
  → 401, idle-expired → 401, absolute-capped → 401, inactive and system users
  still 401, two concurrent refreshes with the same token both succeed.
- [x] 2.4 Add `POST /api/auth/logout` returning 204 and clearing the cookie, with
  no auth requirement. Tests: with cookie → expiring `Set-Cookie`; without
  cookie → 204.
- [x] 2.5 Password reset invalidation: test in `test_auth.py` that a refresh
  token minted before `reset_password` is rejected afterwards and one minted by
  a fresh login works. No handler change expected since `pwv` derives from the
  password hash; the test proves it.
- [x] 2.6 Run `make extract-openapi`, commit `src/web-ui/backend-openapi.json`,
  and verify `make extra-tests` and `make test` pass in `src/django-backend/`.

## 3. Web UI: API client

- [x] 3.1 `src/lib/api/base.ts`: stop storing `refresh_token` and delete a
  stale copy on construction; send `credentials: "include"` on login, refresh
  and logout; dispatch `auth:refreshed` after a successful refresh; add
  `refreshSession()` for a start with no access token. `attemptTokenRefresh`
  returns `invalid` only on 401; absence of a local token is no longer
  `invalid` (the cookie may exist). Update `base.test.ts`: the "no refresh
  token at all" case now calls the endpoint; the "persists the new access
  token" case still holds; add the stale-copy removal and the `auth:refreshed`
  event.
- [x] 3.2 `src/lib/api/auth.ts`: `login` stores only the access token; add
  `logout()` calling `POST /api/auth/logout` and `restoreSession()`, with the
  `logout_pending` marker from the design. Update `src/test/factories.ts` and
  `src/test/helpers.ts` so fixtures no longer set or assert `refresh_token`.
  Verify `make test` in `src/web-ui/`.
- [x] 3.3 `npm run generate-types` and fix any type errors from the changed
  `Token` schema; verify `make lint` passes.

## 4. Web UI: auth context and startup recovery

- [x] 4.1 `src/contexts/auth.tsx`: on `AuthTransientError` (or a network error)
  during `checkAuth`, retry after 1 s, 3 s and 8 s with `isLoading` true; on
  `AuthExpiredError` stop. After exhausting retries keep the token and register
  listeners for `online`, `visibilitychange` (visible) and `auth:refreshed`
  that re-run the check; remove them on unmount. Tests in `auth.test.tsx` with
  fake timers: 503 then 200 shows the user with no logged-out state in between;
  three failures leave the token in place; `online` after failures recovers;
  `auth:refreshed` recovers; 401 from refresh clears immediately.
- [x] 4.2 `logout` in the context calls `api.auth.logout()` and clears the
  access token locally whether it resolves or rejects. Test both branches.
- [x] 4.3 Verify `useRequireAuth` does not redirect while the check is retrying
  (token held, `isLoading` true): add a test in a new
  `src/hooks/useRequireAuth.test.tsx`.

## 5. Integration

- [x] 5.1 Run both services (`make dev` each, `make seed`), log in through the
  UI, and confirm in devtools: `Set-Cookie` on login with `HttpOnly; SameSite=Lax;
  Path=/api/auth`, no `refresh_token` in localStorage, and that after the access
  token is deleted from localStorage a page reload lands signed in without
  visiting `/login`.
- [x] 5.2 Stale-token check: seed localStorage with a refresh token minted
  without the new claims, delete the access token, reload, and confirm the
  browser is logged out and the localStorage key is gone.
- [x] 5.3 Transient check: stop the backend, reload a signed-in page, confirm
  the header shows the placeholder rather than "Log in", start the backend
  within 12 s, and confirm the header resolves to the signed-in user without a
  reload.
- [x] 5.4 Run `cd src/web-ui && npx playwright test e2e/login.spec.ts` against
  the running stack and confirm it passes; fix any helper that expected
  `refresh_token` in a login response body.
- [x] 5.5 Update `docs/2026-09-23-frequent-relogin-causes.md` with a one-line
  status pointing at this change, and correct its claim that a cookie would let
  server components authenticate (it is host-only on the API host).
- [x] 5.6 Remove the transition paths (body fallback, `RefreshRequest`, claim
  fallbacks, web UI body migration) and regenerate OpenAPI. Done before the
  first deploy instead of as a dated follow-up: one forced re-login was
  accepted over carrying the paths.
