# Design: keep users logged in

## Context

See [`proposal.md`](proposal.md) for motivation and the
[investigation](../../../docs/2026-09-23-frequent-relogin-causes.md) for the
evidence. The mechanics that shape the decisions:

- Auth is stateless. `api/auth/jwt.py` mints HS256 JWTs signed with
  `JWT_SECRET_KEY` (a sealed, stable secret in prod); there is no session
  table and nothing is revoked. `verify_token` decodes and checks `exp`;
  routers then check the `type` claim.
- `POST /api/auth/refresh` (`api/routers/auth.py:149`) takes the refresh token
  in a JSON body and returns only an access token.
- The web UI (`src/lib/api/base.ts`) keeps both tokens in localStorage, sends
  the access token as a Bearer header, and on a 401 calls refresh once and
  retries. It already classifies refresh outcomes as `refreshed`, `invalid`
  (401) or `transient` (anything else) and throws `AuthExpiredError` or
  `AuthTransientError` accordingly. `AuthProvider` (`src/contexts/auth.tsx`)
  swallows both at startup.
- Frontend and API are on different hosts of the same site:
  `naglasupan.is` and `api.naglasupan.is` in prod, `localhost:3000` and
  `localhost:8000` in dev. django-cors-headers is configured with
  `CORS_ALLOW_CREDENTIALS = True` and an explicit origin list in prod.
- Every API call sends `Content-Type: application/json`, which makes
  cross-origin browsers preflight the request.
- e2e helpers read `access_token` from localStorage to make direct API calls.

## Goals / Non-Goals

**Goals:**

- No new state on the backend: the change stays stateless so it needs no
  migration, no cleanup job and no new failure mode under concurrency.
- One deploy, no forced logout for browsers that are logged in today.
- The long-lived credential is unreadable from page script and outlives
  Safari's storage purge.
- The web UI never shows "Log in" while it still holds credentials that have
  not been rejected.

**Non-Goals:**

- Revocation of individual sessions or "log out everywhere". Stateless tokens
  cannot do it; if it is wanted later, a session table is the design.
- Moving the access token out of localStorage. Its 30-minute life bounds the
  exposure, and the e2e helpers depend on it.
- Same-origin API proxying through Next.js. It would let server components
  authenticate, but it is a separate, larger change.

## Decisions

### Sliding expiry by re-issue, not by a session table

`/refresh` mints a fresh refresh token (30-day `exp`) alongside the access
token. The old refresh token is not revoked; it dies at its own `exp`.

Alternatives: a `RefreshSession` row per login with rotation and reuse
detection. It buys revocation and reuse alarms at the cost of a table, a
sweep, and the classic multi-tab race where tab B refreshes with a token tab
A just rotated away. That race is exactly what the proposal is trying to stop
causing logouts. Stateless re-issue has no race: any unexpired token works.

The security trade is honest: a stolen refresh token is good for up to 30 idle
days instead of 7. The cookie move (below) is what makes theft harder; the
password-version claim (below) gives the user a way to cut it off.

### Two extra claims on the refresh token

- `auth_time`: the original password login, carried forward unchanged on
  every re-issue. Refresh rejects when `now - auth_time > 365 days`. Without
  it, re-issue makes sessions immortal.
- `pwv`: `user.get_session_auth_hash()`, Django's HMAC of the password hash.
  Refresh rejects on mismatch, so a password reset ends every other session at
  its next refresh. Access tokens are not checked: they die within 30 minutes
  anyway, and the point is to end sessions, not to race a reset against an
  in-flight request.

Tokens minted before this change have neither claim. `auth_time` falls back
to `iat`; a missing `pwv` is accepted. Both fallbacks can be removed once the
old tokens have aged out (7 days after deploy), together with the legacy body
path.

### Refresh token in a host-only cookie on the API host

Set by the API response with `HttpOnly; SameSite=Lax; Path=/api/auth;
Max-Age=<30 days>`, plus `Secure` when `DEBUG` is off. No `Domain` attribute,
so it is host-only for `api.naglasupan.is` (or `localhost` in dev).

Why this and not the alternatives:

- **Parent-domain cookie (`Domain=naglasupan.is`)** would reach the Next.js
  server too, but also every other subdomain, and it does not help the server
  components today because they call the API without a browser. Host-only is
  the minimum that works.
- **Keep it in localStorage** is the status quo: readable by script, purged by
  Safari ITP after 7 days of non-use.
- **Both tokens in cookies** would mean every API request carries credentials
  and needs a CSRF story. Keeping the access token as a Bearer header keeps
  CSRF out of the data endpoints entirely.

Cross-site mechanics: `naglasupan.is` → `api.naglasupan.is` is same-site
(same registrable domain), so `SameSite=Lax` sends the cookie on the
`credentials: "include"` fetches to `/api/auth/*`. It is also same-site for
ITP purposes, and it is set by an HTTP response rather than script, so the
7-day cap does not apply. In dev both hosts are `localhost`; cookies ignore
ports.

