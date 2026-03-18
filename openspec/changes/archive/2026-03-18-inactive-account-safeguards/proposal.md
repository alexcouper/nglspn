## Why

Inactive accounts should be fully excluded from the platform — they can't login, and they shouldn't receive any emails. Login and broadcast emails already enforce this, but discussion notifications don't filter out inactive users. We also lack test coverage confirming these safeguards, making it easy for regressions to slip in.

## What Changes

- Add `is_active=True` filter to discussion notification recipient queries (both immediate and digest)
- Add tests confirming inactive users cannot authenticate (login, token refresh, JWT validation)
- Add tests confirming inactive users are excluded from broadcast email recipients (platform updates, competition results, individual recipients)
- Add tests confirming inactive users are excluded from discussion notification recipients

## Capabilities

### New Capabilities

- `inactive-account-exclusion`: Defines the rules for how inactive accounts are excluded across the platform — authentication, broadcast emails, and discussion notifications. Codifies existing implicit behavior into a testable spec.

### Modified Capabilities

_None._

## Impact

- **Backend code**: `services/notifications/django_impl/handler.py` — notification recipient collection needs `is_active` filtering
- **Tests**: New test files covering auth and email inactive-user exclusion
- **No API changes**: No endpoint signatures or responses change
- **No frontend changes**: No UI impact
