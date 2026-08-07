# Follow-ups

Gaps found while reviewing.

Items 1–4 are frontend fixes on `/profile/following` and are resolved. Item 5's
code has landed but nothing schedules it yet. Items 6 to 16 are open. Items 8
to 11 come from the article-authoring review and were deferred deliberately
rather than fixed; **item 8 is live data loss and ships unfixed**, so it is not
in the "blocks nothing" category the rest are. Items 13 to 16 are spillover
from applying that review — found while fixing something adjacent, left alone
to keep those changes honest.

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

This does not make an empty `Follow` impossible, and it is not meant to.
Deleting a channel cascades `FollowedChannel` rows away, two concurrent
unfollows can each miss the other, and `follows/0004` left emptied rows behind
on purpose. Such a `Follow` notifies about nothing, but `is_followed` still
reports it as followed, so the project shows as "Following" with no channels
ticked and pressing Follow again writes nothing — the user re-ticks a channel in
the popover to recover. Accepted; see design decision 6 in
`openspec/changes/simplify-follow-and-cadence/design.md`.

## 4. Nested interactive elements in the row header — done

The row header put the project `<Link>` inside the expand `<button>`. The
chevron is now its own button with `aria-expanded` / `aria-controls`, and the
link sits outside it.

## 5. Nothing garbage-collects abandoned image uploads — code done, not scheduled

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

`HANDLERS.images.sweep_orphaned_objects()` now does this. `PENDING` rows older
than 24 hours are deleted — a presigned PUT expires after an hour, so nothing
older can still complete — and deleting the row fires the `pre_delete` receiver
that tombstones its `storage_key`, which the same sweep run then drains. The
object goes with the row instead of being left behind. `UPLOADED` rows of any
age and `FAILED` rows are untouched.

**Still open: nothing schedules it.** `manage.py enqueue_storage_sweep` exists,
but the CronJob belongs in the `naglasupan-hq` infra repo and has not been
written. Until it lands, the sweep never runs and the tombstone table only
grows — one row per deleted image. A `WARNING` fires when the oldest undrained
tombstone passes 24 hours, so the gap is visible rather than silent.

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

## 7. An author cannot see an article the way readers will

Raised as finding 9 of the branch's own `REVIEW.md` (since deleted; see
`b83f4e3f`), which was written up as a stale comment.
Checking it turned up the absence behind the comment, which is the part worth
keeping.

There is no preview — of a draft or of a published article. The editor has a
listing-card preview (`ArticleCardPreview`), which shows how the article looks
in a list, not how it reads. The only route to an unpublished article is
`/my-projects/[id]` → `MyProjectArticles.tsx:95` → `articles/edit/[articleId]`,
and the only route to a rendered article is the public
`/projects/[slug]/articles/[articleSlug]`, which drafts cannot reach.

**Why a draft cannot use the public route as it stands.** Three independent
reasons, and the identifier is only one of them:

- Slugs are assigned in `publish_article`
  (`services/articles/django_impl/handler.py:157`) and there is no unpublish
  path, so a draft has no slug to be addressed by.
- `serverFetch` sends no credentials (`src/web-ui/src/lib/api/server.ts:30-32`),
  so `get_article_by_slug` always sees an anonymous user and 404s on a draft
  (`api/routers/articles.py:129`).
- Auth is a bearer token in `localStorage` (`src/web-ui/src/lib/api/base.ts:116`).
  There is no cookie to forward, so *no* server component can authenticate. A
  draft page cannot be server-rendered for its author under any identifier
  scheme; it has to be a client fetch.

**The backend is already there.** `GET /api/projects/{slug}/articles/{article_id}`
is authenticated, and `_can_view_draft` (`api/routers/articles.py:49-54`) admits
the author plus anyone with project edit rights. Addressing a draft by UUID needs
no API change.

**Two shapes.**

- *A preview route* — `/projects/[slug]/articles/preview/[articleId]`,
  client-only, mirroring the `edit/[articleId]` convention. The public route
  keeps its server rendering, stays slug-only and 404s honestly. The URL changes
  at publish, so a link shared before publish dies — defensible for a draft.
