# Code review — Articles Authoring (branch vs `origin/main`)

Adds the article listing image + crop (replacing the mandatory hero), a two-step
image wizard, article digest emails, and collapses per-channel email/in-app
preferences into a single "followed" flag with per-kind user cadences.

Verified before reviewing:

- `cd src/django-backend && make test` — 1065 passed
- `cd src/web-ui && npx vitest run` — 126 passed
- `cd src/django-backend && make extract-openapi` — no diff, so
  `backend-openapi.json` is in sync with the routers/schemas in this change

## Status

| # | Finding | State |
|---|---------|-------|
| 1 | Notification opt-out lost in migration | **Done** — `xzpr 33b4`, but not as reviewed (see below) |
| 2 | Digest cron broken by the task rename | Backend **done** — `nnkr b401`; infra repo in progress |
| 3 | `auto` mode adopts an incomplete upload | **Done** — `wvvx` |
| 4 | N+1 on the Following page | **Done** — `tvyq`, wider than reviewed (see below) |
| 5 | Fresh upload leaves the panel saying "No image" | Open |
| 6 | `listing_image_mode` unvalidated | Open |
| 7–10, 12 | Nits | Open |
| 11 | `ArticleOut.resolve_images` returns pending uploads | **Done** — `99d24cf2` |
| — | Design: article images onto the articles router | **Done** — `99d24cf2` |

Each finding is verified against the code before anything is changed. Finding 1
did not survive that — the bug was real but in a different file, with a
different cause and fix.

## Blockers

### 1. Users who opted out of broadcast email are silently re-subscribed — **Done** (`xzpr 33b4`)

The consent bug is real. The diagnosis in the original review was not.

**As reviewed:** `users/0018`'s RunPython leaves `article_email_frequency` at its
`"hourly"` default for users who had set `notification_frequency = "never"`, so
carry `never` across.

**Why that's wrong:** `notification_frequency` was never a global email
opt-out. The pre-change UI labels it *"Notifications — How often you receive
discussion notifications"*
(`origin/main:src/web-ui/src/app/profile/Settings.tsx:98-101`). `never` there
means "don't mail me about comments"; copying it into article cadence invents a
preference the user never expressed. The design line the review quotes
(`design.md:169`) is about the *broadcast* resolver, a different path.

**Where the opt-out actually lived:** `email_opt_in_competition_results` /
`email_opt_in_platform_updates` → migrated into
`FollowChannelPreference.email_enabled` by `follows/0002` (lines 76, 84), which
has been the live source of truth since the Phase-2 mirror was removed in
`89b9b66e`.

**The real defect:** this branch collapses that boolean into row existence, and
`follows/0004` swept on `email_enabled = False AND in_app_enabled = False`. But
`follows/0002` writes `in_app_enabled = True` unconditionally (lines 77, 85, 91),
so no legacy row can match — the sweep deletes nothing, and every historical
email opt-out survives as a `FollowedChannel`, i.e. a subscription. The rule was
documented as agreed in `design.md` decision 6, so the migration was faithful to
a design that was itself wrong.

**Fix:** sweep on `email_enabled` alone; `in_app_enabled` carries no user intent
for these rows, since the two checkboxes it was seeded alongside predate the
in-app bell entirely. `design.md`, `proposal.md`, the delta spec and `tasks.md`
updated to match. Cost: a user who wanted in-app-but-not-email on a channel is
unfollowed — unrepresentable after the column drop either way, and the quiet
side to err on.

**Left open:** task 3.2 claimed a regression test for the sweep; none exists and
none is writable without a migration-state harness (`django-test-migrations` or
equivalent), since `0005` drops `email_enabled` from the live model. Unticked
rather than quietly dropped. Task 16.2's acceptance criterion was inverted too —
it asked to confirm the deleted-row count is *small*, when under the corrected
rule a near-zero count is the signal the sweep is missing its cohort.

### 2. The digest cron is broken by the task rename, and the stated safety net doesn't exist — Open

`src/django-backend/api/tasks/notifications.py:26`,
`src/django-backend/services/notifications/django_impl/handler.py:265`

`send_hourly_notifications` / `send_daily_notifications` were deleted and
replaced with five new task functions. Nothing in the repo enqueues them
(`grep -rn enqueue src/django-backend` finds no digest callers), so the schedule
lives in the external cloud scheduler — which still names the old functions.
After deploy every digest email stops, silently.

Worse, `send_batch_notifications`'s new docstring claims it is "retained so the
existing tick (`api.tasks.notifications.send_*_notifications`) keeps working
without a celery-config flip" — those functions no longer exist, and nothing
calls `send_batch_notifications` outside a test.

Task 7.5 in `openspec/changes/simplify-follow-and-cadence/tasks.md` is ticked but
only produced a comment block; there is no schedule config anywhere, and the new
`send_article_digest_weekly` has never been scheduled at all.

## Important

### 3. `auto` mode can adopt an upload that never completed — **Done**

`src/django-backend/services/articles/django_impl/handler.py:269`

