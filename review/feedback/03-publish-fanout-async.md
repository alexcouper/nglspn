# 03. Article publish fans out notifications inline in the request

**Finding:** I3 (backend review §12) — `publish` calls
`HANDLERS.notifications.create_notifications_for_article` directly inside the
POST; discussions enqueue a task instead.
**Alex:** Good point, we should be doing this async. Propose a change.
**Type:** fix proposal
**Effort:** S–M, one new task function, four changed lines in the handler, one
changed test and two new ones. The thinking is in where the `enqueue` goes, not
in the amount of code.

## What is actually happening

`services/articles/django_impl/handler.py:139-167`:

```python
with transaction.atomic():
    article.state = ArticleState.PUBLISHED
    ...
    article.save(update_fields=["state", "published_at", "global_visibility"])
    if article.slug is None:
        assign_unique_article_slug(article)

if not _is_backdated(effective_published_at):
    from services import HANDLERS
    HANDLERS.notifications.create_notifications_for_article(article.id)
```

The fan-out is **outside** the `atomic()` block. `create_notifications_for_article`
(`services/notifications/django_impl/handler.py:181-245`) iterates every
`FollowedChannel` on the article's channel and does a `get_or_create` per
recipient — two round trips each. Every active non-system user auto-follows the
house project (`apps/follows/services.py:21-45`), so a house-channel publish is
~2N queries inside `POST /articles/{id}/publish`. A timeout there leaves the
article published with a partial recipient set and no retry.

Contrast `services/discussions/django_impl/handler.py:40-45`, which enqueues.

## The transaction question — the premise needs correcting

The brief asks me to make sure the enqueue happens *after* commit, via
`transaction.on_commit`. For this deployment that is backwards, and I would not
do it.

- `grep -rn "on_commit" --include='*.py'` over `src/django-backend` returns **zero
  hits**. Nothing in the repo uses it.
- The pinned queue is `django-tasks 0.12.0` + `django-tasks-db 0.12.0`
  (`uv.lock:484-499`, `pyproject.toml:30`). Version 0.12 **removed** the
  `ENQUEUE_ON_COMMIT` machinery that 0.9 had. `grep enqueue_on_commit` over the
  installed 0.12 package returns nothing.
- `django_tasks_db.backend.DatabaseBackend.enqueue` is a plain
  `DBTaskResult.objects.create(...)` (`backend.py:60-107`). It writes a row in the
  caller's transaction. There is no broker.

Because the queue *is* the database, the correct placement is the opposite of the
usual advice:

- **Enqueue inside `transaction.atomic()`** and the task row and the article's
  `state = PUBLISHED` commit as one unit. A worker polling
  `DBTaskResult.objects.ready()` runs under READ COMMITTED and cannot see the task
  row before the article write is visible. No race.
- **Enqueue outside** (where the call sits today) and there is a real window: the
  article commits, the process dies before the enqueue, and nobody is ever
  notified — with no record that it should have happened.

So the change moves the fan-out *into* the atomic block, which both fixes the
request-latency problem and closes a lost-notification window the current inline
call has. `transaction.on_commit` would reintroduce that window.

(The same argument applies to `create_discussion_notifications` at
`services/discussions/django_impl/handler.py:45`, which enqueues after
`Discussion.objects.create` with no surrounding transaction. Out of scope here,
but it is the same one-line move and worth doing in the same pass.)

## Proposed change

### 1. `api/tasks/notifications.py` — add the task next to the discussion one

```python
@task()
def create_article_notifications(article_id: str) -> None:
    from services import HANDLERS  # noqa: PLC0415

    HANDLERS.notifications.create_notifications_for_article(UUID(article_id))
```

`str` in, `UUID` inside — same as `create_discussion_notifications` at `:12-16`.
Task arguments go through `normalize_json`, so a bare `UUID` would not survive
the DatabaseBackend.

### 2. `services/articles/django_impl/handler.py` — enqueue inside the transaction