- *UUIDs on the public route* — `[articleSlug]` may be a UUID. The server fetch
  still 404s for a draft, so the page can no longer call `notFound()`; it needs a
  client fallback that retries with the token and renders its own not-found
  state. That puts a round-trip and a loading state in front of every genuine
  404 on the public path to serve the authoring case. It does buy one URL shape
  that survives publishing.

A is the cheaper of the two and needs no backend work.

Either way the editor needs a button; there is none today, which is why this is
a feature rather than a fix.

**The `isDraft` badge stays.** `ArticleRenderContent.tsx:69-73` is unreachable
today, but it becomes correct the moment a preview exists, so deleting it would
only mean writing it again.

The comment that raised this is fixed (`swzk`). It read "the client-side path in
`ArticleRenderContent` rehydrates drafts for the author" — a description of this
missing feature written as though it were already built, which is the kind of
thing that stops the next reader from noticing the gap. It now records the three
constraints above instead, and points here.

## 8. Blanking a published article deletes it from the server

`src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts`

**This one loses data and is not fixed.** The review filed it as the
mid-upload race (I4) and missed the deterministic half; the summary it was
filed under only ever described the race.

The authoring hook registers a cleanup on unmount of `ArticleAuthoringPage`
that calls `api.articles.delete` when the draft looks untouched and the internal
`leaving` flag is false. At the time of review that was the sweep at
`useArticleDraft.ts:162–170` and the predicate `isUntouched` at `:43–54`;
finding 10's decomposition has since moved the predicate out to
`articleDraftState.ts` as `shouldDiscardDraft`, unchanged in behaviour. Go by
the symbol names, not the line numbers.

The predicate is four conjuncts — empty title, empty body, no
`listing_image_id`, `article.images.length === 0`. It reads neither
`article.state` nor whether the article arrived from the server with content.
It asks only "does this look empty right now", so an article the author has
just blanked is indistinguishable from one that was always empty.

**The consequence.** Open a **published**, image-less article, clear the title
and select-all-delete the body, navigate away — the published article is
deleted from the server and drops out of the public listing. No timing window;
it is deterministic. The same holds for a saved draft.

Nothing catches it on the way out. Exactly one `<Link>` on the page consults
the dirty check (`isDirty()`, now `hasUnsavedChanges`) — the breadcrumb, at
`ArticleAuthoringPage.tsx:154` at the time of review. The global nav
(`src/web-ui/src/components/Navigation.tsx`) and browser Back bypass it
entirely. And when the prompt does fire it says "Leave without saving?" — it
never mentions deletion. The `beforeunload` handler is the same.

**The upload race, same predicate.** `useImageUploadStatus.ts` calls
`sendUpload`, keeps `image.url` and throws the rest away; it never calls
`setArticle`, so `article.images` stays whatever the last server response said.
MDXEditor inserts the image node only after the upload handler resolves —
verified in `@mdxeditor/editor` for the toolbar, drop and paste paths alike —
so for the whole presign → S3 PUT → completion round trip the body markdown is
unchanged too. All four conjuncts hold. Insert an image as the *first* action in
an empty draft and leave before it finishes, and the draft is deleted. Narrow
precondition (typing a headline first is enough to protect you) but a wide
window: tens of seconds for a large photo on a domestic uplink. A variant bites
after the upload succeeds — remove the image markdown from the body and leave,
and the sweep fires against a stale `[]`, cascading the `ProjectImage` row
(`apps/projects/models.py:238`) and orphaning the S3 object.

**The fix, ~40 lines across three frontend files, no backend change.** Tighten
`shouldDiscardDraft` so it only ever discards a draft that *arrived* empty and
is still empty:

- bail unless `article.state === "draft"` — closes the published case;
- bail unless `arrivedEmpty`, recorded once in the load effect from the article
  the server returned — closes the blanked-draft case;
- bail while an upload is in flight, and bail if any inline upload has landed
  this session — closes the two upload cases.

