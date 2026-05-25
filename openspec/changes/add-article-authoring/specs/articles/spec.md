## ADDED Requirements

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

The system SHALL provide an `Article` model in a new `apps/articles` Django app. The model SHALL include: `id` (UUID), `project` (FK to Project, `on_delete=CASCADE`, `related_name="articles"`), `channel` (FK to Channel, `on_delete=PROTECT`), `author` (FK to User, nullable), `title` (CharField, max 200), `body` (TextField, markdown), `hero_image` (FK to `projects.ProjectImage`, nullable, `on_delete=PROTECT`), `slug` (SlugField, nullable, unique per project when present), `source` (CharField, choices `internal` / `external`, default `internal`), `external_url` (URLField, nullable), `state` (CharField, choices `draft` / `published`, default `draft`), `published_at` (DateTimeField, nullable), `global_visibility` (CharField, choices `auto` / `pending` / `approved` / `demoted`, default `auto`), `created_at`, `updated_at`.

A partial unique constraint SHALL enforce uniqueness of `(project, slug)` where `slug IS NOT NULL`. A CHECK constraint (or save-time guard for SQLite) SHALL enforce `(source = 'internal' AND external_url IS NULL) OR (source = 'external' AND external_url IS NOT NULL)`.

#### Scenario: Draft article allows empty title, body, hero image
- **WHEN** an Article is created with `state = draft` and no `title`, `body`, or `hero_image`
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

The publish action SHALL be rejected with HTTP 422 when any of `title`, `body`, or `hero_image` is empty.

Slug generation SHALL ensure uniqueness within the project, appending a numeric suffix on collision.

Slug SHALL be generated once on first publish and SHALL NOT be regenerated when the title is edited later.

#### Scenario: Successful publish from draft
- **GIVEN** a draft Article with non-empty `title`, `body`, and `hero_image`
- **WHEN** an authorised contributor publishes it
- **THEN** `state` SHALL be `published`
- **AND** `published_at` SHALL be set
- **AND** `slug` SHALL be assigned

#### Scenario: Publish without hero image is rejected
- **GIVEN** a draft Article with `title` and `body` set but no `hero_image`
- **WHEN** an authorised contributor attempts to publish it
- **THEN** the system SHALL return HTTP 422
- **AND** the Article SHALL remain `state = draft`

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

### Requirement: Authoring endpoint and entry point

The system SHALL provide a "Write article" entry point on the project page that is visible only to authenticated users who are a `ProjectContributor` of the project with `full_edit = True`.

The system SHALL provide an authoring page at `/projects/<project-slug>/articles/new` (Next.js route) and `/projects/<project-slug>/articles/<id>/edit` for an existing draft. The authoring page SHALL provide:
- A markdown editor with side-by-side preview on viewports `≥ md` and tabbed (Edit / Preview) below that.
- Drag-to-insert image upload: dropping an image file on the editor SHALL upload it via the existing project-image upload endpoint and insert a `![](url)` reference at the cursor.
- A hero-image uploader above the body (separate from inline body images).
- A channel dropdown listing this project's channels.
- A "Save draft" button (no field requirements) and a "Publish" button (requires title, body, hero image; opens a confirm dialog with optional `published_at` override).

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
- **WHEN** they navigate to `/projects/<P-slug>/articles/new`
- **THEN** the page SHALL respond with 403 or redirect to the project page

### Requirement: Article render page

The system SHALL serve a render page at `/projects/<project-slug>/articles/<article-slug>` that displays the Article's hero image, title, optional byline, and the markdown-rendered body. The page SHALL reuse the project-page header so the Article is unambiguously part of its project.

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

A `ProjectContributor` with `full_edit = True` SHALL be able to edit `title`, `body`, `hero_image`, `channel`, and `published_at` on a published Article. Editing SHALL NOT alter `slug` or `global_visibility`. Editing SHALL NOT fire notifications.

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