CSRF on the auth endpoints: `SameSite=Lax` stops a cross-site POST from
carrying the cookie at all. Belt and braces, every call sends
`Content-Type: application/json`, which forces a preflight that a foreign
origin fails. A CSRF'd refresh would in any case return an access token to a
response the attacker cannot read. No CSRF token is added.

`Path=/api/auth` means the cookie rides on login, refresh, logout, `/me` and
the password endpoints. Only refresh reads it. Narrowing to `/api/auth/refresh`
would need a second cookie path for logout to clear; not worth it.

### Transition: accept the body for one release

Browsers logged in today hold a refresh token in localStorage and no cookie.
If refresh only read the cookie, every one of them would be logged out on the
first access-token expiry after the deploy, which is the opposite of the
point. So for one release:

1. `/refresh` reads the cookie; if absent, reads `refresh_token` from the
   body; verifies whichever it found; always sets the cookie on success.
2. The web UI, on first refresh after the deploy, sends the localStorage
   token in the body and deletes it from localStorage immediately, success or
   not. From then on the cookie carries it.

The `RefreshRequest` schema keeps `refresh_token` as optional, and the
follow-up that removes the body path also removes the schema. Both steps
regenerate the OpenAPI file.

### Logout endpoint

`POST /api/auth/logout` responds 204 and deletes the cookie (same `Path`,
`Max-Age=0`). No auth required: an expired access token must not stop someone
logging out. It cannot revoke the token (stateless), only remove it from the
browser. The web UI calls it with `credentials: "include"`, then clears the
access token locally whatever the response.

### Startup recovery in the web UI

`AuthProvider.checkAuth` distinguishes the two errors it already receives:

- `AuthExpiredError` → the session is over; leave `user` null.
- `AuthTransientError` (or any network error) → retry after 1 s, 3 s, 8 s
  with `isLoading` still true, so the header shows its placeholder rather
  than "Log in". After the third failure, set `isLoading` false and `user`
  null but keep the token, and re-run the check on `window` `online`,
  `document` `visibilitychange` to visible, and a new `auth:refreshed` event
  that `APIClient` dispatches whenever a refresh succeeds. Any one success
  populates `user`.

Why not keep `isLoading` true indefinitely: a placeholder that never resolves
is worse than a wrong button when the backend is genuinely down for minutes,
and the page body will be failing too. Twelve seconds covers a pod rollover
and a cold connection.

`useRequireAuth` already declines to redirect while `api.isAuthenticated()`
is true; that stays, so protected pages wait through the retries.

### Ninja specifics

Setting a cookie from a Ninja view: declare `response: HttpResponse` as a
view parameter; Ninja injects the response object and merges its headers and
cookies into the final response. Reading: `request.COOKIES`. One helper in
`api/auth/cookies.py` owns the name and attributes so login, refresh and
logout cannot drift.

## Risks / Trade-offs

- [Longer-lived stolen refresh token: 30 idle days, up to a year] → cookie
  is `HttpOnly`, `Secure`, path-scoped; password reset invalidates via `pwv`.
  Accepted.
- [Cookie not sent because a browser treats the hosts as cross-site] → they
  share the registrable domain; verified by the e2e login flow in a real
  browser. If a future frontend host is on a different domain the design
  must change to a proxy.
- [Missing `Secure` in a non-DEBUG http deployment] → prod is https-only with
  HSTS. Dev runs with `DEBUG=True`.
- [Legacy body path left in place forever] → tasks include the removal
  follow-up with a named date, and the transition claims fallback is tied to
  it.
- [Two tabs both migrating a localStorage token in the body] → both succeed
  (stateless), both receive the cookie, both delete the local copy.
- [Startup retries hammer a backend that is coming back] → three attempts
  per tab with backoff, then event-driven only. Negligible.
- [e2e helpers that log in through the API and stash tokens] → they call the
  UI login form and read only `access_token`; unaffected. Any helper that
  posts to `/api/auth/login` directly and expects `refresh_token` in the body
  must switch to reading the cookie or drop the assertion.

## Migration Plan

1. Deploy backend and web UI together (one image tag, as today).
2. Already-logged-in browsers: first 401 after deploy → refresh with body
   token → cookie set, local copy deleted. No user-visible effect.
3. Fresh logins get the cookie directly.
4. After 7 days every pre-change refresh token has expired. Ship the
   follow-up that removes the body path, the `RefreshRequest` schema, and the
   `auth_time`/`pwv` fallbacks; regenerate OpenAPI.
5. Rollback: revert the deploy. Browsers that migrated to the cookie hold no
   localStorage refresh token and will be logged out on their next access
   expiry; that is the only cost of a rollback and it is bounded to the
   rollout window.

## Open Questions

None that change the specs or tasks. Whether the absolute cap should be
shorter than a year is a settings value and can be tuned after launch.