The upload counters must be refs, not state: the unmount cleanup reads them
synchronously and cannot see state that has not committed. Wiring is
`ArticleAuthoringPage` → `ArticleEditor` → `useImageUploadStatus` as two
individually stable positional callbacks (`onUploadStart` / `onUploadSettled`)
— they land in the deps of the MDXEditor upload handler, so an options object
would churn the plugin's params on every keystroke.

Adopting the uploaded image into `article.images` at that point is a visible
behaviour change: the listing wizard would start offering inline uploads before
a save, which it does not today. Read `listing-image-dialog.test.tsx` for
assumptions about that list.

**What the fix still would not cover.** A killed tab. `beforeunload` cannot
await an in-flight upload and the cleanup never runs, so the draft survives as
an empty row — a leak, not a loss. The only backstop is server-side: a periodic
task deleting `state="draft"` articles with empty title/body/images older than
an hour. Worth doing in addition. Item 9's option (b) — never create the draft
eagerly — removes this entire class instead, which is the real end state.

Regression tests worth having: an in-flight upload is not swept; a settled
*failed* upload is (guards the counter against leaking); a published article the
author blanked is not; an article that had content when it loaded is not. Now
that the predicate is a pure function, only the first needs a React harness —
the rest belong in `articleDraftState`'s own test. Plus a Playwright case that
delays the presigned PUT, clicks the
breadcrumb mid-upload and asserts the article is still listed — note the PUT
goes to the S3 host, not the app origin, so `page.route` needs a glob over the
bucket URL.

## 9. Text typed immediately after `/new` is discarded

`src/web-ui/src/app/projects/[slug]/articles/useArticleDraft.ts`, the create
branch (`:95–150` at the time of review; finding 10's decomposition has since
split the load effect into `useArticleLoad.ts` and left the URL swap in
`useArticleDraft`)

Raised as I5. Related to item 8 — same hook, same draft lifecycle — but the two
fixes are independent and can land in either order.

`api.articles.create` resolves, the hook sets `leaving = true`, calls
`router.replace` to `/edit/<id>`, and then, without awaiting it, writes `form`,
`bodyRef` and `isLoading = false` in the same tick. So the page drops out of its
skeleton and renders the title input, the channel dropdown and the body editor
— on a page that is already navigating away.

`/new` and `/edit/[articleId]` are distinct route segments. When the RSC payload
lands, React unmounts the `/new` tree and mounts a fresh `ArticleAuthoringPage`,
which refetches the article as the server holds it: `title: ""`, `body: ""`.
Everything typed lived in the unmounted hook's `form` and `bodyRef` and is gone.
No prompt — `isDirty()` belongs to the dead instance, and a transition is not a
link click. The window is the RSC fetch plus a `getProjectOr404` server call:
imperceptible locally, seconds on a cold backend.

The eager create itself is sound. `ArticleEditor` and `ListingImageDialog` both
take a non-optional `articleId`, and `api.articles.getImageUploadUrl` is
addressed by article, so the id genuinely must exist before either surface is
usable. The bug is that the URL swap is a *route change*.

**Option (c), recommended — swap the URL without a route change.** Replace
`router.replace` with `window.history.replaceState(null, "",
'/projects/<ref>/articles/edit/<id>')`. Next 16 supports `pushState` /
`replaceState` and syncs `usePathname` / `useSearchParams` from them; this is
the documented escape hatch. `replaceState` replaces the `/new` entry, so Back
behaves as it does today. Delete `leaving = true` from this path — there is no
unmount to suppress, and leaving it set disables the sweep for the whole
session. One cosmetic follow-on: the breadcrumb label is derived from the
`articleId` prop, which stays undefined for the life of the mount, so it would
read "New article" forever; derive it from `draft.article` instead.

One mount then owns the draft from creation to departure, and `arrivedEmpty` in
item 8 becomes exactly "this session created this draft", which is what the
sweep always meant.

Risk worth a comment in the code: the URL says `/edit/<id>` while the mounted
segment is `/new`. Nothing reads route params on that page today —
`ArticleAuthoringPage` takes `project` and `articleId` as props from the server
component, not from `useParams` — but a future change adding `/edit`-only
behaviour to `edit/[articleId]/page.tsx` would silently not apply in a create
session.

