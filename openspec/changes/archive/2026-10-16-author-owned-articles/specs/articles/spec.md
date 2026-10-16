# Spec Delta

## MODIFIED Requirements

### Requirement: Article model

The system SHALL provide an `Article` model in a new `apps/articles` Django app. The model SHALL include: `id` (UUID), `project` (FK to Project, nullable, `on_delete=CASCADE`, `related_name="articles"`), `channel` (FK to Channel, nullable, `on_delete=PROTECT`), `author` (FK to User, nullable), `title` (CharField, max 200), `body` (TextField, markdown), `listing_image` (FK to `projects.Image`, nullable, `on_delete=SET_NULL`), `listing_crop` (JSONField, nullable), `listing_image_mode` (CharField, choices `auto` / `chosen` / `none`, default `auto`), `slug` (SlugField, nullable), `source` (CharField, choices `internal` / `external`, default `internal`), `external_url` (URLField, nullable), `state` (CharField, choices `draft` / `published`, default `draft`), `published_at` (DateTimeField, nullable), `global_visibility` (CharField, choices `auto` / `pending` / `approved` / `demoted`, default `auto`), `created_at`, `updated_at`.

An article with a `project` SHALL have a `channel` on that project. An article with no `project` is author-owned: it SHALL have a non-null `author`, a null `channel` while draft, and the author's personal channel once published (see the `author-articles` and `user-following` capabilities).

A partial unique constraint SHALL enforce uniqueness of `(project, slug)` where `slug IS NOT NULL AND project IS NOT NULL`, and a second SHALL enforce uniqueness of `(author, slug)` where `slug IS NOT NULL AND project IS NULL`. A CHECK constraint (or save-time guard for SQLite) SHALL enforce `(source = 'internal' AND external_url IS NULL) OR (source = 'external' AND external_url IS NOT NULL)`.

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

#### Scenario: A project article needs a channel
- **WHEN** an Article is saved with a non-null `project` and a null `channel`
- **THEN** the save SHALL be rejected

### Requirement: Publish an internal article

The system SHALL provide a publish endpoint that transitions an internal Article from `state = draft` to `state = published`, sets `published_at` (default `now()`, optionally an author-supplied past datetime), and generates `slug` from `title` using the same Icelandic-aware transliteration helper used for Project slugs.

The publish action SHALL be rejected with HTTP 422 when either of `title` or `body` is empty. An article needs no image — see the `article-listing-image` capability.

Slug generation SHALL ensure uniqueness within the article's container — its project, or for an author-owned article its author's other author-owned articles — appending a numeric suffix on collision.

Slug SHALL be generated once on first publish and SHALL NOT be regenerated when the title is edited later.

Publishing an author-owned article SHALL ensure the author has a personal channel, creating it on first publish (see the `user-following` capability).

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

#### Scenario: Author-owned publish scopes the slug to the author
- **GIVEN** an author-owned published Article by U with `slug = "news"`
- **WHEN** U publishes another author-owned Article titled "News"
- **THEN** its `slug` SHALL be `news-2`

### Requirement: Authoring endpoint and entry point

The system SHALL provide a "Write article" entry point on the project page that is visible only to authenticated users who are a `ProjectContributor` of the project with `full_edit = True`, and a second on the owner's own profile page that creates an author-owned draft (see the `author-articles` capability). Each entry point SHALL itself create the draft Article and then route to that draft's authoring page. There SHALL NOT be an authoring route that creates an Article on mount and rewrites its own URL — an image cannot be uploaded against an Article that has no id, so the Article has to exist before the editor opens, and creating it on the click costs one navigation instead of two.

The system SHALL provide one authoring page at `/articles/edit/<id>`, which always addresses an existing draft of either kind, and SHALL redirect the former `/projects/<project-slug>/articles/edit/<id>` to it. The authoring page SHALL provide:
- A markdown editor with side-by-side preview on viewports `≥ md` and tabbed (Edit / Preview) below that.
- Drag-to-insert image upload: dropping an image file on the editor SHALL upload it against the article it is being written into and insert a `![](url)` reference at the cursor. Article images are addressed under the article that owns them (`/api/articles/{id}/images/...`), not through the project's gallery endpoints, and SHALL NOT count against the project's image cap or become its cover image.
- A **Listing settings** tab holding the summary, the listing-image control and a preview of the article's card.
- A channel dropdown listing this project's channels, for a project article only.
- A "Save draft" button (no field requirements) and a "Publish" button (requires title and body; opens a confirm dialog with optional `published_at` override).

