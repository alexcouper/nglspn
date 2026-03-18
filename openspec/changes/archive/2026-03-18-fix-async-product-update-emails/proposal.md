## Why

The broadcast email send from the Django admin runs synchronously in the HTTP request cycle. When sending to many recipients, the admin UI hangs until all emails are delivered one-by-one via SMTP. This should use django-tasks to dispatch sending to the background worker, returning the admin response immediately.

## What Changes

- Move broadcast email sending to a background task using `django_tasks`
- The admin send action should enqueue the task and return immediately with a "sending in progress" message
- Track broadcast send status so the admin can see progress (pending → sending → sent)
- Individual per-recipient email delivery continues to be tracked via `BroadcastEmailRecipient`

## Capabilities

### New Capabilities

- `async-broadcast-send`: Background task execution for broadcast email delivery, including send status tracking

### Modified Capabilities

## Impact

- `apps/emails/admin.py` — `BroadcastEmailAdmin.send_view()` changes from synchronous send to task enqueue
- `services/email/django_impl/handler.py` — `send_broadcast()` called from task context instead of request context
- `api/tasks/email.py` — new task for broadcast sending
- `apps/emails/models.py` — may need send status field on `BroadcastEmail` to track in-progress state