**Option (a), the fallback if the history swap fights the router.** `return`
straight after the `replace` and let the `/edit` mount render. Three lines,
correct, nothing can be typed so nothing can be lost — but the author watches a
skeleton for the length of the RSC fetch, which is the interval that feels fast
today, and a stalled navigation leaves a skeleton with no error and no way out.

**Option (b), the end state.** Do not create the draft eagerly; create on first
upload. `ArticleEditor` and `ListingImageDialog` take
`ensureArticleId: () => Promise<string>`; `persistDraft` branches
create-vs-update; `article` is null for the first part of the page's life, so
"Couldn't open this article" must stop treating null as failure; `remove()`
no-ops; the listing tab's implicit save has to create. It buys the removal of
item 8's whole class — no empty draft ever exists, so nothing needs sweeping.
It does *not* fix this item on its own: the first upload still mints an id that
still has to reach the URL, so you need (c) anyway, just less often.

Rejected: passing the loaded article through to the `/edit` mount. What is lost
is not the fetched article, it is the typed text in the unmounted component's
state; carrying that across the route change is a worse version of (c).

## 10. Opening the listing tab writes unsaved edits to a live article

`src/web-ui/src/app/projects/[slug]/articles/ArticleAuthoringPage.tsx`,
`handleTabClick` (`:131` at the time of review)


Raised as I6. **Nothing was changed. Both fixes below are outstanding** — the
narrow one because it was explicitly held back, the proper one because it is a
feature.

`handleTabClick` awaits `draft.save()` before switching to the listing tab, and
`save()` sends the full payload — `title`, `body`, `channel_id`, `summary` and
the three listing fields — through `api.articles.update`. `patch_article`
(`api/routers/articles.py`) is the same endpoint for a draft and for a
published article and never consults `ArticleState`; `draft.isPublished` only
changes a button label. Type one character into a published article's body,
click the tab, and that character is live.

**The narrow fix needs no schema change and works against today's API.** The
tab needs a server round-trip for exactly three *derived* values, and none of
them requires the author's unsaved body to be persisted:

- the placeholder/fallback summary, which is `derive_summary` of the **saved**
  body (`api/schemas/article.py:130`);
- this article's uploaded images — inline uploads never reach draft state, which
  is item 8's root cause;
- `auto` resolved to an image (`_apply_listing_image` in
  `services/articles/django_impl/handler.py`, which resolves `auto` to the first
  uploaded article image), settled on *write*, not on read.

`ArticleUpdate` (`api/schemas/article.py:36`) is all-optional, `update_article`
skips `title` / `body` / `summary` when they arrive as `None`, and
`_apply_listing_image` runs unconditionally — so an empty `PATCH {}` returns all
three and persists nothing the author typed. The generated TS type has every
field optional, so `api.articles.update(ref, id, {})` compiles today. No
backend change, no OpenAPI regeneration, no migration.

That is roughly 40 lines: a `refreshListing()` in place of `draft.save()`,
adopting the server's `auto` resolution into the form *only* while the mode is
still `auto` (a wizard choice made since the last save must not be reverted),
and moving `title` and `channelName` into `ArticleCardPreview`'s `toListItem`
overrides so the card preview stops reading last-saved fields. Worth a backend
test pinning the contract the frontend would then depend on: an empty PATCH
resolves `auto` without touching the body — otherwise adding a required field to
`ArticleUpdate` breaks the listing tab silently.

Residual, if that is taken: `auto` re-resolution is still technically a write on
a published article whose author has inline-uploaded since the last save. It is
derived, idempotent with what any save would do, and avoidable by resolving
`auto` client-side as `images[0]` and using a plain `GET` — at the cost of
duplicating the rule. And the Save button still writes live with no
confirmation, which is honest for a button labelled Save.

**The proper fix — draft revisions — is what is deferred here.** "Editing a
published article is safe in general, including via Save." 1–2 weeks:

- **Schema.** Shadow columns on `Article` (`draft_title`, `draft_body`, …) or an
  `ArticleRevision` table. Shadow columns are the cheap half; a revision table is
  the honest one.