`article.images.order_by("created_at").first()` has no `upload_status` filter.
`get_upload_url` creates the `ProjectImage` row as `PENDING` before the S3 PUT,
and nothing deletes it if the PUT fails. `_apply_listing_image` runs on *every*
PATCH, so: the author's first inline upload fails → they insert a second one
that works → save → the listing image is the dead row, and `listing_image_url`
(built from `storage_key`, not upload state) points at an object that doesn't
exist. Every listing card for that article then shows a broken image.

Filter on `upload_status=UploadStatus.UPLOADED`.

**Resolution.** Confirmed, and wider than written: `_resolve_listing_image`
(`handler.py:375`) had the same hole, so `PATCH {"listing_image_id": <pending>}`
was accepted too. Rather than filtering at each site, the rule got one home —
`ProjectImageQuerySet.uploaded()` plus `ProjectImage.is_uploaded` for callers
holding a prefetch (`apps/projects/models.py:216,286`). All ten read sites now
go through it; no `upload_status=UPLOADED` literal remains outside the model.
`chosen` on an incomplete upload raises the new `ListingImageNotUploadedError`
→ 422, kept distinct from the wrong-project case because the client legitimately
holds that id — `upload-url` returned it.

Orphaned `PENDING` rows are now inert but still accumulate; logged as
`FOLLOW_UPS.md` item 5.

### 4. N+1 on the Following page — **Done**

`src/django-backend/services/follows/django_impl/query.py:32`

`_to_follow_with_preferences` now runs `Channel.objects.filter(project=follow.project)`
per follow, inside the loop in `list_follows_for_user`. The old code got all of
it from `prefetch_related("preferences__channel")`. A user following 20 projects
goes from 3 queries to 23. Prefetch `project__channels` on the outer queryset
instead.

**Resolution.** Confirmed, and it was three queries per follow, not one. The
channel query is the regression this change introduced; `_hero_image_url` was
already unprefetched on `main`, so `resolve_image_by_purpose`'s
`project.images.all()` and `variant_url`'s `image.variants.all()` each fired per
follow too. Measured, before → after:

| follows | before | after |
|---|---|---|
| 1 | 5 | 5 |
| 4 | 14 | 5 |
| 20 | 62 | 5 |

Flat at 5 = follows, `followed_channels`, `project__channels`,
`project__images`, variants.

The image prefetch also closes a correctness hole. `resolve_image_by_purpose`
does no filtering and trusts what the prefetch handed it — stated at
`services/review/django_impl/query.py:90,122` — and this was the one caller that
never narrowed it. So the hero fallback chain (role → main → `images[0]`) could
land on an article upload or a `PENDING` row, i.e. finding 3's failure mode in a
sixth place. `Prefetch("project__images", queryset=project_gallery_images())`
handles ordering, `.uploaded()`, `article__isnull=True` and the variants in one.

Both entry points now share `_follow_queryset`, so `get_follow_preferences`
can't drift from the list path. Tests: a scaling assertion (query count for four
follows equals the count for one), plus hero resolution ignoring article uploads
and incomplete ones.

### 5. Picking a freshly-uploaded image in the wizard leaves the panel saying "No image" — Open

`src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts:310`

`chooseListingImage` only updates `form`; `article.images` is not refetched. The
`listingImage` selector looks the id up in `article.images` (miss) then falls
back to `article.listing_image` only when
`form.listing_image_id === article.listing_image_id` (also a miss for a brand-new
upload) → `null`. So after "Upload new" → "Use it", `ListingSettingsPanel`
renders the "No image" placeholder and an imageless card preview next to the
label "Your choice.", until a save round-trips.

Images picked from the body (already in `article.images`) are fine, which is why
the e2e — which picks index 1 of two body images — doesn't catch it. Push the
confirmed image into `article.images` via the already-exposed `setArticle`.

### 6. `listing_image_mode` is an unvalidated string all the way to the column — Open

`src/django-backend/api/schemas/article.py:49`

Declared `str | None`, passed straight through `_resolve_mode` to
`article.listing_image_mode` with no membership check (Django doesn't enforce
`choices` on save). `PATCH {"listing_image_mode": "nonsense"}` returns 200 and
persists it; subsequent reads hand the frontend a mode that isn't a key of
`MODE_LABEL`. Make it a `Literal["auto", "chosen", "none"]` so Ninja rejects it
with a 422.

## Minor / nits

7. **`ListingImageDialog` doesn't honour its own "uncroppable" contract.** The
   `frame` step renders the cropper only when `selected.width && selected.height`,
   but "Use it" stays live and calls `defaultCrop({width: selected.width!, …})`.
   With null dimensions — which `lib/uploadProjectImage.ts::readImageDimensions`
   explicitly allows — that yields a NaN rect, `JSON.stringify` turns it into
   nulls, and the PATCH 422s with "Failed to save article". Disable the button,
   or don't advance to `frame` for a dimensionless image.

