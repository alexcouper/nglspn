# articles Specification

## Purpose
TBD - created by archiving change add-article-authoring. Update Purpose after archive.
## Requirements
### Requirement: Articles service layer

All read and write operations on `Article`, `Channel`, and related rows initiated by this change SHALL go through a dedicated service layer following the handler/repository pattern already used by `notifications`, `follows`, and other domains in `services/`. The handler SHALL be registered in `services/__init__.py` as `HANDLERS.articles`. Read-only queries SHALL be registered as `REPO.articles`. Channel-management operations SHALL be registered similarly (as `HANDLERS.channels` / `REPO.channels`, or as part of an existing project-domain handler — the wiring choice is recorded in `design.md`).

The handler interface for articles SHALL support at minimum:
- `create_draft(project_id, author_id, channel_id, **fields) -> Article`
- `update_article(article_id, **fields) -> Article`
- `publish(article_id, published_at=None) -> Article` — generates slug, sets `state`/`published_at`/`global_visibility`, and triggers notification fan-out via `HANDLERS.notifications.create_notifications_for_article`.
- `delete_article(article_id) -> None`
- `set_global_visibility(article_id, value) -> Article` (admin demote / approve)

The repository interface SHALL expose at minimum:
- `get_by_id(article_id) -> Article | None`
- `get_by_project_and_slug(project_slug, article_slug) -> Article | None`
- `for_project(project_id, *, include_drafts=False) -> Iterable[Article]`

API routes, signal handlers, admin actions, and management commands SHALL invoke the service layer rather than calling `Article.objects.*` (or equivalent ORM patterns) directly. Admin form rendering is the only exception — Django admin reads through the ORM by design.

#### Scenario: Service is accessible via HANDLERS and REPO
- **WHEN** code imports `from services import HANDLERS, REPO`
- **THEN** `HANDLERS.articles` and `REPO.articles` SHALL be available
- **AND** the channel-management handler SHALL be available (location per `design.md`)

#### Scenario: API routes do not access ORM directly
- **WHEN** the article and channel API route handlers are inspected
- **THEN** no route handler SHALL import or call `Article.objects`, `Channel.objects`, `FollowChannelPreference.objects`, or related managers directly
- **AND** every database operation in a route handler SHALL be a call into `HANDLERS.articles` / `REPO.articles` / the channel handler

### Requirement: Article API endpoints are thin pass-throughs