- **Publish semantics.** `publish()` is a one-way `DRAFT → PUBLISHED` transition
  today that assigns the slug and fires notifications. It becomes "promote the
  working revision", i.e. re-entrant — which forces `published_at` not to move on
  a re-publish and `create_notifications_for_article` not to re-fire. There is no
  already-notified guard today.
- **Images.** `ProjectImage.article` is per-article, not per-revision. An image
  in an unpublished revision is already stored, already counts against the image
  cap, and — because `_apply_listing_image` resolves `auto` from the article's
  uploaded images — can already become the live card's image. Either image rows
  get revision scoping or `auto` resolves against the live revision's body.
- **API.** PATCH writes the working revision, a new endpoint discards it,
  `ArticleOut` grows a working/live distinction. OpenAPI regen, type regen, and
  `_get_article`'s prefetch chain changes.
- **UI.** An "unpublished changes" banner, a discard action, a preview toggle
  between "what readers see" and "what you have written", and the read page must
  keep serving the live revision to everyone — including the author, who
  currently sees drafts via `_can_view_draft`.
- **Migration.** Backfill a working revision per published article, or create one
  lazily on first edit.

This is a product feature. It has nothing to do with a tab click writing to the
database, which is why the narrow fix stands on its own if the feature slips.

## 11. The article read page ships 333 Prism grammars

`src/web-ui/src/app/projects/[slug]/articles/[articleSlug]/ArticleRenderContent.tsx`

The component is `"use client"` and imports the default export of
`rehype-prism-plus`. That entry is a barrel: it registers `refractor` **and**
`refractor/all`, so the cost is 36 + 297 = **333 grammar registrations**, not
297. Because it is a client component, react-markdown + refractor also run twice
on a cold load — once for SSR, once for hydration.

**Measured**, from the Turbopack production build committed on this branch
(`BUILD_ID MRRsbxqEnbn36bmxI2pnj`, 6 Aug 18:09; no build was run for the
review):

| | Raw | gzip -9 |
|---|---:|---:|
| `static/chunks/8cf557b2c8ae44cd.js` (the grammar chunk) | 791,119 B | 272,367 B |
| Client JS for `projects/[slug]/articles/[articleSlug]` (10 chunks) | 1,017,818 B | ~340 kB |
| Client JS for `projects/[slug]` (9 chunks) | 249,978 B | ~75 kB |

Grammar tables are ~570 KB of that chunk's 776 KB body (73%), and the chunk is
78% of the read page's client JS. Reading an article is the heaviest thing this
app does in the browser — heavier than opening the editor, which is lazy.

The editor offers 11 real languages (`codeBlockLanguages` in
`ArticleEditor.tsx`), covered by 12 refractor grammars: 58,172 bytes of source
against 1,087,804.

**Rejected — `rehype-prism-plus/common` (one line).** Drops the `all` block but
`jsx` and `tsx` are not in refractor's common set, and `ignoreMissing: true`
makes that silent: the author picks TSX in the toolbar, the editor colours it,
the published page does not. Worse than the bug it fixes.

**Option (b), recommended for the cheap win.** Hand-register the subset:
`refractor/core` plus the 12 `refractor/lang/*` deep imports (both are declared
exports, not reaching inside the package), fed to `rehype-prism-plus/generator`
rather than the barrel. Registration order matters — refractor does not resolve
dependencies (`clike` → `javascript` → `typescript`/`jsx` → `tsx`; `markup` →
`markdown`). Drive the editor's dropdown off the same shared language map and
add a test asserting every offered language resolves, so adding "Go" to the
dropdown fails loudly instead of silently shipping unhighlighted code.

Projected result: the chunk lands around 250 KB raw / ~85 kB gz, roughly
**185 kB gzipped off every article page load**. Those are projections from a
measured ~0.52 minify ratio on this build, not from a build of the change —
re-measure before quoting them anywhere.