8. **`generateMetadata` builds the page description from raw markdown** —
   `src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/page.tsx:22,26`.
   `article.body.slice(0, 160)` will emit `![](https://…)` and `##` into
   `<meta description>` and the OG card. `summary_display` is right there and is
   exactly this, cleaned.

9. **Misleading comment / unreachable branch.** `page.tsx:42` says "the
   client-side path in `ArticleRenderContent` rehydrates drafts for the author";
   `ArticleRenderContent` only marks notifications read, it never refetches.
   Drafts also have `slug = None` until publish, so there is no URL to reach one
   by — the `isDraft` badge in `ArticleRenderContent` is dead code.

10. **Column churn in the migrations.** `projects/0044` adds
    `ProjectImage.source` and `projects/0045` removes it again, both in this
    change — an add-then-drop of an indexed column on a production table for no
    net effect. Worth squashing before deploy.

11. **`ArticleOut.resolve_images` returns pending/failed uploads.**
    `api/schemas/article.py:132` returns every linked row regardless of
    `upload_status`. The wizard happens to filter them out via
    `width && height`, so this is latent rather than broken today.

12. **Article uploads have no cap.** `api/routers/my_projects.py:261` exempts
    them from `MAX_IMAGES_PER_PROJECT` without substituting a per-article
    ceiling. Intentional per the design, but any `full_edit` contributor can now
    upload unbounded images by creating one draft article.

## Verdict

Address the two blockers before this ships — the opt-out reset is a consent
problem you can't undo after the first send, and the scheduler rename will take
digests down silently. 3–6 are worth fixing in this change; the rest can follow.

Blocker 1 is done, though the fix landed in `follows/0004`, not where the review
pointed. Blocker 2 still stands. Findings 3 and 4 are done, both wider than
written — in each case the rule the review wanted enforced at one call site had
to be given a single home instead. Its fix is partly outside this repo: no
scheduler config exists here (no `infra/prod`, no cron files), so the task names
have to be changed wherever the schedule actually lives.

## Design — move article image upload into the articles router — **Done** (`99d24cf2`)

Raised by the author during review:

> Should we have a separate API for uploading of images to articles rather than
> shoe horning into projects?

Yes. Article uploads should live on the articles router, not in the my-projects
image endpoints.

### Where it is today

Articles are addressed under one prefix and their images under another, keyed by
a different identifier:

```
GET PATCH DELETE  /api/projects/{slug}/articles/{article_id}
POST              /api/my/projects/{project_id}/images/upload-url
                  ↳ body: {source: "article", source_id: "<article_id>", …}
POST              /api/my/projects/{project_id}/images/{image_id}/complete
DELETE            /api/my/projects/{project_id}/images/{image_id}
```

An article image round-trip therefore crosses `/api/projects/{slug}/…` →
`/api/my/projects/{id}/…` and back. That leaks into the frontend:
`ArticleAuthoringPage` hands `useArticleDraft` the slug (`project.slug ?? project.id`)
and `ArticleEditor` the UUID (`project.id`), because the two APIs address the
same project differently.

### Why it's worth moving

The project endpoint is accumulating branches for a concern it doesn't own.
`get_upload_url` validates a `source` enum, resolves an `Article`, and skips the
gallery cap; `complete_upload` skips cover-image promotion; `delete_image` skips
article rows when promoting a replacement; and `ProjectResponse.resolve_images`
filters them out again as "belt and braces" (`api/schemas/project.py:117`).
That is five places that have to agree on "article images are not project
images" — and finding 3 above is exactly what happens when one of them forgets.

### Shape

```
POST   /api/projects/{slug}/articles/{article_id}/images/upload-url
POST   /api/projects/{slug}/articles/{article_id}/images/{image_id}/complete
DELETE /api/projects/{slug}/articles/{article_id}/images/{image_id}
```

- The article is in the path, so `source` / `source_id` disappear from
  `PresignedUploadRequest` along with the `ImageSource` enum
  (`api/schemas/project.py:14`) — one fewer request-shaped thing that can
  disagree with storage.
- Ownership uses the helpers the articles router already has —
  `require_full_edit` + `_get_article_in_project` — instead of the ad-hoc
  `Article.objects.filter(pk=payload.source_id, project=project).first()` at
  `api/routers/my_projects.py:249`, which is also a raw ORM query in a router.
- The missing per-article cap (finding 12) becomes a natural thing to add,
  because there is somewhere obvious to put it.
- Presign, storage key, `generate_image_variants` and the `ProjectImage` row
  stay shared — this is a second door onto the same table, not a second model.
  The `article` FK on `ProjectImage` is the right shape and shouldn't change.

### If the full move isn't worth it now

Keep one set of endpoints, but give the "which gallery does this belong to" rule
a single home: a queryset/manager on `ProjectImage` (`gallery()` /
`for_article()`) that both the routers and the schemas go through, so the rule
lives in one place instead of five.
`services/project/django_impl/query.py::project_gallery_images()` is already
half of this — the my-projects router just doesn't use it.
