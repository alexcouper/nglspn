## Context

Broadcast emails are sent from the Django admin via `BroadcastEmailAdmin.send_view()`. Currently, clicking "Send" calls `HANDLERS.email.send_broadcast()` synchronously — iterating all recipients and sending SMTP emails one-by-one within the HTTP request cycle. This causes the admin UI to hang for the duration of the send.

The project already uses `django-tasks` with `DatabaseBackend` in production for other email types (verification, approval, notifications). The infrastructure for async task execution is in place.

## Goals / Non-Goals

**Goals:**
- Admin send action returns immediately after enqueuing the broadcast task
- Broadcast emails are sent in the background by the task worker
- Admin UI reflects that a send is in progress (not just "draft" or "sent")

**Non-Goals:**
- Retry logic for individual failed emails (current behavior logs failures and continues — keep that)
- Progress bar or real-time send progress in the admin UI
- Batching or rate-limiting of outgoing emails

## Decisions

### 1. Single task per broadcast (not per-recipient)

Enqueue one `send_broadcast_email` task per broadcast, not one task per recipient.

**Rationale**: The current `send_broadcast()` method already handles iterating recipients, tracking success/failure counts, and updating the broadcast record. Wrapping this in a single task is the minimal change. Per-recipient tasks would require restructuring the handler and the status tracking model for no immediate benefit.

**Alternative considered**: Per-recipient tasks would give better parallelism and individual retry, but adds complexity disproportionate to current scale.

### 2. Add a `status` field to `BroadcastEmail`

Add a `status` field with values: `draft`, `queued_for_sending`, `sending`, `sent`, `failed`.

**Rationale**: Currently, sent status is inferred from `sent_at` being non-null. With async sending, we need intermediate states to prevent double-sends and to show progress in the admin. Two intermediate states provide a clear handoff: the admin view sets `queued_for_sending` (enqueued but not yet picked up), and the task transitions to `sending` when it starts processing (claiming the work). The `sent_at` and `sent_by` fields remain for recording completion.

**Alternative considered**: Using a boolean `is_sending` flag — rejected because a proper status field is cleaner and extensible.

### 3. Two-phase status transition for safe handoff

The admin view sets status to `queued_for_sending` and enqueues the task. The task transitions to `sending` as its first step (claiming the broadcast), then to `sent` or `failed` on completion. The task receives `broadcast_id` and `sent_by_user_id` as arguments.

**Rationale**: The `queued_for_sending` → `sending` transition acts as a claim mechanism. The admin view only needs to guard against re-enqueue (check status is `draft`), and the task confirms it owns the work by transitioning from `queued_for_sending` to `sending`. django-tasks serializes arguments as primitives, so we pass user ID for the `sent_by` field.

## Risks / Trade-offs

- **Double-send prevention**: The admin view only enqueues if status is `draft`. The task only proceeds if it can transition from `queued_for_sending` to `sending`. This two-phase approach prevents both duplicate enqueues and duplicate task execution.
- **Task failure**: If the worker crashes mid-send, the broadcast stays in `sending` state. This is acceptable — an admin can investigate and the `BroadcastEmailRecipient` records show which emails were actually delivered. → No automated recovery needed for now.
- **Testing**: `ImmediateBackend` in DEBUG mode means the task still runs synchronously in dev/test. This is fine — it matches existing behavior for other tasks.
