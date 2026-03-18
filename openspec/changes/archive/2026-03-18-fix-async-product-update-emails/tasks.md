## 1. Model changes

- [x] 1.1 Add `BroadcastEmailStatus` TextChoices to `apps/emails/models.py` with values: `draft`, `queued_for_sending`, `sending`, `sent`, `failed`
- [x] 1.2 Add `status` field to `BroadcastEmail` model, defaulting to `draft`
- [x] 1.3 Replace `is_sent` property to derive from `status == sent` (maintain backward compat for existing checks)
- [x] 1.4 Create and run migration

## 2. Background task

- [x] 2.1 Add `send_broadcast_email` task to `api/tasks/email.py` accepting `broadcast_id` and `sent_by_user_id`
- [x] 2.2 Task transitions status from `queued_for_sending` → `sending` (abort if not in `queued_for_sending`)
- [x] 2.3 Task calls existing `HANDLERS.email.send_broadcast()` to deliver emails
- [x] 2.4 Task transitions status to `sent` on completion, or `failed` on unhandled exception
- [x] 2.5 Task sets `sent_at` and `sent_by` on successful completion

## 3. Admin view changes

- [x] 3.1 Update `BroadcastEmailAdmin.send_view()` to set status to `queued_for_sending` and enqueue task instead of calling `send_broadcast()` directly
- [x] 3.2 Guard send action to only proceed when status is `draft`
- [x] 3.3 Update success message to indicate send has been queued (not completed)
- [x] 3.4 Hide send button on change form for non-draft broadcasts
- [x] 3.5 Add `status` to admin list display with badge styling

## 4. Handler refactor

- [x] 4.1 Update `send_broadcast()` to no longer set `sent_at`/`sent_by` (moved to task layer)
- [x] 4.2 `send_broadcast()` returns success/failure counts only — status transitions handled by task

## 5. Tests

- [x] 5.1 Test that send view enqueues task and sets status to `queued_for_sending`
- [x] 5.2 Test that send view rejects non-draft broadcasts
- [x] 5.3 Test that task transitions `queued_for_sending` → `sending` → `sent`
- [x] 5.4 Test that task aborts if broadcast is not in `queued_for_sending` state
- [x] 5.5 Test that task sets status to `failed` on unhandled exception