```diff
         effective_published_at = published_at or timezone.now()
 
         with transaction.atomic():
             article.state = ArticleState.PUBLISHED
             article.published_at = effective_published_at
             article.global_visibility = _resolve_visibility_on_publish(article)
             article.save(update_fields=["state", "published_at", "global_visibility"])
             if article.slug is None:
                 assign_unique_article_slug(article)
-
-        if not _is_backdated(effective_published_at):
-            # Notification fan-out is owned by the notifications service so
-            # the same trigger drives email + in-app paths consistently.
-            from services import HANDLERS  # noqa: PLC0415
-
-            HANDLERS.notifications.create_notifications_for_article(article.id)
+            if not _is_backdated(effective_published_at):
+                # Fan-out is ~2N queries on a house-channel publish, so it goes
+                # to the worker. Enqueued *inside* the transaction on purpose:
+                # the queue is a table (django-tasks-db), so the task row and
+                # the PUBLISHED write commit together — a worker cannot see the
+                # task before the article, and a crash cannot lose the enqueue.
+                from api.tasks.notifications import (  # noqa: PLC0415
+                    create_article_notifications,
+                )
+
+                create_article_notifications.enqueue(str(article.id))
 
         return article
```

Point (c) from the brief: **`_is_backdated` stays here and cannot move into the
task.** The task receives only an article id. From the row alone, "published with
an explicit `published_at` seven days ago" and "published normally an hour ago
while the worker was backed up" are indistinguishable — both are just a
`published_at` in the past. The decision has to be taken where the request payload
is still in scope. Leaving the guard in `publish` also keeps the fast path free of
a pointless enqueue on a bulk backfill.

### 3. Idempotency on retry — point (b): already safe, with one caveat

`create_notifications_for_article` uses
`Notification.objects.get_or_create(recipient=user, article=article, ...)`
(`services/notifications/django_impl/handler.py:221-228`), backed by the partial
unique constraint `notifications_recip_article_uniq`
(`apps/notifications/models.py:64-68`). A re-run creates no duplicate rows, and
the `house_channel_article_enqueued` log line is inside `if created`
(`:229-245`), so it does not re-emit either. Re-running the task after a partial
failure resumes correctly.

The caveat is the other direction: **django-tasks-db does not retry.**
`db_worker.run_task` (`management/commands/db_worker.py:149-190`) catches
`BaseException`, calls `set_failed(e)`, and moves on. There is no attempt counter
and no requeue. So going async trades a *visible* failure (the author's publish
request 500s) for an *invisible* one (the article is published, some followers
are notified, and only a `FAILED` row in `django_tasks_database_dbtaskresult`
records it).

Two cheap mitigations, both worth taking:

- Wrap the task body so a failure logs a structured line naming the article id,
  at `ERROR`, then re-raises — the `FAILED` row alone is not something anyone
  watches.
- Make the fan-out resumable at recipient granularity rather than dying on the
  first bad row: the loop at `:216-245` is already per-recipient, so a
  `try/except/log/continue` around the `get_or_create` turns "one bad user kills
  the whole fan-out" into "one user missed". Whether that is worth it depends on
  whether you would rather fail loudly; I would take the continue, because
  `get_or_create` here can only realistically fail on a database problem that
  will also fail the next recipient.

## Tests

### What breaks

Nothing, as it happens — and that is itself the problem.

`conftest.py:22-28` forces `ImmediateBackend` in every test. In django-tasks
0.12.0, `ImmediateBackend.enqueue` calls `_execute_task` **synchronously**
(`backends/immediate.py:107`); the `transaction.on_commit` wrapper that 0.9 had is
gone. So the whole chain — `publish` → `enqueue` → task → handler — runs inside
the test call, and every existing assertion holds verbatim:

- `services/notifications/django_impl/test_article_fanout.py:355-372`
  (`test_live_publish_creates_in_app_row`) — passes.
- `:374-391` (`test_backdated_publish_via_handler_creates_no_rows`) — passes; the
  guard did not move.
