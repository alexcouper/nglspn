# Backend review — `d2463b33..7a20fb38`

Scope: `src/django-backend/**`. Line numbers are from the tree at `7a20fb38`.
Overlap with `review/05-crosscutting-review.md` (migrations, upload authz,
template injection, CI) is deliberately not repeated here.

Test suite at `7a20fb38`: 1111 passed.

---

## Architecture & maintainability

### 1. There is no `REPO.images`, so routers query `ProjectImage` directly

`api/routers/articles.py:292`, `api/routers/my_projects.py:253,282,321`

`HANDLERS.images` was introduced for the write side, and the upload lifecycle
moved out of `my_projects.py` into it — good. But no query counterpart was
added, so both routers still reach for the ORM to fetch the row they are about
to hand to the handler. The knowledge of *what a valid target row looks like* is
consequently spread across four `get_object_or_404` call sites, each with its
own filter set:

- `articles.py:292` — `article=article`, plus a caller-supplied
  `upload_status=PENDING`
- `my_projects.py:253` — `project=`, `article__isnull=True`, `upload_status=PENDING`
- `my_projects.py:282` — `ProjectImage.objects.uploaded()`, `article__isnull=True`
- `my_projects.py:321` — `project=`, `article__isnull=True`, no status filter

`article__isnull=True` is the rule "a project endpoint must not touch an article
image", and it is written out three times by hand. The next endpoint that forgets
it is an IDOR-adjacent bug with nothing to catch it.

The guard that was written instead gives false confidence:
`api/routers/test_articles.py:902-912` asserts that `Article.objects`,
`Channel.objects` and `FollowedChannel.objects` do not appear in
`api/routers/articles.py` — but not `ProjectImage.objects`, which is exactly the
ORM access the file does perform.

Direction: `REPO.images.get_for_article(article, image_id, ...)` /
`get_gallery_image(project, image_id, ...)`, and extend the string list in the
guard test to `ProjectImage`.

### 2. "Follow a project and enrol every channel" is implemented three times

`services/follows/django_impl/handler.py:21-31`,
`apps/follows/services.py:36-45`, `apps/follows/services.py:83-89`

All three do `Follow.get_or_create` then loop `FollowedChannel.get_or_create`
over a channel set. `apps/follows/services.py` also imports *upwards* into the
service layer (`from services.users.django_impl.query import
BROADCAST_CHANNEL_BY_EMAIL_TYPE`, `:60-62`) and into another app's signals
module (`from apps.projects.signals import DEFAULT_CHANNEL_NAME`, `:59`), which
is the opposite of the stated `routers -> services -> models` direction.