**Option (c), structurally right, larger.** Render the markdown in the server
component and pass the tree down as children. `ArticleRenderContent` cannot stop
being `"use client"` — it uses `useAuth`, `useNotifications` and an effect to
POST the read receipt — but the markdown render does not have to live inside it,
and this repo already renders react-markdown in server components
(`src/web-ui/src/app/about/why/page.tsx`, `about/prizes/page.tsx`,
`privacy/page.tsx`). That removes refractor, react-markdown, rehype-raw,
rehype-sanitize and remark-gfm from the client bundle entirely: ~340 kB gz down
to ~70 kB.

Its cost is real. Today the RSC payload carries `article.body` as a markdown
string and the chunk that renders it is immutably cached and shared across every
article. Option (c) swaps that for a serialised element tree per article —
typically 2–4x the markdown, worse for code-heavy articles where every token
becomes an element, and not shared. A reader who opens ten articles pays ten
inflated payloads instead of one cached chunk. Option (b) keeps the caching and
takes most of the win.

Ordering note: the smaller grammar set also shrinks the token-class allow-list
that the markdown-sanitisation work needs, so this lands first.

## 12. `src/web-ui` shadows the shared `build` target, warning on every make run

`scripts/app-common.mk:1` defines `build:` as `../../scripts/build.sh $(APP)`.
`src/web-ui/Makefile:35` defines `build:` again, as `./scripts/build.sh`. The
later definition wins, so every `make` invocation in `src/web-ui` prints:

```
Makefile:36: warning: overriding commands for target `build'
../../scripts/app-common.mk:2: warning: ignoring old commands for target `build'
```

Pre-existing and harmless — web-ui's own recipe is the one that runs, which is
presumably the intent. It matters slightly more now that CI runs more `make`
targets per job, because the warning precedes every one of them and reads like
a failure in the log.

Fix is either to rename web-ui's target or to make the shared one conditional.
Not worth doing alone; fold it into the next change that touches either Makefile.

## 13. Discussion creation enqueues its fan-out outside any transaction

`services/discussions/django_impl/handler.py:34-45`

`create_discussion` does `Discussion.objects.create(...)` and then
`create_discussion_notifications.enqueue(...)` with no `transaction.atomic()`
around either, so the two commit separately. A crash or a connection loss
between them leaves a discussion nobody is notified about, permanently — the
queue is a table, so there is no retry that would notice.

The article publish path was given exactly this treatment in the review round:
the enqueue moved *inside* `transaction.atomic()`, so the task row and the
content row commit together. `django-tasks-db` defines no `ENQUEUE_ON_COMMIT`,
which is why `on_commit` is the wrong tool — it would widen the window rather
than close it.

This is the same fix, one `atomic()` block. It was out of scope for that change
and is not urgent: the failure needs a crash in a sub-millisecond window.

## 14. `projects__tags` is dead weight on both competition endpoints

`api/routers/competitions.py`

Same defect as the `projects__images` prefetch removed alongside it:
`CompetitionResponse.from_competition` re-queries
`competition.projects.filter(status=APPROVED)`, and calling `filter()` on a
prefetched related manager clones the queryset and drops the cache, so the
router's prefetch cannot reach it. `from_competition` brings its own
`tags__category` prefetch.

Left in place only because it is not an image prefetch and so fell outside that
change's remit. Costs one wasted query per request on both endpoints. Removing
`projects__images` measured 14 queries down to 13; expect the same shape here.

## 15. `describeApiError` covers four screens, not the app

`src/web-ui/src/lib/api/errors.ts`

The author-facing error copy landed on the article authoring page, my-projects,
profile and login. Roughly twenty `err instanceof Error ? err.message : "Failed
to …"` sites remain — notifications, discussions, follows, competitions — and
still surface raw throw text such as "Unauthorized" or "Failed to fetch".

`describeApiError` is the seam; each site needs a fallback sentence chosen for
what the user was doing. Mechanical, but it is twenty small copy decisions
rather than a find-and-replace.

## 16. The query-counting test helper is duplicated

`services/articles/django_impl/test_handler.py`,
`services/follows/django_impl/test_query.py`

Both define their own `_count_queries`. A third copy is one prefetch regression
away. Lifting it needs a shared test-support module, which does not exist yet —
that decision is the actual work, not the move.