- `services/articles/django_impl/test_handler.py:284-296`
  (`test_delete_cascades_notifications`) — passes.
- `services/articles/django_impl/test_handler.py:267-276`
  (`test_live_publish_invokes_notification_handler`) patches
  `DjangoNotificationHandler.create_notifications_for_article` and asserts
  `assert_called_once_with(article.id)`. The patch still fires through the task,
  and `UUID(str(x)) == x`, so the assertion still passes.

That last one is the meaningful loss. It reads as though it pins the execution
model and it does not — after this change it would pass equally whether publish
enqueued or called inline. The review's coverage gap 2 names exactly this: *"none
asserting where the fan-out runs (inline vs enqueued)"*.

### What to add

**1. Pin the execution model.** `services/articles/django_impl/test_handler.py`,
replacing `test_live_publish_invokes_notification_handler`:

```python
def test_live_publish_enqueues_the_fan_out_task(self):
    article = ArticleFactory()

    with patch("api.tasks.notifications.create_article_notifications.enqueue") as enqueue:
        self.handler.publish(article.id)

    enqueue.assert_called_once_with(str(article.id))


def test_backdated_publish_enqueues_nothing(self):
    article = ArticleFactory()

    with patch("api.tasks.notifications.create_article_notifications.enqueue") as enqueue:
        self.handler.publish(article.id, published_at=timezone.now() - timedelta(days=7))

    enqueue.assert_not_called()
```

The `str(...)` in the assertion is load-bearing: it is what stops someone passing
a `UUID` that the DatabaseBackend cannot serialise but the ImmediateBackend
accepts silently.

**2. Keep the integration assertion meaningful.** `test_live_publish_creates_in_app_row`
stays exactly as it is (`test_article_fanout.py:355`), but its docstring should
say what it now proves: publish → enqueue → task → handler, end to end, on the
immediate backend. That is real coverage of the wiring, not an accident.

**3. Pin the transaction placement.** The property worth guarding is "the enqueue
does not happen if the publish write rolls back":

```python
def test_a_failed_publish_write_enqueues_nothing(self):
    article = ArticleFactory()

    with (
        patch("api.tasks.notifications.create_article_notifications.enqueue") as enqueue,
        patch.object(Article, "save", side_effect=IntegrityError),
        pytest.raises(IntegrityError),
    ):
        self.handler.publish(article.id)

    enqueue.assert_not_called()
```

**4. Fill coverage gap 2's other half.** A fan-out test at scale, in
`test_article_fanout.py`, asserting the query count does not depend on the article
— use the `_count_queries` helper pattern from
`services/follows/django_impl/test_query.py:58-61`. It will not be constant (the
fan-out is inherently O(N)), so assert instead that `publish` itself is constant:
count queries for `publish` with 1 follower and with 20 followers, patching
`enqueue`, and assert they are equal. That is the assertion that fails if anyone
puts the fan-out back inline.

## Risks and what this does not cover

- **Worker availability becomes a correctness dependency.** If the `db_worker`
  deployment is down, publishes succeed and nobody is notified until it comes
  back. Recoverable — the task rows queue up — but it is a new failure mode. The
  digest path already has this property, so it is not a new class of risk.
- **A `FAILED` task is terminal.** No automatic retry exists (see above). Manual
  recovery is re-enqueuing the task by id; a re-publish also works, because the
  fan-out is idempotent, but it moves `published_at` (finding 18).
- **Finding 18 gets worse in one respect and better in another.** `publish` is
  still not guarded against re-publish, so a double-click still shifts
  `published_at` and re-enqueues; but the response now returns fast, so the
  "author retries after a slow response" trigger the review named largely goes
  away. The guard is still worth adding, separately.
- **No OpenAPI change**, no migration, no frontend change. The response body and
  status code are unchanged; only the latency drops.
- **Does not change the discussion path**, which has the same
  enqueue-outside-the-transaction window. One-line fix, same reasoning, worth
  including if you want them consistent.