The docstring at `apps/follows/services.py:1-7` justifies the split ("signals
live here, the router-facing layer lives under `services/follows/`") but the
enrolment rule is not a signal concern — it is the same business rule the
handler owns. The maintenance cost is already visible in finding 10 below: the
branch made "zero followed channels ⇒ unfollowed" a rule in one of the three
copies and not the others.

Direction: `apps/follows/services.py` should call
`HANDLERS.follows.follow(user_id, project)` rather than re-implement it, leaving
only the signal wiring and the house-project anointing in the app module.

### 3. The 16:9 listing-card rule lives in six files across two languages

`services/articles/crop.py:19` (`CARD_RATIO = 16 / 9`),
`src/web-ui/src/app/projects/[slug]/articles/ListingImageDialog.tsx:15`
(`const CARD_RATIO = 16 / 9`), plus hard-coded `aspect-[16/9]` in
`ListingImageDialog.tsx:275,293`, `ListingSettingsPanel.tsx:84`,
`ArticlesList.tsx:66-69`.

`crop.py`'s module docstring states the invariant ("there is exactly one crop per
article and it is always 16:9, because the lead card and the grid card render
from the same rectangle") and `validate_crop` enforces it server-side — but
changing the card shape means editing a Python constant, a TypeScript constant,
and four Tailwind literals, and getting any one wrong produces a 422 the author
cannot act on. The `ratio` field is carried in the payload precisely so the
client need not know the source dimensions; it does not remove the need for the
client to know the target ratio.

Direction: at minimum, expose `CARD_RATIO` on the API (it is already a field on
every crop) so the frontend has one source; better, derive the Tailwind classes
from a single exported constant.

### 4. `patch_article` uses two different "field omitted" conventions in one call

`api/routers/articles.py:198-210`, `services/articles/handler_interface.py:14-24`

Within a single `update_article` invocation:

- `title`, `body`, `summary`, `listing_image_mode`, `channel_id`,
  `published_at` use `None` to mean "omitted" — so `{"title": null}` is silently
  a no-op and `published_at` can never be cleared.
- `listing_image_id` and `listing_crop` use a hand-rolled `UNSET` sentinel read
  out of `payload.dict(exclude_unset=True)` — so `{"listing_image_id": null}`
  clears.

Both conventions are documented (`api/schemas/article.py:38-53`), which is why
this is a maintenance note rather than a bug, but a reader has to check the
signature per-field to know what `null` does. Pydantic already knows which keys
arrived (`model_fields_set` / `exclude_unset`); the router computes `provided`
and then throws it away for six of the eight fields.

Direction: pass `provided` through for every field and drop `UnsetType`, or
accept `None` as "clear" uniformly and use a separate `PATCH`-vs-`PUT` split.

### 5. `_apply_listing_image` is the branch's densest piece of logic and has no
### single statement of its rules

`services/articles/django_impl/handler.py:243-351`

Five collaborating private methods, with the mode-resolution rule ("touching the
image or the crop implicitly commits `chosen`") stated only in
`_resolve_mode`'s docstring, and the crop-invalidation rule ("an image that
changed takes its framing with it") only in `_chosen_crop`'s. It runs on *every*
`PATCH`, including a title-only save, and in `auto` mode issues an extra query
per save (`:270`).

It is well commented and well tested — the cost is that the rules are only
readable by executing the call graph in your head. A table of
`(mode_in, image_in, crop_in) -> (mode_out, image_out, crop_out)` in the module
docstring would make the next change to it reviewable.

### 6. The digest cadence vocabulary is written in four places

`apps/users/models.py:11-24` (`DiscussionEmailFrequency` /
`ArticleEmailFrequency`), `apps/notifications/models.py:9-19`
(`NotificationCadence`, the union),
`apps/notifications/management/commands/enqueue_digest.py:24-30`
(`TASK_BY_KIND_AND_CADENCE`), `api/tasks/notifications.py:32-64` (one task
symbol per pair) — plus the CronJob arguments in the infra repo and the
free-text schedule comment at `api/tasks/notifications.py:26-31`.

`enqueue_digest` is a genuine improvement over the hand-written `INSERT`s it
replaces. But adding a cadence is now a five-site edit across two repos, and the
schedule comment restating deployed wall-clock times has nothing keeping it
honest.

Direction: derive `TASK_BY_KIND_AND_CADENCE`'s keys from the two `TextChoices`
and generate the task functions, or collapse to one parameterised task
(`send_digest(kind, cadence)`) — `django_tasks` supports arguments; the whole
per-pair symbol set exists only because the old CronJobs named symbols.

### 7. `projects/0044` adds a column that `projects/0045` removes

`apps/projects/migrations/0044_projectimage_source.py`,
`apps/projects/migrations/0045_remove_projectimage_source_projectimage_article.py`

`source` (a `project`/`article` enum with `db_index=True`) is added and then
dropped in the same branch, replaced by the `article` FK. Both ship together so
there is no correctness problem, but on a large `project_images` table it is two
extra DDL statements and an index build for nothing. Squash before merge.

### 8. `DjangoImageHandler` mixes request-path and worker-path concerns

`services/images/django_impl/handler.py:45-289`

One class holds row reservation and presigning (runs in the HTTP request,
touches S3 metadata only) and Pillow decode/resize/encode (runs in the worker,
holds the whole image in memory). They share nothing but the model. The split is
already visible in the file's own section comments.

Not urgent; worth remembering the next time the variant pipeline changes, because
the request-path half is what the API contract depends on.

---

## Latent bugs

### Blocker

None.

### Important

#### 9. The article digest and the notification bell prefetch `project.images` unfiltered, defeating `project_gallery_images()`

`services/notifications/django_impl/handler.py:328`, `:377`;
`services/email/django_impl/handler.py:102-110`;
`services/project/django_impl/query.py:37-48`, `:84-105`

`project_gallery_images()` exists specifically so that article uploads and
never-completed `PENDING` rows cannot reach an image pick — its docstring says
"use this for every `Prefetch("images", ...)` on a project-facing query". Both
new article paths use a bare string prefetch instead:

```python
.prefetch_related(
    "article__listing_image__variants",
    "article__project__images__variants",   # unfiltered
)
```

`_build_article_group` (`:119`) and `_digest_article_image_url` (`:109`) then
call `REPO.project.get_project_icon_url(project)`, which is
`resolve_image_by_purpose(project, "icon")` → `list(project.images.all())` →
falls back to `images[0]` when the project has neither an `is_icon` nor an
`is_main` row. With the unfiltered prefetch that first row can be an article
figure or a `PENDING` upload.

Failure: project P has no cover (created as a tip-off, or its only gallery
upload PUT failed and left a `PENDING` row at `display_order=0`). A follower
publishes an article on P. The follower's notification bell and their hourly
article digest both render `<img src>` pointing at the `PENDING` row's
`storage_key` — an object that is not in S3 — so the icon is a broken image in
the email and in the dropdown. Where the first row is instead another article's
figure, the "project icon" silently becomes an inline body image from an
unrelated article.

The same unfiltered prefetch is on the discussion path at `:363-365`; that line
predates the branch, but the fix is the same `Prefetch("images",
queryset=project_gallery_images())` in all three places.

#### 10. The "a Follow with no channels is deleted" rule is enforced in exactly one of the three places that can empty a Follow

`services/follows/django_impl/handler.py:64-75`, `:17-31`;
`api/routers/channels.py:120-144`

`unfollow_channel` deletes the `Follow` when it removes the last
`FollowedChannel`, on the stated grounds that "a follow that notifies about
nothing is not a state we keep". Two other paths reach that state and do not
clean up:

*Route A — channel deletion (no concurrency needed).* Project P has channels A
and B. User U follows P but has unfollowed B, so U has one `FollowedChannel`
(A). The owner reassigns A's articles to B and deletes channel A
(`DELETE /api/projects/{slug}/channels/{channel_id}` — permitted, `article_count`
is 0 and a sibling remains). `FollowedChannel.channel` is `CASCADE`, so U's last
row disappears. U's `Follow` survives with zero children.

*Route B — concurrent unfollow.* U follows channels A and B. Two `DELETE`
requests (two tabs, or a double-click on a list of checkboxes) run concurrently.
Under READ COMMITTED, T1 deletes A then `FollowedChannel.objects.filter(
follow=follow).exists()` still sees B (T2 uncommitted); T2 deletes B and still
sees A. Neither deletes the `Follow`. The `transaction.atomic()` at `:69` does
not help — there is no lock on the `Follow` row.

Either way `REPO.follows.is_followed` (`query.py:69-72`) returns `True`, the UI
shows the project as followed, and the user receives nothing from it, forever.

Recovery is trapped: `follow()` (`:21-31`) enrols channels **only** when
`get_or_create` reports `created=True`, so pressing "Follow" again is a no-op.
The user must unfollow and re-follow, or tick a channel individually — neither
is discoverable from "I am already following this".

`apps/follows/migrations/0004_sweep_both_off_rows.py:33-38` explicitly reasons
that an emptied `Follow` is "a legacy-only state". It is not; the branch creates
two ways to produce it in normal use.

Fix: `select_for_update()` on the `Follow` inside `unfollow_channel`, a
`post_delete` on `Channel` (or a check in `delete_channel`) that drops emptied
`Follow` rows, and — cheapest and most robust — make `follow()` enrol missing
channels unconditionally rather than only on create.

#### 11. Deleting an article orphans every S3 object it owned

`services/articles/django_impl/handler.py:169-172`,
`services/images/django_impl/handler.py:103-123`

```python
def delete_article(self, article_id: UUID) -> None:
    deleted, _ = Article.objects.filter(pk=article_id).delete()
```

`ProjectImage.article` is `CASCADE` (`apps/projects/models.py:238-241`), so the
image rows and their `ImageVariant` rows go with the article. Storage cleanup
lives only in `HANDLERS.images.delete_image`, which this path never calls — and
a queryset `.delete()` would bypass a model `delete()` override anyway. Nothing
else deletes from storage: `grep delete_object` returns two call sites, both in
`images/django_impl/handler.py`.

Failure: author creates an article, uploads 8 inline figures (each generating up
to 3 WebP variants), then deletes the draft. 8 originals + up to 24 variants stay
in the bucket permanently, with no row that references them — they cannot even be
found by a future sweep, because the `storage_key`s are gone. At 10 MB per
original this is unbounded per user, and unlike `FOLLOW_UPS.md` item 5 (abandoned
`PENDING` rows) there is no row left to reconcile against.

Fix: iterate `article.images.all()` through `HANDLERS.images.delete_image` before
deleting the article, or record the keys in a `pending_deletions` table for a
worker to drain.

#### 12. Article publish fans out notifications synchronously in the HTTP request

`services/articles/django_impl/handler.py:160-165`, contrast
`services/discussions/django_impl/handler.py:45`

Discussions enqueue: `create_discussion_notifications.enqueue(str(discussion.id))`.
Articles call the handler inline:

```python
if not _is_backdated(effective_published_at):
    from services import HANDLERS
    HANDLERS.notifications.create_notifications_for_article(article.id)
```

`create_notifications_for_article` iterates every `FollowedChannel` on the
article's channel and does a `get_or_create` per recipient
(`services/notifications/django_impl/handler.py:216-228`) — two round trips each.

Failure: every active non-system user auto-follows the house project
(`apps/follows/services.py:21-45`, and `anoint_house_project` backfills the rest),
so publishing a house-channel article — the "ranking day" case the new
`house_channel_article_enqueued` logging at `:232-245` is built for — issues
~2N queries inside `POST /articles/{id}/publish`. At a few thousand users that is
a request-timeout, and because the fan-out is outside the `transaction.atomic()`
block at `:152`, a timeout leaves the article published with a partial recipient
set and no retry. There is a task runner, and `api/tasks/notifications.py`
already has the identical shape for discussions.

Fix: `create_article_notifications.enqueue(str(article.id))`, mirroring
discussions. The `_is_backdated` gate stays in `publish`.

#### 13. `users/0018` re-subscribes users who set "Never" and are not covered by the follows sweep

`apps/users/migrations/0018_user_article_email_frequency_and_more.py:5-9`,
`apps/follows/migrations/0004_sweep_both_off_rows.py:11-38`

`review/05-crosscutting-review.md` §2.4 records the `article_email_frequency`
default as a deliberate decision, on the reasoning that "the real opt-out lived
in `FollowedChannel.email_enabled`, handled by `follows/0004`". That reasoning
holds for the broadcast channels; it has a hole for ordinary project follows.

Before: `create_notifications_for_article` snapshotted
`user.notification_frequency` onto the row, and `_send_article_batch` selected
`email_cadence=cadence` for `hourly`/`daily` only. A user with
`notification_frequency = "never"` received **no** article email, whatever their
`FollowedChannel.email_enabled` said.

After: `follows/0004` deletes only rows with `email_enabled=False`. A user who
followed project P's channel with `email_enabled=True` *and* had
`notification_frequency = "never"` keeps the row, and `users/0018` gives them
`article_email_frequency = "hourly"`.

Failure: that user starts receiving an hourly article digest they had explicitly
switched off, and neither migration touched the state that recorded the
preference. Concretely reproducible: `UserFactory(notification_frequency="never")`
+ `make_followed_channel(user, project, channel)` on a non-house project → after
migrating, `send_article_digest("hourly")` mails them.

Fix, if the decision is to be honoured: add
`User.objects.filter(notification_frequency="never").update(
article_email_frequency="never")` to the `RunPython` in `0018`.

#### 14. `PATCH` and `POST /publish` return `ArticleOut` off a queryset that does not prefetch the article's images

`services/articles/django_impl/handler.py:353-361`, contrast
`services/articles/django_impl/query.py:24,39`;
`api/schemas/article.py:149-159`, `api/schemas/project.py:54-56`

`REPO.articles.get_by_id` / `get_by_project_and_slug` both prefetch
`"images__variants"` "because `images` is the listing-image wizard's selection
list on `ArticleOut`". The handler's own `_get_article` — whose return value is
what `patch_article` and `publish_article` serialise — prefetches only
`listing_image__variants`.

Failure: an article with 12 uploaded figures. Every `PATCH` (the editor's *Save
draft*, and the tab switch to *Listing settings*) issues 1 query for
`obj.images.all()` plus 12 for `ProjectImageResponse.resolve_variants` —
13 avoidable queries per save, growing linearly toward the 30-image cap. `create_article`
(`api/routers/articles.py:81-90`) is worse: it serialises a bare `Article(...)`
instance, so `project`, `author` and `images` are each a fresh query.

Fix: `_get_article` should reuse the query service's prefetch set, or
`patch_article`/`publish_article` should re-read through `REPO.articles.get_by_id`
before returning.

### Minor

#### 15. The notification bell shows raw markdown for articles and ignores the authored summary

`services/notifications/django_impl/handler.py:31,47-51,123`;
contrast `services/email/django_impl/handler.py:120-122` and
`api/schemas/article.py:130-131,187-188`

Every other surface flattens the body through
`services.articles.summary.derive_summary` and prefers `article.summary` when
set. `_build_article_group` does neither:

```python
latest_body_excerpt=_body_excerpt(article.body),   # str.strip() + text[:240]
```

`src/web-ui/src/components/NotificationGroupItem.tsx:49` renders that as plain
text.

Failure: an article whose body opens `# Why we rewrote the indexer\n\n![diagram](https://…/x.png)\n\nWe…`
appears in the bell as `# Why we rewrote the indexer ![diagram](https://…` — the
first 240 characters of markdown, with the author's `summary` (which exists
precisely for this) unused. `summary.py`'s docstring says it "lives only here" so
that no second implementation drifts; this is the second implementation.

Fix: `article.summary or derive_summary(article.body, limit=_BODY_EXCERPT_MAX)`.

#### 16. Deleting a `ProjectImage` leaves articles in a state the write path rejects

`apps/articles/models.py:59-64` (`listing_image` → `SET_NULL`),
`services/articles/django_impl/handler.py:336-345`,
`services/images/django_impl/handler.py:103-123`

`_validated_crop` raises `InvalidCropError(NO_LISTING_IMAGE)` — "cannot set a
crop on an article with no listing image" — so the API refuses to *create* a
crop-without-image. Deletion produces one anyway: `SET_NULL` blanks
`listing_image` while `listing_crop` and `listing_image_mode="chosen"` are left
as they were.

Failure: author sets a listing image on article A and frames it, then deletes
that image from the project gallery. A now serialises `listing_image_url: null`
with a populated `listing_crop`, and because the mode is still `chosen`, no
later save re-derives an image from A's own uploads — the card is imageless
until someone opens the dialog again. Low impact (a blank card, not a wrong
one), but it is a state the invariant says cannot exist, which is the kind of
thing that trips the next reader of `crop.py`.

Fix: null `listing_crop` and reset the mode to `auto` when the referenced image
goes away — a `post_delete` on `ProjectImage`, or handle it in
`HANDLERS.images.delete_image` alongside the cover-promotion it already does.

#### 17. `get_article_by_slug` is the only endpoint in the router that does not accept a project id

`api/routers/articles.py:117-131`, contrast
`services/project/django_impl/query.py:163-175`

`resolve_visible_project_or_404(slug, user)` goes through `get_by_identifier`,
which accepts a UUID *or* a slug — every other endpoint in `articles.py` and
`channels.py` therefore works with either. Line 126 then calls
`REPO.articles.get_by_project_and_slug(slug, article_slug)`, which filters
`project__slug=<the raw path segment>`.

Failure: `GET /api/projects/<project-uuid>/articles/by-slug/my-article` resolves
the project successfully at `:123` and then 404s at `:128`, for an article that
exists and is published. The frontend uses slugs so this is not live today; it is
a trap for anyone who assumes the router's identifier convention is uniform.

Fix: `REPO.articles.get_by_project_and_slug(project.id, article_slug)` with the
query keyed on `project_id`. The `article.project_id != project.id` check at
`:127` already covers the ownership half.

#### 18. `publish` is not guarded against re-publish and moves `published_at`

`services/articles/django_impl/handler.py:139-167`

Nothing checks `article.state`. A second `POST .../publish` with no
`published_at` in the body sets `published_at = timezone.now()` again and re-runs
the fan-out.

Failure: an author double-clicks *Publish*, or retries after a slow response
(likely, given finding 12). The article's publish time silently shifts, which
reorders it in `for_project`'s `published_at DESC` listing. `get_or_create` in
the fan-out prevents duplicate `Notification` rows for existing followers, but
anyone who followed the channel between the two calls is notified about an
article that was already live. The slug is correctly left alone (`:157`).

Fix: return early when `article.state == PUBLISHED` and `published_at` was not
explicitly supplied.

---

## Test coverage gaps

New logic only; declarative renames and schema changes are excluded.

1. **`services/images/django_impl/handler.py:103-123` (`delete_image`) has no
   test for cover promotion after deletion.** `test_handler.py` in
   `services/images/django_impl/` is the old variant-generation file, renamed
   only. The article-image tests (`api/routers/test_article_images.py`) cover
   `test_removes_the_row` and `test_leaves_a_project_gallery_image_alone`, but
   nothing exercises "deleting the cover promotes the next gallery image", nor
   that the promotion candidate excludes article uploads — which is the branch's
   own new `_gallery_queryset` rule (`:182-185`).

2. **No test for `create_notifications_for_article` against a project with more
   than a handful of followers**, and none asserting where the fan-out runs
   (inline vs enqueued). `services/notifications/django_impl/test_article_fanout.py`
   covers correctness of the recipient set thoroughly; nothing pins the
   execution model, so finding 12 could be fixed and silently regressed.

3. **`send_article_digest` is not tested against an unfiltered
   `project.images` prefetch.** `services/email/django_impl/test_handler.py`
   covers `build_article_digest_entries`, but every fixture gives the article a
   `listing_image`, so the `REPO.project.get_project_icon_url` fallback branch
   (`handler.py:109`) — the one that reaches finding 9 — is never entered.

4. **`unfollow_channel` has no test for the emptied-`Follow` state arriving from
   anywhere other than `unfollow_channel` itself.** `test_handler.py` covers the
   last-channel deletion; nothing covers `delete_channel` cascading a user's last
   `FollowedChannel`, which is route A of finding 10 and needs no concurrency.

5. **`delete_article` has no test asserting storage cleanup.**
   `api/routers/test_articles.py` has `test_owner_can_delete`, which checks the
   row is gone. Finding 11 would be caught by asserting
   `storage_service.delete_object` was called for each of the article's images.

Well covered and needing nothing further: `services/articles/crop.py`
(`test_crop.py`, 11 cases including the overhang and ratio-contradiction edges),
`services/articles/summary.py` (`test_summary.py`), the listing-image mode state
machine (`test_articles.py::TestArticleListingImage*`, 12 cases covering
auto-adoption, explicit-null clearing, stale-crop invalidation and mode
stickiness), the article image caps and cross-article IDOR attempts
(`test_article_images.py`, 22 cases), and slug uniqueness
(`apps/articles/tests/test_slugs.py`).

---

## Checked and clean

- **Article endpoint authorisation.** Every one of the ten endpoints in
  `api/routers/articles.py` goes through `require_full_edit` or
  `resolve_visible_project_or_404`, and every id-addressed object is
  re-checked against the project in the URL: articles via
  `_get_article_in_project` (`:57-63`), images via `_get_article_image_or_404`
  (`:289-292`, `article=article`). Draft visibility (`_can_view_draft`, `:49-54`)
  admits the author plus `REPO.project.user_can_edit`, and returns 404 (not 403)
  on the anonymous slug path so draft existence is not leaked. No IDOR found.
- **`my_projects.py` image endpoints correctly exclude article uploads** —
  `article__isnull=True` on complete, roles and delete (`:253,282,321`), so an
  article figure cannot be promoted to a project cover or reordered into the
  gallery. `ProjectResponse.resolve_images` (`api/schemas/project.py:104-111`)
  filters again in Python as a backstop.
- **kennitala.** Not touched by the branch. `PublicUserProfile`
  (`api/schemas/user.py:53-58`) exposes id / first_name / last_name / info only,
  and it is the only user shape reachable from `ArticleOut.author`.
  `test_auth.py:650-672` still asserts absence on `/me` and register.
- **X-Forwarded-For.** No new reader. `project_showcase/middleware.py:22-35`
  counts back from the right by `NUM_TRUSTED_PROXIES`; unchanged by this branch.
- **`services/image/` → `services/images/` rename is complete.** No live
  reference to the old path or to `HANDLERS.image` remains; the only hits are in
  `openspec/changes/archive/2026-02-28-image-variant-pregeneration/` (an archived
  change, correctly frozen) and `review/01-features-articles.md`.
- **Slug generation under concurrency.** `apps/articles/slugs.py` (unchanged)
  retries on `IntegrityError` inside a nested `atomic()` savepoint and is backed
  by the partial unique constraint `articles_project_slug_uniq`
  (`apps/articles/models.py:108-113`). Calling it from inside `publish`'s outer
  `atomic()` block is safe — the savepoint absorbs the failed insert.
- **`follow()` under concurrent first-follow.** `get_or_create` against the
  `unique_together (user, project)` on `Follow` retries the `get` internally; no
  500.
- **Digest bulk update is atomic per recipient in effect.** `send_article_digest`
  (`:339-354`) sends, then `bulk_update`s the whole batch; a send failure logs
  and leaves `email_sent=False` for retry, and cannot half-mark a recipient's
  rows.
- **`ProjectImageQuerySet.uploaded()` reaches the related managers.** Assigning
  `objects = ProjectImageQuerySet.as_manager()` (`apps/projects/models.py:272`)
  makes it the `_default_manager`, so `project.images.uploaded()` and
  `article.images.uploaded()` both work; the `is_uploaded` property
  (`:282-288`) is the correct in-memory twin for prefetched relations and is used
  as such in `api/schemas/article.py:157`.
- **`_is_backdated` (`services/articles/django_impl/handler.py:46-50`) is applied
  to `effective_published_at`, not the raw payload**, so a publish with no
  explicit timestamp cannot accidentally be classed as backdated.
- **Migration graph.** `articles/0005` → `projects/0044`, `projects/0045` →
  `articles/0005` — no cycle, and `follows/0003→0004→0005` /
  `users/0018→0019` order the data move before the column drop in both cases.
- **Email templates.** `article_digest.mjml` / `.txt` interpolate with plain
  `{{ }}` under autoescape; `body_excerpt` is additionally flattened through
  `summary.py`'s `_HTML_TAG_RE`. (Also covered in `review/05` §3.5.)
- **Full backend suite passes at `7a20fb38`:** 1111 passed, 0 failed.
