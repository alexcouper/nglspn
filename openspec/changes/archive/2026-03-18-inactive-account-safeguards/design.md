## Context

The platform uses `is_active` on the User model to soft-disable accounts. Authentication already rejects inactive users at three points: login, token refresh, and JWT validation. Broadcast emails (platform updates, competition results, individual recipients) all filter `is_active=True` when resolving recipients.

However, the discussion notification system (`services/notifications/django_impl/handler.py`) collects recipients — project owners, thread authors, and previous participants — without checking `is_active`. Both immediate and digest notification paths are affected.

There are no existing tests verifying inactive-user exclusion for any of these systems.

## Goals / Non-Goals

**Goals:**
- Fix the discussion notification bug so inactive users never receive notification emails
- Add test coverage for all inactive-user exclusion points (auth, broadcast emails, discussion notifications)

**Non-Goals:**
- Changing how accounts become inactive (admin workflow stays as-is)
- Adding is_active checks to the web UI or API permission layer (JWT validation already handles this)
- Notification preferences or opt-out — separate concern

## Decisions

### 1. Filter at notification creation, not at send time

Add `is_active=True` to the recipient queryset in `create_notifications_for_discussion()` rather than filtering in `send_batch_notifications()`.

**Rationale**: Preventing Notification objects from being created for inactive users is cleaner than creating them and skipping at send time. It avoids dead notification records and matches how broadcast emails work (filter at recipient resolution).

**Alternative considered**: Filter at send time in `send_batch_notifications()`. Rejected because it still creates notification records for users who will never see them.

### 2. Test structure: one test module per concern

Organize tests into focused modules:
- `test_inactive_user_auth.py` — login, token refresh, JWT validation
- `test_inactive_user_emails.py` — broadcast recipients, discussion notifications

**Rationale**: Keeps related assertions together, easy to run a subset. Follows existing test organization patterns in the codebase.

### 3. Use factory-based test setup

Create inactive users via the existing User model/factory with `is_active=False` rather than creating users and then deactivating them.

**Rationale**: More readable test setup — intent is clear from construction.

## Risks / Trade-offs

- **Existing notifications for inactive users**: If any Notification records already exist for inactive users, they won't be cleaned up. This is acceptable — they'll simply never be sent since the user can't login to trigger anything. → No migration needed.
- **Future notification channels**: If we add new notification paths (e.g., in-app notifications), they'll need their own `is_active` checks. → The spec and tests document the expected behavior pattern.
