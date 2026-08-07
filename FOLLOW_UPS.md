# Follow-ups

Gaps found while reviewing. None blocks anything.

Items 1–4 are frontend fixes on `/profile/following` and are resolved. Items 5
and 6 are open, and unrelated to that page.

## 1. No way to unfollow a single channel from the following page — done

Expanding a row listed the project's channels as static `Followed` /
`Not followed` badges, so narrowing a subscription meant visiting each project
page and using the follow popover there.

The badges are now checkboxes. The toggle logic that `FollowPopover` had is
extracted to `src/web-ui/src/hooks/useChannelToggle.ts` and the markup to
`src/web-ui/src/components/ChannelToggleList.tsx`, so both screens share one
implementation. The extracted version writes state through functional updates —
the popover's original built both the optimistic write and the rollback from a
render-closure snapshot, so a failure could discard a concurrent toggle of a
different channel.

## 2. The empty-state link pointed at `/discover`, which 404s — done

`href` is now `/projects`, which is where Discover lives.

## 3. Unfollowing the last channel unfollows the project — done

A Follow with no followed channels notifies about nothing, so
`DELETE /api/projects/{slug}/follow/channels/{channel_id}` now deletes the
Follow when it removes the last `FollowedChannel`. It returns
`200 FollowStateResponse` rather than `204` so the caller learns the resulting
project-level state instead of duplicating the rule client-side. Idempotent
while other channels remain; once the Follow is gone a repeat is a 404.

## 4. Nested interactive elements in the row header — done

The row header put the project `<Link>` inside the expand `<button>`. The
chevron is now its own button with `aria-expanded` / `aria-controls`, and the
link sits outside it.

## 5. Nothing garbage-collects abandoned image uploads

`services/images/django_impl/handler.py:151`, `src/web-ui/src/lib/uploadImage.ts:86`

`ProjectImage` rows are created `PENDING` before the client PUTs to S3. If the
PUT fails, `uploadImage` throws and the row is left behind — no client-side
cleanup, no server-side sweep. `grep` finds nothing that deletes on
`upload_status`.

Reading them is now handled: `ProjectImageQuerySet.uploaded()` /
`ProjectImage.is_uploaded` gate every display path (review finding 3). So these
rows are inert rather than harmful. But they still accumulate, one per failed
upload, each holding a `storage_key` for an object that may or may not exist —
`PENDING` means "we never heard back", not "there is nothing there", so a PUT
that succeeded while the completion call failed leaves an orphaned S3 object
with no row that admits to owning it.

Worth a periodic task that deletes `PENDING` rows older than some threshold,
attempting the storage delete first. Sizing it needs a count from prod — the
table may well be tiny, in which case this stays a note.

## 6. The dev task-checker still reads `django_tasks`' table directly

`naglasupan-hq:infra/modules/services/backend-task-checker/function/backend-task-checker/handler.py:106`

Raised by the infra agent while removing the CronJobs' hand-written INSERTs.

```sql
SELECT COUNT(*) FROM django_tasks_database_dbtaskresult WHERE status = 'READY'
```

The same coupling the digest CronJobs had — a third-party library's table name
and status vocabulary hard-coded outside the app — but a `SELECT`, so the failure
mode is milder: on a library schema change the worker stops being woken rather
than tasks silently failing.

Two things make this a separate decision rather than part of that change:

- **It is instantiated**, at `infra/dev/app.tf:147`. The notification-scheduler
  module was dead code; this one is live, so deleting it breaks dev's terraform.
- **It is dev-only.** No `infra/prod/*.tf` references it. Prod runs the worker as
  an always-on k8s Deployment (`k8s/base/backend/worker-deployment.yaml`) with no
  queue-depth scaling, so this exists solely to wake dev's scale-to-zero Scaleway
  container. Blast radius is a dev worker that doesn't start.

**The obstacle to the obvious fix.** A management command exposing the count
doesn't close this on its own: the checker is a Scaleway serverless function
(`pg8000` + `urllib`), not a Django process. It can reach the database and the
Scaleway API and nothing else — there is no way for it to run `manage.py`. So the
count has to travel over a wire it can already speak:

- **An authenticated HTTP endpoint on the backend** the function `GET`s. Closes
  the coupling properly. Costs an endpoint, its auth, and a check that hitting it
  doesn't itself wake a scaled-to-zero backend container.
- **A management command anyway**, as the single supported definition of "queue
  depth" — useful for humans and as the endpoint's implementation, but it needs
  the endpoint (or some other caller) to be reachable from the function.
- **Keep the SQL, name the table once** — a terraform variable or module constant
  so a library change is a one-line edit. Cheapest; doesn't remove the coupling.
- **Accept it.** Defensible while it stays dev-only.

Worth revisiting if the checker ever moves to prod, which would change the blast
radius from "dev is slow" to "prod tasks don't run".