The authoring page SHALL resolve the article with the caller's credentials rather than anonymously, and for a project article SHALL therefore open for a `full_edit` contributor whatever the project's `status` is — `DRAFT`, `PENDING`, `APPROVED`, `REJECTED` or `ICE_BOX`. Project approval SHALL NOT be a precondition for creating, editing, publishing or deleting an article.

The authoring page SHALL redirect an unauthenticated visitor to the login route rather than rendering a not-found page, and SHALL NOT request the article before authentication has settled.

When the article cannot be resolved for the caller — it does not exist, or the caller has no right to edit it — the authoring page SHALL render an in-page message with a route back to the caller's projects or profile, not the global not-found page.

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
- **WHEN** they navigate to `/articles/edit/<article-id>` for an article on P
- **THEN** the page SHALL render an in-page message and SHALL NOT load the editor

#### Scenario: Authoring opens on a draft project
- **GIVEN** a `full_edit` contributor on project P with `status = DRAFT`
- **WHEN** they use the entry point on P
- **THEN** a draft Article SHALL be created and the authoring UI SHALL open on its edit route, not a not-found page

#### Scenario: Authoring page opens on a pending project
- **GIVEN** a `full_edit` contributor on project P with `status = PENDING`
- **WHEN** they navigate to `/articles/edit/<article-id>` for an article on P
- **THEN** the page SHALL render the authoring UI for that article

#### Scenario: Article endpoints ignore project status
- **GIVEN** a `full_edit` contributor on project P whose `status` is `DRAFT` or `PENDING`
- **WHEN** they create, patch, publish or delete an article on P
- **THEN** each request SHALL succeed exactly as it would on an `APPROVED` project

#### Scenario: Unauthenticated visitor is sent to login
- **GIVEN** a visitor with no session
- **WHEN** they navigate to `/articles/edit/<article-id>`
- **THEN** they SHALL be redirected to the login route carrying the authoring path as its return target

#### Scenario: Unresolvable project shows an in-page message
- **GIVEN** an authenticated user and an id that resolves to no article they may edit — it does not exist, or it sits on a project they cannot edit
- **WHEN** they navigate to that id's authoring route
- **THEN** the page SHALL render an in-page error with a link back to their projects or profile

#### Scenario: Old editor route redirects
- **WHEN** a client requests `/projects/<project-slug>/articles/edit/<id>`
- **THEN** it SHALL be redirected to `/articles/edit/<id>`

### Requirement: Article render page

The system SHALL serve a render page at `/projects/<project-slug>/articles/<article-slug>` for an article on a project, and at `/users/<author-id>/articles/<article-slug>` for an author-owned article, that displays the Article's title, optional byline, and the markdown-rendered body. It SHALL NOT display an image band above the body — an author who wants one inserts it into the body. The project page SHALL reuse the project-page header so the Article is unambiguously part of its project; the author page SHALL show the author's name and avatar in its place (see the `author-articles` capability).

The page SHALL return 404 when:
- the slug does not exist under that container, OR
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

#### Scenario: Author-owned article is not served under a project
- **GIVEN** a published author-owned Article A by U with slug `hello`
- **WHEN** a visitor requests `/projects/<any-slug>/articles/hello`
- **THEN** the response SHALL be 404

### Requirement: Edit and delete after publish

A `ProjectContributor` with `full_edit = True` SHALL be able to edit `title`, `body`, the listing image and its framing, `channel`, and `published_at` on a published Article on a project. The author of an author-owned Article SHALL be able to edit the same fields except `channel`. Editing SHALL NOT alter `slug` or `global_visibility`. Editing SHALL NOT fire notifications.

The same people SHALL be able to hard-delete a published Article. Deletion SHALL cascade-delete any related Notification rows that point at the Article.

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

#### Scenario: Author edits an author-owned article after publish
- **GIVEN** a published author-owned Article A by U
- **WHEN** U updates `body`
- **THEN** the new body SHALL be persisted and no notifications SHALL be created