Every article-related and channel-management API endpoint introduced by this change SHALL be implemented as a thin pass-through to the service layer. Route handlers SHALL be responsible only for: parsing and validating the request payload (via the route's pydantic schema), enforcing authentication and authorisation (caller is a `ProjectContributor` with `full_edit = True` where required), invoking exactly one handler or repository method, and shaping the response. Route handlers SHALL NOT contain business logic and SHALL NOT access ORM models directly.

This applies to all of:

- `POST /api/projects/{slug}/articles` → `HANDLERS.articles.create_draft`
- `GET /api/projects/{slug}/articles/{id}` → `REPO.articles.get_by_id`
- `PATCH /api/projects/{slug}/articles/{id}` → `HANDLERS.articles.update_article`
- `POST /api/projects/{slug}/articles/{id}/publish` → `HANDLERS.articles.publish`
- `DELETE /api/projects/{slug}/articles/{id}` → `HANDLERS.articles.delete_article`
- `GET /api/projects/{slug}/articles/by-slug/{article_slug}` → `REPO.articles.get_by_project_and_slug`
- `POST /api/projects/{slug}/channels` → channel-add handler
- `PATCH /api/projects/{slug}/channels/{id}` → channel-rename handler
- `DELETE /api/projects/{slug}/channels/{id}` → channel-delete handler
- `POST /api/projects/{slug}/channels/{id}/reassign` → channel-reassign handler

#### Scenario: Route handler is a thin pass-through
- **WHEN** an article or channel route handler is inspected
- **THEN** its body SHALL consist of input parsing, auth checks, exactly one service-layer call (per the mapping above), and response shaping
- **AND** SHALL NOT contain ORM queries, multi-step business logic, or transaction-coordination code (those belong in the service layer)

### Requirement: Article model

The system SHALL provide an `Article` model in a new `apps/articles` Django app. The model SHALL include: `id` (UUID), `project` (FK to Project, `on_delete=CASCADE`, `related_name="articles"`), `channel` (FK to Channel, `on_delete=PROTECT`), `author` (FK to User, nullable), `title` (CharField, max 200), `body` (TextField, markdown), `listing_image` (FK to `projects.ProjectImage`, nullable, `on_delete=SET_NULL`), `listing_crop` (JSONField, nullable), `listing_image_mode` (CharField, choices `auto` / `chosen` / `none`, default `auto`), `slug` (SlugField, nullable, unique per project when present), `source` (CharField, choices `internal` / `external`, default `internal`), `external_url` (URLField, nullable), `state` (CharField, choices `draft` / `published`, default `draft`), `published_at` (DateTimeField, nullable), `global_visibility` (CharField, choices `auto` / `pending` / `approved` / `demoted`, default `auto`), `created_at`, `updated_at`.

A partial unique constraint SHALL enforce uniqueness of `(project, slug)` where `slug IS NOT NULL`. A CHECK constraint (or save-time guard for SQLite) SHALL enforce `(source = 'internal' AND external_url IS NULL) OR (source = 'external' AND external_url IS NOT NULL)`.

#### Scenario: Draft article allows empty title, body, listing image
- **WHEN** an Article is created with `state = draft` and no `title`, `body`, or `listing_image`
- **THEN** the save SHALL succeed

#### Scenario: Internal article cannot carry an external_url
- **WHEN** an Article is saved with `source = internal` and a non-null `external_url`
- **THEN** the save SHALL be rejected by the CHECK constraint (or save-time guard on SQLite)

#### Scenario: Two internal articles in the same project cannot share a slug
- **GIVEN** an internal Article A in project P with `slug = "news"`, `state = published`
- **WHEN** another internal Article B is saved in project P with the same `slug`
- **THEN** the save SHALL fail with an integrity error

#### Scenario: Two internal articles in different projects can share a slug
- **GIVEN** an internal Article A in project P1 with `slug = "news"`
- **WHEN** another internal Article B is saved in project P2 with `slug = "news"`
- **THEN** the save SHALL succeed

### Requirement: User `article_trust` flag

The User model SHALL include a non-null `article_trust` BooleanField with `default=True`. The field SHALL be admin-editable only — no public API exposes a way to toggle it.

#### Scenario: New user defaults to trusted
- **WHEN** a new User row is created
- **THEN** `article_trust` SHALL be `True`

#### Scenario: Admin can revoke trust
- **GIVEN** a User with `article_trust = True`
- **WHEN** an admin updates the User in Django admin and sets `article_trust = False`
- **THEN** the row's `article_trust` SHALL be `False`

### Requirement: Publish an internal article

The system SHALL provide a publish endpoint that transitions an internal Article from `state = draft` to `state = published`, sets `published_at` (default `now()`, optionally an author-supplied past datetime), and generates `slug` from `title` using the same Icelandic-aware transliteration helper used for Project slugs.

The publish action SHALL be rejected with HTTP 422 when either of `title` or `body` is empty. An article needs no image — see the `article-listing-image` capability.

Slug generation SHALL ensure uniqueness within the project, appending a numeric suffix on collision.

Slug SHALL be generated once on first publish and SHALL NOT be regenerated when the title is edited later.

#### Scenario: Successful publish from draft
- **GIVEN** a draft Article with non-empty `title` and `body`
- **WHEN** an authorised contributor publishes it
- **THEN** `state` SHALL be `published`
- **AND** `published_at` SHALL be set
- **AND** `slug` SHALL be assigned

#### Scenario: Publish without an image is allowed
- **GIVEN** a draft Article with `title` and `body` set but no `listing_image`
- **WHEN** an authorised contributor publishes it
- **THEN** the system SHALL return HTTP 200
- **AND** the Article SHALL be `state = published`

#### Scenario: Slug stable across title edits
- **GIVEN** a published Article in project P with `title = "Hello world"` and `slug = "hello-world"`
- **WHEN** the author edits `title` to "Hello, world!"
- **THEN** `slug` SHALL remain `hello-world`

#### Scenario: Slug collision appends suffix
- **GIVEN** a published Article in project P with `slug = "news"`
- **WHEN** another Article in project P is published whose title would generate the same slug `news`
- **THEN** the new Article's `slug` SHALL be `news-2` (or the next available numeric suffix)

### Requirement: Backdated publish suppresses notifications

When publishing an Article with `published_at` more than 60 seconds in the past (relative to server clock), the publish handler SHALL NOT fan out notifications (neither in-app nor email).

The 60-second skew window is owned by the publish handler (`HANDLERS.articles.publish`). The notifications service (`HANDLERS.notifications.create_notifications_for_article`) is a pure fan-out primitive and does not re-evaluate the backdate decision — calling it for a backdated article would in fact fan out notifications. The boundary is intentional: a single owner of the gating rule prevents drift and double-checks.

Editing `published_at` on an already-published Article SHALL NEVER fire notifications retroactively.

#### Scenario: Backdated publish fires no notifications
- **GIVEN** a draft Article in project P whose followers include user U
- **WHEN** the author publishes with `published_at = now() - 7 days`
- **THEN** no Notification row SHALL be created for U
- **AND** no email SHALL be enqueued for U

#### Scenario: Publish at "now" fires notifications
- **GIVEN** a draft Article in project P whose followers include user U with the channel's in-app switch on
- **WHEN** the author publishes with no `published_at` override (or `published_at = now()`)
- **THEN** a Notification row SHALL be created for U pointing at the Article

#### Scenario: Editing published_at backwards does not fire
- **GIVEN** a published Article that has already fired notifications
- **WHEN** the author edits `published_at` to a different past date
- **THEN** no additional notifications SHALL be created

### Requirement: Approval flow for internal articles

When an internal Article is published, the system SHALL set `global_visibility = auto` if `author.article_trust = True`, and `global_visibility = pending` if `author.article_trust = False`.

Flipping `author.article_trust` after publish SHALL NOT retroactively change the `global_visibility` of already-published Articles. Admin SHALL be able to set `global_visibility` to any of `auto`, `pending`, `approved`, `demoted` on any individual Article at any time.

The four states have these semantics:
- `auto` — assigned automatically because the author had `article_trust = True` at publish time. No admin action recorded.
- `pending` — awaiting admin review. Author was untrusted at publish time, or (Phase 6) the article came from an unapproved external feed.
- `approved` — admin explicitly reviewed the article and approved it for global rendering. Distinct from `auto` so the audit trail records that an admin made the decision.
- `demoted` — admin pulled the article out of global rendering. Retained locally.

An Article SHALL expose a derived `is_globally_visible` property that returns `True` if and only if `state = published` AND `global_visibility` is one of `auto` or `approved`.

When an admin transitions a `pending` article via the "approve" action, the resulting state SHALL be `approved` (not `auto`) so the audit trail preserves the admin review.

#### Scenario: Trusted author auto-approved
- **GIVEN** a User U with `article_trust = True`
- **WHEN** U publishes an internal Article A
- **THEN** A's `global_visibility` SHALL be `auto`
- **AND** A's `is_globally_visible` SHALL be `True`

#### Scenario: Untrusted author goes to pending
- **GIVEN** a User U with `article_trust = False`
- **WHEN** U publishes an internal Article A
- **THEN** A's `global_visibility` SHALL be `pending`
- **AND** A's `is_globally_visible` SHALL be `False`

#### Scenario: Admin approves a pending article
- **GIVEN** a published Article A with `global_visibility = pending`
- **WHEN** an admin sets `global_visibility = approved`
- **THEN** A's `global_visibility` SHALL be `approved` (not `auto`)
- **AND** A's `is_globally_visible` SHALL be `True`

#### Scenario: Admin can demote an auto-approved article
- **GIVEN** a published Article A with `global_visibility = auto`
- **WHEN** an admin sets `global_visibility = demoted`
- **THEN** A's `is_globally_visible` SHALL be `False`
- **AND** the article row SHALL remain in the database

#### Scenario: Admin can demote an explicitly-approved article
- **GIVEN** a published Article A with `global_visibility = approved`
- **WHEN** an admin sets `global_visibility = demoted`
- **THEN** A's `is_globally_visible` SHALL be `False`

#### Scenario: Trust flag flip does not affect existing articles
- **GIVEN** a User U with `article_trust = True` and one published Article A with `global_visibility = auto`
- **WHEN** an admin flips U's `article_trust` to `False`
- **THEN** A's `global_visibility` SHALL remain `auto`

### Requirement: Read paths gate on `is_globally_visible`

An Article that is not globally visible SHALL NOT be served by any public read path. This covers drafts, articles awaiting admin review and demoted articles alike — one rule, not three.

The rule SHALL have a single home in `apps/articles/models.py`: a `GLOBALLY_VISIBLE_STATES` tuple read by both the `is_globally_visible` property and a `globally_visible_q(prefix)` helper, which `ArticleQuerySet.globally_visible()` and the feed's join filter both build on. The property and the queryset condition are separate expressions of one rule — a test SHALL assert they agree across every `state` × `global_visibility` combination.

The gated paths are:
- `GET /projects/{slug}/articles` — SHALL exclude non-visible Articles unless the caller can edit the project, in which case it SHALL include them. This listing backs the my-projects article table, which is where an author sees the state of their own work, so `ArticleListItem` SHALL carry the derived `is_globally_visible` rather than leaving the client to re-derive the rule.
- `GET /projects/{slug}/articles/by-slug/{article_slug}` — SHALL return 404 for a non-visible Article unless the caller is its author or can edit the project.
- `GET /projects/{slug}/articles/{article_id}` — SHALL return 403 for a non-visible Article unless the caller is its author or can edit the project.
- The Latest feed — `FeedEventQuerySet.visible_subject()` SHALL drop an article-led entry whose Article is not globally visible, in addition to the existing project-status check.

Authorisation ("may this user see it anyway") SHALL stay separate from visibility ("does this render for everyone"): the former lives in `api/routers/articles.py`, the latter on the model.

Feed entries SHALL NOT be maintained on visibility changes. The entry is appended when the Article publishes and the read filter decides whether to serve it, so approving an Article writes nothing to `feed_events` and demoting one leaves `retired_at` untouched — that column means an admin withdrew an entry, which is a different fact.

Supersession is the exception, because it is a claim about *another* entry. `link_article_to_event` SHALL hold a supersession only while the write-up is globally visible: a non-visible Article SHALL release whatever its entry supersedes, and take it again if it becomes visible. Without this the feed loses both entries — the bare event hidden as superseded, the write-up hidden as invisible. The `post_save` signal already re-runs on every Article save, so approval and demotion both re-evaluate the link.

#### Scenario: An article awaiting review is not served publicly
- **GIVEN** a published Article A in an approved project with `global_visibility = pending`
- **WHEN** an anonymous client lists the project's articles or requests A by slug
- **THEN** A SHALL be absent from the listing, and the by-slug request SHALL return 404

#### Scenario: A demoted article is not served publicly
- **GIVEN** a published Article A with `global_visibility = demoted`
- **WHEN** an anonymous client lists the project's articles or requests A by slug
- **THEN** A SHALL be absent from the listing, and the by-slug request SHALL return 404

#### Scenario: The author still sees a held-back article in edit mode
- **GIVEN** a published Article A with `global_visibility = pending` or `demoted`
- **WHEN** its author, or a user who can edit the project, lists the project's articles or requests A by id
- **THEN** A SHALL appear in the listing, and the by-id request SHALL return 200

#### Scenario: A held-back article is not served by the feed
- **GIVEN** a published Article A with `global_visibility = pending`
- **WHEN** the Latest feed is read
- **THEN** neither the lead nor any entry SHALL be A's feed event

#### Scenario: Approving an article serves the entry appended at publish time
- **GIVEN** a published Article A with `global_visibility = pending` and its feed event already appended
- **WHEN** an admin sets `global_visibility = approved`
- **THEN** the feed SHALL serve that same event, with no new `feed_events` row written

#### Scenario: Demoting an article withdraws its entry without retiring it
- **GIVEN** a published Article A with `global_visibility = auto` whose feed event the feed serves
- **WHEN** an admin sets `global_visibility = demoted`
- **THEN** the feed SHALL stop serving that event
- **AND** the event's `retired_at` SHALL remain null

#### Scenario: A write-up awaiting review supersedes nothing
- **GIVEN** a feed event E and an Article A linked to it via `about_feed_event`, published with `global_visibility = pending`
- **WHEN** the Latest feed is read
- **THEN** E's `superseded_by` SHALL be null and the feed SHALL serve E

#### Scenario: Demoting a write-up gives the superseded event back
- **GIVEN** a globally visible Article A whose entry supersedes feed event E
- **WHEN** an admin sets A's `global_visibility = demoted`
- **THEN** E's `superseded_by` SHALL be null and the feed SHALL serve E again

### Requirement: Notification fan-out follows visibility

Publishing an Article SHALL enqueue the notification fan-out only when the Article is globally visible on publish. An Article held for review has no readable page, so notifying its followers would deliver a link that 404s for every recipient.

`set_global_visibility` SHALL enqueue the fan-out when it moves a published Article from a non-visible state into `auto` or `approved`, and SHALL stamp `approved_at` with that moment.

The backdating suppression SHALL be measured against `approved_at` — when the Article became visible to everyone — and never against `published_at`. The two agree on a straight publish by a trusted author and nowhere else: an Article held for review accumulates an old `published_at` by waiting in the queue, so measuring against it suppressed the fan-out for every Article an admin took longer than a minute to approve. An import that should notify nobody arrives already visible and carries a backdated `approved_at` from the publish path.

The fan-out SHALL remain safe to re-run: it creates notifications with `get_or_create` per `(recipient, article)`, so a demote followed by a second approval delivers nothing twice.

#### Scenario: Publishing an article awaiting review notifies nobody
- **GIVEN** a User U with `article_trust = False`, and followers on the channel U is publishing into
- **WHEN** U publishes an internal Article A
- **THEN** no fan-out task SHALL be enqueued

#### Scenario: Approval delivers the article to its followers
- **GIVEN** a published Article A with `global_visibility = pending` and a live `published_at`
- **WHEN** an admin sets `global_visibility = approved`
- **THEN** the fan-out task SHALL be enqueued for A

#### Scenario: A slow review still delivers the article
- **GIVEN** a published Article A with `global_visibility = pending`, published a week ago
- **WHEN** an admin sets `global_visibility = approved`
- **THEN** the fan-out task SHALL be enqueued for A, because A becomes visible now

#### Scenario: An import that was already visible elsewhere notifies nobody
- **GIVEN** an Article published as globally visible with a `published_at` a week in the past
- **WHEN** the publish completes
- **THEN** `approved_at` SHALL be that same past instant and no fan-out task SHALL be enqueued

#### Scenario: Demoting an article enqueues nothing
- **GIVEN** a published, globally visible Article A
- **WHEN** an admin sets `global_visibility = demoted`
- **THEN** no fan-out task SHALL be enqueued

#### Scenario: Re-approving does not notify a follower twice
- **GIVEN** a published Article A whose fan-out has already delivered a notification to follower F
- **WHEN** an admin demotes A and then approves it again
- **THEN** F SHALL hold exactly one notification for A

### Requirement: Authoring endpoint and entry point

The system SHALL provide a "Write article" entry point on the project page that is visible only to authenticated users who are a `ProjectContributor` of the project with `full_edit = True`. The entry point SHALL itself create the draft Article and then route to that draft's authoring page. There SHALL NOT be an authoring route that creates an Article on mount and rewrites its own URL — an image cannot be uploaded against an Article that has no id, so the Article has to exist before the editor opens, and creating it on the click costs one navigation instead of two.

The system SHALL provide an authoring page at `/projects/<project-slug>/articles/edit/<id>`, which always addresses an existing draft. The authoring page SHALL provide:
- A markdown editor with side-by-side preview on viewports `≥ md` and tabbed (Edit / Preview) below that.
- Drag-to-insert image upload: dropping an image file on the editor SHALL upload it against the article it is being written into and insert a `![](url)` reference at the cursor. Article images are addressed under the article that owns them (`/api/projects/{slug}/articles/{id}/images/...`), not through the project's gallery endpoints, and SHALL NOT count against the project's image cap or become its cover image.
- A **Listing settings** tab holding the summary, the listing-image control and a preview of the article's card.
- A channel dropdown listing this project's channels.
- A "Save draft" button (no field requirements) and a "Publish" button (requires title and body; opens a confirm dialog with optional `published_at` override).

The authoring page SHALL resolve its project with the caller's credentials rather than anonymously, and SHALL therefore open for a `full_edit` contributor whatever the project's `status` is — `DRAFT`, `PENDING`, `APPROVED`, `REJECTED` or `ICE_BOX`. Project approval SHALL NOT be a precondition for creating, editing, publishing or deleting an article.

The authoring page SHALL redirect an unauthenticated visitor to the login route rather than rendering a not-found page, and SHALL NOT request the project before authentication has settled.

When the project cannot be resolved for the caller — it does not exist, or the caller has no edit rights on an unapproved one — the authoring page SHALL render an in-page message with a route back to the caller's projects, not the global not-found page.

#### Scenario: Write article button hidden for non-contributors
- **GIVEN** an authenticated user with no `ProjectContributor` row on project P
- **WHEN** they view P's project page
- **THEN** the "Write article" button SHALL NOT be rendered

#### Scenario: Write article button hidden for read-only contributors
- **GIVEN** an authenticated user who is a `ProjectContributor` on project P with `full_edit = False`
- **WHEN** they view P's project page
- **THEN** the "Write article" button SHALL NOT be rendered

#### Scenario: Authoring page rejects non-contributors
- **GIVEN** an authenticated user with no `full_edit` on project P
- **WHEN** they navigate to `/projects/<P-slug>/articles/edit/<article-id>` for an article on P
- **THEN** the page SHALL respond with 403 or redirect to the project page

#### Scenario: Authoring opens on a draft project
- **GIVEN** a `full_edit` contributor on project P with `status = DRAFT`
- **WHEN** they use the entry point on P
- **THEN** a draft Article SHALL be created and the authoring UI SHALL open on its edit route, not a not-found page

#### Scenario: Authoring page opens on a pending project
- **GIVEN** a `full_edit` contributor on project P with `status = PENDING`
- **WHEN** they navigate to `/projects/<P-identifier>/articles/edit/<article-id>` for an article on P
- **THEN** the page SHALL render the authoring UI for that article

#### Scenario: Article endpoints ignore project status
- **GIVEN** a `full_edit` contributor on project P whose `status` is `DRAFT` or `PENDING`
- **WHEN** they create, patch, publish or delete an article on P
- **THEN** each request SHALL succeed exactly as it would on an `APPROVED` project

#### Scenario: Unauthenticated visitor is sent to login
- **GIVEN** a visitor with no session
- **WHEN** they navigate to `/projects/<P-identifier>/articles/edit/<article-id>`
- **THEN** they SHALL be redirected to the login route carrying the authoring path as its return target

#### Scenario: Unresolvable project shows an in-page message
- **GIVEN** an authenticated user and an identifier that resolves to no project they may edit
- **WHEN** they navigate to that identifier's authoring route
- **THEN** the page SHALL render an in-page error with a link back to their projects

### Requirement: Article render page

The system SHALL serve a render page at `/projects/<project-slug>/articles/<article-slug>` that displays the Article's title, optional byline, and the markdown-rendered body. It SHALL NOT display an image band above the body — an author who wants one inserts it into the body. The page SHALL reuse the project-page header so the Article is unambiguously part of its project.

The page SHALL return 404 when:
- the slug does not exist, OR
- the Article's `state` is `draft` and the caller is not the author and not a `ProjectContributor` with `full_edit = True` on the Article's project.

The page SHALL render normally for Articles whose `global_visibility` is `pending` or `demoted` — local rendering is unaffected by approval state. `auto` and `approved` articles also render here (they additionally appear on the global surfaces gated by `is_globally_visible`).

When linked from a Phase 5 carousel, internal article links SHALL open in a new tab.

#### Scenario: Published article renders
- **GIVEN** a published Article A with slug `hello` on project P
- **WHEN** an unauthenticated visitor requests `/projects/<P-slug>/articles/hello`
- **THEN** the response SHALL be 200 and the body SHALL contain the rendered Article

#### Scenario: Draft article 404s for the public
- **GIVEN** a draft Article A on project P
- **WHEN** an unauthenticated visitor requests A's URL
- **THEN** the response SHALL be 404

#### Scenario: Draft article renders for the author
- **GIVEN** a draft Article A authored by user U on project P
- **WHEN** U requests A's URL while authenticated
- **THEN** the response SHALL be 200 and the body SHALL contain the rendered Article

#### Scenario: Demoted article still renders locally
- **GIVEN** a published Article A with `global_visibility = demoted` on project P
- **WHEN** any visitor requests A's URL
- **THEN** the response SHALL be 200

### Requirement: Edit and delete after publish

A `ProjectContributor` with `full_edit = True` SHALL be able to edit `title`, `body`, the listing image and its framing, `channel`, and `published_at` on a published Article. Editing SHALL NOT alter `slug` or `global_visibility`. Editing SHALL NOT fire notifications.

A `ProjectContributor` with `full_edit = True` SHALL be able to hard-delete a published Article. Deletion SHALL cascade-delete any related Notification rows that point at the Article.

#### Scenario: Edit body after publish
- **GIVEN** a published Article A on project P
- **WHEN** an authorised contributor updates `body`
- **THEN** the new body SHALL be persisted
- **AND** no new notifications SHALL be created

#### Scenario: Edit channel after publish
- **GIVEN** a published Article A in channel C1 on project P
- **WHEN** an authorised contributor moves A to channel C2 (also on P)
- **THEN** A's `channel` FK SHALL be C2
- **AND** no new notifications SHALL be created

#### Scenario: Delete after publish
- **GIVEN** a published Article A with 50 Notification rows pointing at it
- **WHEN** an authorised contributor deletes A
- **THEN** A SHALL be removed
- **AND** all 50 Notification rows pointing at A SHALL be removed via cascade

### Requirement: Channel management UI

The system SHALL provide channel-management endpoints and a "Channels" section in project settings, accessible to `ProjectContributor` users with `full_edit = True` on the project. The UI SHALL support:

- **Add channel**: free-form name; rejected with HTTP 409 when the name collides with an existing channel on the same project (unique constraint `(project, name)`).
- **Rename channel**: in-place rename of an existing channel. ChannelPreference rows are FK'd to the Channel row, so user preferences SHALL follow the rename transparently.
- **Delete channel**:
  - SHALL be rejected with HTTP 409 if the channel currently has any associated Articles, with a response body indicating the article count.
  - SHALL be rejected with HTTP 409 if the channel is the only channel on the project.
  - SHALL succeed otherwise; any ChannelPreference rows referencing the channel SHALL be cascade-deleted.
- **Reassign articles**: a "Reassign all articles to channel X" action SHALL bulk-update every Article in the source channel to a chosen target channel on the same project.

#### Scenario: Add duplicate-name channel rejected
- **GIVEN** project P has a channel "Updates"
- **WHEN** an authorised contributor POSTs to add a channel named "Updates"
- **THEN** the response SHALL be HTTP 409

#### Scenario: Rename channel preserves follower preferences
- **GIVEN** project P has channel C named "Updates" and user U has ChannelPreference (follow, C, email=on, in_app=off)
- **WHEN** an authorised contributor renames C to "News"
- **THEN** U's ChannelPreference SHALL still reference C
- **AND** the preference values (email=on, in_app=off) SHALL be unchanged

#### Scenario: Delete channel with articles is rejected
- **GIVEN** channel C on project P has 3 Articles
- **WHEN** an authorised contributor DELETEs C
- **THEN** the response SHALL be HTTP 409 with the article count in the body
- **AND** C SHALL still exist

#### Scenario: Delete only channel is rejected
- **GIVEN** project P has exactly one channel C ("Updates"), with no articles
- **WHEN** an authorised contributor DELETEs C
- **THEN** the response SHALL be HTTP 409
- **AND** C SHALL still exist

#### Scenario: Reassign then delete succeeds
- **GIVEN** project P has channels C1 (3 articles) and C2 (0 articles)
- **WHEN** an authorised contributor reassigns all of C1's articles to C2, then DELETEs C1
- **THEN** all 3 articles SHALL now reference C2
- **AND** C1 SHALL be removed

### Requirement: Article publish event fans out notifications

On a non-backdated publish, the system SHALL iterate every Follow on the Article's project and, for each follower, look up the ChannelPreference for the Article's channel. The system SHALL:

- Create a Notification row pointing at the Article (with `email_cadence` snapshotted from `follower.notification_frequency`) when the channel's `in_app` switch is `True`.
- Enqueue an email (via the existing immediate / hourly / daily notification email path) when the channel's `email` switch is `True` and the follower's `notification_frequency` is not `NEVER`.

Notifications SHALL NOT be created for the Article's author (they don't need to be told about their own publish).

