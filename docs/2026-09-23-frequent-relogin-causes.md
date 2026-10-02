# Why Naglasúpan asks you to log in again so often

Investigation, 2026-09-23. Nothing changed yet — this records how a login
session actually lives and dies today, and ranks the reasons a returning user
lands on `/login` (or sees a logged-out header) far more often than on other
sites.

**Status, 2026-10-02:** causes 1, 2 and 3 are fixed by the OpenSpec change
[`keep-users-logged-in`](../openspec/changes/keep-users-logged-in/proposal.md);
everything below describes the behaviour before it.

## How a session works today

There is no server-side session. Login returns two JWTs and the browser keeps
them in `localStorage`.

| Piece | Where | Lifetime |
|-------|-------|----------|
| Access token | `settings.py:240`, minted in `api/auth/jwt.py:14` | 30 minutes |
| Refresh token | `settings.py:241`, minted in `api/auth/jwt.py:29` | 7 days, **fixed from the moment of login** |
| Storage | `src/lib/api/base.ts:47-58` — `localStorage` keys `access_token`, `refresh_token`, plus a script-set `logged_in` cookie nothing reads | until the browser drops it |
| Refresh | `POST /api/auth/refresh` (`api/routers/auth.py:149-175`) | returns a new access token **only**; the refresh token is never rotated or extended |

On every page load `AuthProvider` (`src/contexts/auth.tsx:33-45`) calls
`/api/auth/me`. After 30 minutes that gets a 401, `APIClient` tries a refresh
(`base.ts:83-114`), and one of three things happens:

- **refreshed** — retry, user is set, all good.
- **invalid** (refresh returned 401) — tokens cleared, `auth:logout` fired,
  user goes to `/login`.
- **transient** (network error, 5xx, anything not 401) — tokens are kept, but
  `checkAuth` swallows the error and never retries. `user` stays `null`.

Compare with a typical site: a server-side session cookie with a 2–4 week
sliding expiry, extended on every visit, set `HttpOnly` by the server.

## Probable causes, most likely first

### 1. The refresh token is a hard 7-day cutoff, not a sliding window

`create_refresh_token` stamps `exp = now + 7 days` at login, and `/refresh`
never issues a new one. So the session ends exactly 7 days after you last
typed your password, however active you were in between. Daily users get
logged out every week; weekly users are logged out on essentially every
visit. This is the single biggest difference from sites that "keep you logged
in": they rotate or extend the long-lived credential on use.

Confirmation: log in, note the time, use the site every day; you will be
kicked out on day 7 to the minute.

### 2. A single failed request at page load looks exactly like being logged out

If the access token has expired (anything over 30 minutes since the last
request) and the refresh call fails for a *transient* reason, `checkAuth`
catches the error, sets `isLoading` false and leaves `user` as `null`.
`Navigation.tsx:77-79` then renders the "Log in" button. Nothing retries, and
nothing tells the user their credentials are still valid. Reloading the page
would fix it; logging in "again" also fixes it, which is what a user naturally
does — so it registers as a re-login even though the tokens were fine.

Things that make the very first request of a visit fail transiently:

- The backend pod restarting after a deploy (single replica in
  `k8s/base/backend/deployment.yaml`; deploy days on `main` are frequent).
- A cold DB connection or a slow first response after idle; `conn_max_age=600`
  means the first request after 10 minutes reopens the connection.
- Flaky mobile connectivity in the first second after the tab foregrounds.
- The Scaleway serverless variant of the stack scales to zero in dev
  (`infra/dev/app.tf:108,122`) and overnight via the scaler function, so a
  cold start is guaranteed there.

On protected pages the picture is worse: `useRequireAuth` sees
`api.isAuthenticated()` still true so it does *not* redirect, giving a page
whose header says logged out while its content loads as you.

### 3. Safari (and every iOS browser) purges `localStorage` after 7 days of non-use

Intelligent Tracking Prevention deletes all script-writable storage —
`localStorage` and cookies set via `document.cookie` — for a site after seven
days of Safari use without interacting with that site. Both of our tokens and
the `logged_in` cookie are script-written, so they are all in scope. An
`HttpOnly` cookie set by a `Set-Cookie` header with an explicit long `Max-Age`
is what survives ITP; that is what the "other sites" are doing. If you use
Safari or an iPhone, this and cause 1 both land at the same 7-day mark.

### 4. Storage is per origin, per profile, per app

`localStorage` does not travel. Any of these gives a fresh, logged-out store:

- A different browser profile, or a private window.
- An iOS home-screen web app versus Safari itself.
- A different host — `www.naglasupan.is` does not resolve today, so this is
  not biting in prod, but a dev or preview host is a separate login.
- "Clear site data on close" or a privacy extension.

### 5. Ruled out

- **Secret key rotation.** `JWT_SECRET_KEY` falls back to `SECRET_KEY`, which
  is a sealed k8s secret last resealed 2026-05-12. A rotation would invalidate
  every token at once, but it is not happening on deploys.
- **Multiple tabs racing on refresh.** Refresh tokens are not rotated, so two
  tabs refreshing concurrently cannot invalidate each other. (Rotating them,
  as cause 1 suggests, would need a grace window for exactly this.)
- **The `logged_in` cookie.** Set and cleared in `base.ts`, read nowhere.
- **Clock skew.** Tokens are minted and verified on the same backend; PyJWT's
  `iat`/`exp` checks would need more than 30 minutes of skew to matter.

## What would fix it

In order of effect:

1. **Slide the refresh token.** Have `/refresh` return a new refresh token
   with a fresh `exp` (and accept the old one for a short grace period so
   concurrent tabs don't fight). Raise `JWT_REFRESH_TOKEN_EXPIRE_DAYS` to
   30 or more. This alone turns "weekly" into "monthly, and never while
   active".
2. **Retry transient failures on load** instead of silently rendering the
   logged-out header. `checkAuth` already has the distinction
   (`AuthTransientError` vs `AuthExpiredError`); it just throws it away.
3. **Move the refresh token to an `HttpOnly`, `Secure`, `SameSite=Lax` cookie**
   set by the backend. That fixes the Safari purge and takes the long-lived
   credential out of reach of any script. It is the larger change: CORS
   credentials and a CSRF story for the refresh endpoint.

   It does **not** let server components authenticate
   (`ArticleAuthoringRoute.tsx:23` notes they cannot, and that still holds).
   The cookie is host-only on `api.naglasupan.is`, so the browser never sends
   it to the Next.js server on `naglasupan.is`, and server components call the
   API without a browser in between. An earlier version of this document
   claimed otherwise, and said the cookie had to be scoped to the parent
   domain; it does not, because the browser talks to the API host directly and
   the two hosts are same-site. Authenticating server components would take a
   same-origin API proxy, which is a separate change.
