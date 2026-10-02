# Spec Delta

## Purpose

Defines how a signed-in session is issued, kept alive, stored in the browser
and ended, so that an active user stays logged in for weeks rather than being
cut off seven days after typing their password.

## ADDED Requirements

### Requirement: Session tokens and their lifetimes
Login SHALL issue a short-lived access token and a long-lived refresh token.
The access token SHALL expire 30 minutes after issue. The refresh token SHALL
expire 30 days after issue (the idle lifetime). Every refresh token SHALL record
the time of the original password login, and no refresh token derived from that
login SHALL be accepted more than 365 days after it (the absolute lifetime).

#### Scenario: Access token expires after 30 minutes
- **WHEN** a request presents an access token issued more than 30 minutes ago
- **THEN** the request is rejected with HTTP 401

#### Scenario: Refresh token expires after 30 idle days
- **WHEN** a refresh is attempted with a refresh token issued more than 30 days ago
- **THEN** the refresh is rejected with HTTP 401

#### Scenario: Session cannot outlive the absolute cap
- **WHEN** a refresh is attempted with a refresh token whose original login was more than 365 days ago, even if the token itself was issued less than 30 days ago
- **THEN** the refresh is rejected with HTTP 401

### Requirement: Refresh extends the session
A successful refresh SHALL return a new access token and SHALL issue a new
refresh token whose idle expiry is 30 days from the time of the refresh. The new
refresh token SHALL carry forward the original login time. The previous refresh
token SHALL remain valid until its own expiry, so that concurrent refreshes from
several tabs cannot invalidate each other.

#### Scenario: Active user is never logged out by the idle limit
- **WHEN** a user refreshes at least once every 30 days
- **THEN** every refresh succeeds until the absolute lifetime is reached

#### Scenario: Refresh issues a new refresh token
- **WHEN** a valid refresh token is presented
- **THEN** the response carries a new access token and a new refresh token with an expiry 30 days from now

#### Scenario: Concurrent refreshes from two tabs both succeed
- **WHEN** two requests present the same valid refresh token at the same time
- **THEN** both receive a new access token and neither is rejected because of the other

### Requirement: Refresh token is an HttpOnly cookie on the API host
The refresh token SHALL be delivered to the browser only as a cookie set by the
API host with the attributes `HttpOnly`, `SameSite=Lax`, a `Path` restricted to
the authentication endpoints and a `Max-Age` equal to its idle lifetime. In
production the cookie SHALL also be `Secure`. The login response body SHALL NOT
contain the refresh token. The refresh endpoint SHALL read the token from that
cookie.

#### Scenario: Login sets the cookie and omits the token from the body
- **WHEN** a user logs in successfully
- **THEN** the response sets the refresh-token cookie with the attributes above
- **AND** the JSON body contains `access_token`, `token_type` and `is_verified` but no `refresh_token`

#### Scenario: Refresh reads the cookie
- **WHEN** the refresh endpoint is called with a valid refresh-token cookie and no body
- **THEN** it responds HTTP 200 with a new access token and sets a new refresh-token cookie

#### Scenario: Refresh without any token
- **WHEN** the refresh endpoint is called with no cookie and no legacy body token
- **THEN** it responds HTTP 401

#### Scenario: Cookie is not sent to non-auth endpoints
- **WHEN** the browser requests any endpoint outside the authentication path
- **THEN** the refresh-token cookie is not included in the request

#### Scenario: Cookie is not readable by script
- **WHEN** page script reads `document.cookie`
- **THEN** the refresh-token cookie is not present in the result

### Requirement: Refresh tokens issued before the cookie are rejected
The refresh endpoint SHALL read the token only from the cookie and SHALL
ignore a token in the request body. A refresh token without the login-time and
password-version claims SHALL be rejected. The web UI SHALL delete any refresh
token it finds in localStorage.

#### Scenario: Token in the body is ignored
- **WHEN** the refresh endpoint is called with no cookie and a valid refresh token in the JSON body
- **THEN** it responds HTTP 401

#### Scenario: Token without the new claims
- **WHEN** a refresh token carries no login time or no password version
- **THEN** the refresh is rejected with HTTP 401

#### Scenario: Stale token in localStorage is removed
- **WHEN** the web UI starts with a refresh token in localStorage
- **THEN** the key is removed and no request carries its value

### Requirement: A session is restored from the cookie alone
When the web UI starts without an access token it SHALL ask the refresh
endpoint once. A new access token restores the session; HTTP 401 means there is
no session. A logout whose request did not reach the backend SHALL be repeated
on a later start before any restore is attempted, and a successful login SHALL
cancel that.

#### Scenario: localStorage was purged but the cookie remains
- **WHEN** a page loads with no access token and a valid refresh-token cookie
- **THEN** the header shows the signed-in user without visiting the login page

#### Scenario: No session at all
- **WHEN** a page loads with no access token and no cookie
- **THEN** one refresh request is made and the header shows the logged-out state

#### Scenario: Logout that never reached the backend
- **WHEN** the user logged out while the backend was unreachable and later loads a page
- **THEN** the logout is sent again and the session is not restored

### Requirement: Logout endpoint clears the cookie
There SHALL be a logout endpoint that expires the refresh-token cookie. It SHALL
succeed whether or not a cookie was present. The web UI's logout action SHALL
call it and SHALL clear the access token locally regardless of the call's
outcome.

#### Scenario: Logout expires the cookie
- **WHEN** the logout endpoint is called with a refresh-token cookie
- **THEN** it responds with a `Set-Cookie` that expires the cookie
- **AND** a subsequent refresh using the old cookie value still succeeds until that token's own expiry (statelessness is unchanged)

#### Scenario: Logout with no cookie
- **WHEN** the logout endpoint is called without a cookie
- **THEN** it responds with success

#### Scenario: Web UI logout survives a backend failure
- **WHEN** the user clicks Log out and the logout request fails
- **THEN** the access token is removed locally and the UI shows the logged-out state

### Requirement: Rejected refresh ends the session in the browser
When the refresh endpoint rejects the token (HTTP 401), the web UI SHALL discard
the access token, treat the user as logged out and, on a page that requires
login, send them to the login page with a return path.

#### Scenario: Expired refresh token
- **WHEN** a request gets HTTP 401 and the subsequent refresh also gets HTTP 401
- **THEN** the access token is cleared and the header shows the logged-out state

### Requirement: Transient failures at startup do not show the user as logged out
When the web UI holds an access token and its startup check of the current user
fails for a reason other than a rejected refresh token (network error, HTTP 5xx,
HTTP 429), it SHALL keep the token, keep the header in its loading state and
retry the check with increasing delays. If the retries are exhausted it SHALL
retry again when the browser reports it is online, when the tab regains focus,
and whenever a later refresh succeeds. It SHALL NOT clear the token or show the
"Log in" control because of a transient failure.

#### Scenario: Backend restarting during page load
- **WHEN** the current-user check fails with HTTP 503 and the next attempt succeeds
- **THEN** the header shows the signed-in user without any user action and the token was never cleared

#### Scenario: Offline at page load
- **WHEN** the current-user check fails with a network error and all retries fail
- **THEN** the token is kept
- **AND** when the browser reports it is online again the check runs again and, on success, the header shows the signed-in user

#### Scenario: Later request succeeds first
- **WHEN** the startup check has given up and a request elsewhere on the page later refreshes the access token successfully
- **THEN** the current-user check runs again and the header shows the signed-in user

#### Scenario: A page that requires login waits rather than redirecting
- **WHEN** a page that requires login mounts while the startup check is retrying
- **THEN** it does not redirect to the login page while a token is still held