#### Scenario: Follower with in-app on, email on gets both
- **GIVEN** user U follows project P; channel C on P has U's preference `in_app = True, email = True`; U's `notification_frequency = IMMEDIATE`
- **WHEN** a different contributor publishes a non-backdated Article in P / C
- **THEN** a Notification row SHALL be created for U pointing at the Article
- **AND** an immediate email SHALL be sent to U

#### Scenario: Follower with in-app on, email off gets in-app only
- **GIVEN** user U follows project P; channel C on P has U's preference `in_app = True, email = False`
- **WHEN** a contributor publishes a non-backdated Article in P / C
- **THEN** a Notification row SHALL be created for U
- **AND** no email SHALL be enqueued for U

#### Scenario: Follower with NEVER cadence gets in-app only even when email switch is on
- **GIVEN** user U follows project P; channel C has U's preference `in_app = True, email = True`; U's `notification_frequency = NEVER`
- **WHEN** a contributor publishes a non-backdated Article in P / C
- **THEN** a Notification row SHALL be created for U
- **AND** no email SHALL be sent

#### Scenario: Author not notified of their own publish
- **GIVEN** user A follows project P (auto-follow on contributor creation, or explicit follow)
- **WHEN** A publishes an Article in P
- **THEN** no Notification row SHALL be created with A as recipient for this Article

