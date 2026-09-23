# Design: user profile page

## Context

See [`proposal.md`](proposal.md) for the motivation and the
[design canvas](https://claude.ai/artifact/EtycAMJgbaSXFN7vuFHALR) for what the
pages look like. The mechanics that shape the decisions below:

- A user is `first_name`, `last_name`, `info` (markdown) and account flags
  (`apps/users/models.py:62-92`). There is no image of any kind on the model.
- Every image in the system is a `ProjectImage` (`apps/projects/models.py:225`):
  a non-null FK to a project, a storage key under `projects/{project_id}/`, a
  `PENDING → UPLOADED` lifecycle driven by a presigned PUT, WebP width variants
  generated after completion, and an orphan sweep that reaps stale `PENDING`
  rows and drains `OrphanedStorageObject` tombstones written by a `pre_delete`
  receiver. Article images ride on the same row with an `article` FK.
- Crops are applied at render, not at upload: an article's listing image is
  the original plus a normalised `CropRect`, and `CroppedImage` frames it in CSS
  (`components/CroppedImage.tsx`). `ImageCropper` produces the rect and takes a
  `lockRatio`.
- Public reads of projects and articles already have one visibility rule each:
  `ProjectStatus.APPROVED` (`api/routers/_helpers.py:50`) and
  `Article.is_globally_visible` (`apps/articles/models.py`, `globally_visible_q`).
  Contributor roles are `owner` and `tipster`, with `full_edit` on the row
  (`ProjectContributor`). System users are filtered out of credits in the UI
  (`CreatorCredit.tsx`, `ArticleRenderContent.tsx:89`) but not by the API.
- `PublicUserProfile` is embedded in every `ProjectResponse` (creator and each
  contributor) and every `ArticleOut.author`, so anything added to it is paid
  for on every project and article read.
- `/profile` is a client page holding the edit form, a read-only preview and
  the account settings, all fed by `GET /api/auth/me` and `PUT /api/auth/me`.

## Goals / Non-Goals

**Goals:**

- A visitor landing on `/users/{id}` from a byline sees who the person is and
  what they have done here, using only data the visitor could already see
  elsewhere.
- An avatar that costs one small object per user, cannot orphan storage, and
  degrades to initials when absent.
- `/profile` edits the public fields and nothing else; settings have their own
  page.
- No new query pattern per embedded `PublicUserProfile`: the additions to it
  must be answerable from the user row alone.

**Non-Goals:**

- Server-side image processing for avatars (resize, variant generation).
- Rendering the avatar in bylines, contributor lists or the nav beyond the
  account button. The field is exposed; adoption is a follow-up.
- Per-item visibility controls on the profile's project and article lists.
- Pagination of either list. A person has tens of items at most; if that
  stops being true the endpoints gain a `limit` then.
- Changing how `info` is edited beyond a Write/Preview switch. No WYSIWYG.

## Decisions

### A separate `UserAvatar` model, not a `ProjectImage` with a nullable project

`ProjectImage.project` is non-null and everything downstream assumes it: the
gallery cap, cover-image promotion, the storage key prefix, the variant pipeline
and the `_is_gallery_image` predicate. Making it nullable to admit avatars would
put a fourth kind of row into a model whose docstring already spends a
paragraph explaining how to tell the second kind from the first, and every
gallery query would need one more exclusion.

`UserAvatar` copies only the part of the lifecycle that matters for orphan
safety: `storage_key`, `content_type`, `file_size`, `width`, `height`,
`upload_status` (`PENDING`/`UPLOADED`), `created_at`, `uploaded_at`, and a
non-null `user` FK. `User.avatar` is a nullable FK to the row that is current.
A `pre_delete` receiver tombstones the key into `OrphanedStorageObject`, exactly
as the project image receiver does, so replace and remove are both "delete the
row" and the existing `_drain_tombstones` does the S3 work out of the request
path. `_reap_abandoned_uploads` gains a second query over stale `PENDING`
`UserAvatar` rows; the cutoff constant is shared.

*Alternative considered:* two plain fields on `User` (`avatar_key`,
`avatar_pending_key`). Fewer tables, but an abandoned PUT then leaves an object
with no row for the sweep to find, and the receiver pattern has nothing to hang
off. Rejected.

### The browser produces the square; the server stores it

The avatar is rendered at 28 px in the nav, 72 or 96 px on the profile. Serving
a 10 MB original for that is what the variant pipeline exists to avoid, and
extending that pipeline to a second model is the bulk of this change's risk for
a benefit of one size. Instead the edit page runs the upload through
`ImageCropper` with `lockRatio: 1`, draws the chosen region onto a 512×512
canvas and uploads the resulting JPEG. The server sees an ordinary presigned
upload with a 2 MB ceiling (`MAX_AVATAR_FILE_SIZE`) and the shared
`ALLOWED_CONTENT_TYPES` minus `image/gif`, and stores what it is given. One
object, one URL, no crop rect to carry, no variants.

The cost is that the server takes the browser's word for the dimensions on
`complete`, as it already does for every other image. `width`/`height` are
recorded for the same reason they are on `ProjectImage`: a later backfill can
read them without a HEAD.

*Alternative considered:* store the original plus a `CropRect` and frame it
with `CroppedImage`, as articles do. It is the established pattern, but it
serves the original everywhere the avatar appears, and the avatar appears in
the nav on every page. Rejected for weight.

### Two list endpoints under `/api/users/{id}`, not a fatter `PublicUserProfile`

`PublicUserProfile` gains `avatar_url` and `created_at`. Both come off the
`User` row and cost nothing where the schema is embedded. The projects and
articles do not go on it: a `ProjectResponse` carries one profile per
contributor, and nesting every contributor's project list into every project
read is a query explosion for data the project page never shows.

`GET /api/users/{id}/projects` returns `UserProjectResponse` items: `id`,
`slug`, `title`, `tagline`, `category_name`, `main_image_thumb_url`, `role`.
`GET /api/users/{id}/articles` returns `UserArticleResponse` items:
`ArticleListItem`'s public fields plus a `project` ref (`slug`, `title`), since
the article's URL is `/projects/{slug}/articles/{articleSlug}` and the card
shows the project name where a channel-only listing would not need to.

Both live behind `REPO.users` query methods (`list_public_projects_for`,
`list_public_articles_for`) so the visibility rules are applied in one place
and are testable without HTTP. The thumb URL comes from the same
`variant_url` / `resolve_image_by_purpose` helpers the discover lists use
(`services/project/django_impl/query.py`), not a new resolver.

### What is listed, and in what order

Projects: every `ProjectContributor` row for the user whose project is
`APPROVED`, ordered owner rows first, then by `published_at` descending.
`role` is the contributor row's role; the UI labels `owner` as "Owner" and
`tipster` as "Tipped off", matching `CreatorCredit`. `full_edit` is not
exposed: it is an editing permission, not a public fact.

Articles: `Article.author == user`, `is_globally_visible`, and the project is
`APPROVED`, ordered by `published_at` descending. The project check matters
because the article page resolves through `resolve_visible_project_or_404`: an
article on a project that later went to `ICE_BOX` would list here and 404 on
click without it.

The owner viewing their own profile sees exactly what a visitor sees. There is
no "include hidden" mode: the page is the public page, and the my-projects and
authoring surfaces already show drafts.

### System users and inactive accounts have no profile

`GET /api/users/{id}` returns 404 for `is_system_user` or `not is_active`, and
so do the two list endpoints. The UI already refuses to link to a system user
(`CreatorCredit`, `ArticleRenderContent`); the community seed user's projects
are its whole reason to exist and would make a misleading "person". An inactive
account cannot log in or receive mail (`inactive-account-exclusion`) and should
not have a browsable page either. `REPO.users.get_active_by_id` exists and
excludes inactive users; the router switches to it and adds the system-user
check. Embedded `PublicUserProfile`s are unaffected: the 404 is on the page,
not the schema.

### `/profile` edits, `/profile/settings` configures

The current page's Edit/Preview toggle exists because the edit form and the
public rendering share a URL. Once the public page renders the About markdown
with the projects and articles around it, the preview is that page: Save
navigates to `/users/{me}`, and the "Edit profile" button there is the way
back. `ReadOnlyProfile.tsx` goes.

The settings block moves to `/profile/settings` as-is: it is already a
self-contained component with its own saves. The user menu gains a "Settings"
entry; "Profile" keeps pointing at `/profile`. Nothing in onboarding links to
either page.

Save stays a single `PUT /api/auth/me` with the three text fields, so the
`mandatory-profile-names` rule keeps working unchanged. The avatar saves on its
own, immediately on completion, not with the form: it is an upload with a
progress state, and tying it to the Save button would mean holding a completed
upload in limbo or uploading on Save and failing late.

### About: the markdown renderer disallows images and raw HTML

`ReadOnlyProfile` renders `info` with `react-markdown` and no options.
`react-markdown` already drops raw HTML; images are the remaining way to put
arbitrary third-party content on a public page under someone else's name. The
new page passes `disallowedElements={["img"]}` and the edit page's helper text
says so ("paragraphs, lists and links"). Headings are left alone.

### The public page fetches three things in parallel and renders as they land

Profile, projects and articles are three requests. The header renders from the
first; each section shows its skeleton until its own list arrives, the same
shape the project detail page uses for its sections. A 404 on the profile is a
"User not found" page and the two list requests are not made. The lists are
rendered with `ProjectTile` (with `categoryName` and a role chip added to the
tile body as an optional prop) and `ArticleCard` in its `grid` variant with the
project name prepended to the channel line.

## Risks / Trade-offs

- **Two orphan-sweep sources instead of one.** → The `UserAvatar` receiver and
  reap query mirror the project image ones line for line, and
  `test_orphaned_objects.py` gains the avatar cases: abandoned reservation
  reaped, replaced avatar tombstoned and drained, removed avatar likewise.
- **Client-side crop trusts the browser.** A hand-crafted PUT can store a
  non-square or oversized image within the 2 MB limit. → The avatar is always
  rendered in a fixed square box with `object-fit: cover`, so a non-square
  upload is framed rather than broken; the size limit bounds the cost.
  Accepted, consistent with every other upload.
- **`created_at` on `PublicUserProfile` says when the account was made, not
  when the person first did anything.** A 2024 registration with a first
  project in 2026 reads "Joined 2024". → Accepted; it is what every platform
  means by "joined".
- **The projects list leaks contributorship on approved projects only.** A
  tipster on a project still in `PENDING` review is not listed until approval,
  which matches the project being invisible. → Intended, and a spec scenario.
- **Route budget.** `/users/[id]` inherits the `*` budget (200 kB). The page
  adds `ProjectTile`, `ArticleCard` and `react-markdown`, all already in other
  routes' chunks. → `make extra-tests` in `src/web-ui/` after the build; add a
  route-specific line to `bundle-budgets.json` only if the default is loose
  enough to hide a regression.
- **Moving Settings changes a URL people may have bookmarked.** → `/profile`
  keeps working; only the settings block moves, and the edit page links to it.
- **OpenAPI drift.** Three schemas change and five endpoints are added. → The
  backend's `make extra-tests` fails on a stale `backend-openapi.json`; the
  regenerate-and-commit step is a task, not a reminder.

## Migration Plan

1. Deploy the backend first: the new table and the nullable `User.avatar` FK
   are additive, and the schema additions are optional fields. Old clients
   ignore them.
2. Deploy the web UI. The new `/users/[id]` page needs the two list endpoints;
   the edit page needs the avatar endpoints.
3. Rollback is the reverse order. Rolling the backend back with the web UI still
   deployed breaks the profile page's lists and the avatar upload but nothing
   else; the migration is reversible because no data is moved.

No backfill: every existing user has no avatar and renders initials.

## Open Questions

- Whether `avatar_url` should be picked up by `CreatorCredit`, the contributor
  list on the project page and article bylines in this change or the next. The
  field will be there; the design leaves them text-only to keep the diff to
  the profile pages.
- Whether to add a `limit` to the two list endpoints now. Left out until a
  profile exists that needs it.
