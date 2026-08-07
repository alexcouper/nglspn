# Follow-ups

Small gaps found while reviewing. None blocks anything.

Items 1 and 2 are frontend-only, on `/profile/following`.

## 1. No way to unfollow a single channel from the following page

`src/web-ui/src/app/profile/following/page.tsx:168`

Expanding a row lists the project's channels, but each one renders as a static
`Followed` / `Not followed` badge. The only mutation on the page is the
whole-project `Unfollow` button (`page.tsx:150`), so narrowing a subscription —
the common case once you follow more than a handful of projects — means visiting
each project page and using the follow popover there. The page header says as
much (`page.tsx:60`: "Manage per-channel subscriptions from each project's
page"), so this is a deliberate limitation rather than an oversight, but it makes
the one screen that shows every subscription the one screen where you can't
adjust them.

The plumbing already exists: `api.follows.followChannel` /
`unfollowChannel` (`src/web-ui/src/lib/api/follows.ts:38,48`), used by
`src/web-ui/src/components/FollowPopover.tsx:69`. The work is swapping the badge
for a toggle and reusing the popover's optimistic-update handling — including its
rollback on failure, since the list here is loaded once and never refetched.

## 2. The empty-state link points at `/discover`, which 404s

`src/web-ui/src/app/profile/following/page.tsx:82`

```tsx
<Link href="/discover" className="text-accent hover:underline">
  Discover projects
</Link>
```

There is no `/discover` route and no redirect or rewrite for it in
`src/web-ui/next.config.ts`. Discover lives at `/projects` — that's what the
"Discover" tab links to (`src/web-ui/src/app/projects/CategoryTabs.tsx:17`).

So a user with no follows sees the empty state and the single call to action on
it is dead. Fix is `href="/projects"`. This is the only `/discover` reference in
`src/web-ui/src`.

## 3. Nothing garbage-collects abandoned image uploads

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

## 4. The dev task-checker still reads `django_tasks`' table directly

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
