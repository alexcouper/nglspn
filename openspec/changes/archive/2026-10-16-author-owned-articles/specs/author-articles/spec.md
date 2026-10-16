# Spec Delta

## Purpose

An article a person publishes under their own name, with no project behind it:
how it is owned, addressed, imaged, listed and edited.

## ADDED Requirements

### Requirement: An article belongs to a project or to its author

An article SHALL have either a project and a channel on that project, or no project ("author-owned"). An author-owned article SHALL have a non-null `author`, and that author is the only person who may edit, publish or delete it. Its `channel` SHALL be null while it is a draft and SHALL be the author's personal channel once published (see the `user-following` capability); it SHALL never be a project's channel. An article with a project keeps today's rule: any contributor with `full_edit` on the project may edit it.

Deleting a user SHALL delete the author-owned articles they wrote, together with their images and notifications. Articles on a project keep today's behaviour (`author` becomes null, the article stays).

#### Scenario: Author-owned article cannot sit in a project's channel
- **GIVEN** a channel C belonging to project P
- **WHEN** an author-owned article is saved with `channel = C`
- **THEN** the save SHALL be rejected

#### Scenario: Publishing attaches the author's channel
- **GIVEN** an author-owned draft A by U with `channel` null
- **WHEN** U publishes A
- **THEN** A's `channel` SHALL be U's personal channel

#### Scenario: Project article has a channel
- **WHEN** an article is saved with a non-null `project` and `channel` null
- **THEN** the save SHALL be rejected

#### Scenario: Author-owned article without an author
- **WHEN** an article is saved with `project` null and `author` null
- **THEN** the save SHALL be rejected

#### Scenario: Only the author edits an author-owned article
- **GIVEN** an author-owned article A by user U
- **WHEN** a different authenticated user, including a site administrator using the public API, tries to patch, publish or delete A
- **THEN** the response SHALL be 404

#### Scenario: Deleting the author removes the article
- **GIVEN** user U with one author-owned article and one article on project P
- **WHEN** U's account is deleted
- **THEN** the author-owned article, its images and its notifications SHALL be gone
- **AND** the project article SHALL remain with `author` null

### Requirement: Slug uniqueness for an author-owned article is per author

A published author-owned article SHALL have a slug unique among that author's author-owned articles. The same slug MAY exist on another author's article, or on any project's article. Slug generation and collision suffixing SHALL be the same as for a project article, scoped to the author.

#### Scenario: Two authors share a slug
- **GIVEN** an author-owned article by U1 with slug `hello`
- **WHEN** U2 publishes an author-owned article titled "Hello"
- **THEN** U2's article SHALL get slug `hello`

#### Scenario: Same author collides
- **GIVEN** an author-owned article by U with slug `hello`
- **WHEN** U publishes another author-owned article titled "Hello"
- **THEN** the new article SHALL get slug `hello-2`

#### Scenario: Author slug does not collide with a project slug
- **GIVEN** a project article on P with slug `hello`, authored by U
- **WHEN** U publishes an author-owned article titled "Hello"
- **THEN** the author-owned article SHALL get slug `hello`

### Requirement: Images of an author-owned article belong to the article alone

An image SHALL belong to a project, or to an article, or to both (an article on a project). It SHALL NOT belong to neither. An image of an author-owned article SHALL have a null project and SHALL be stored under an `articles/{article_id}/` key prefix. Such images SHALL go through the same upload reservation, completion, variant generation, deletion and orphan sweep as project images, and SHALL NOT appear in any project gallery or count against any project's image cap.

An author-owned article's listing image SHALL be one of that article's own images.

#### Scenario: Image with neither owner is rejected
- **WHEN** an image row is saved with `project` null and `article` null
- **THEN** the save SHALL be rejected

#### Scenario: Upload against an author-owned article
- **GIVEN** an author-owned draft article A by U
- **WHEN** U reserves an upload against A and completes it
- **THEN** the image SHALL have `article = A`, `project` null and a storage key starting `articles/{A.id}/`
- **AND** its width variants SHALL be generated as for a project image

#### Scenario: Listing image from another article is rejected
- **GIVEN** an author-owned article A by U and an image I belonging to a different article
- **WHEN** U sets A's listing image to I
- **THEN** the request SHALL be rejected with 400

#### Scenario: Deleting the article removes its images
- **GIVEN** an author-owned article A with two uploaded images
- **WHEN** A is deleted
- **THEN** both image rows SHALL be gone and their storage objects SHALL be tombstoned for the orphan drain

### Requirement: Author-owned articles are created from the author's profile

`POST /api/auth/me/articles` SHALL create a draft author-owned article for the authenticated caller and return it. The owner's public profile page SHALL show a "Write article" entry point that calls it and opens the editor on the new draft. There SHALL be no channel to choose: an author-owned article has none.

Anonymous requests SHALL be rejected with 401. System users and inactive accounts SHALL NOT be able to create one.

#### Scenario: Create from the profile
- **GIVEN** authenticated user U on their own profile page
- **WHEN** U uses "Write article"
- **THEN** a draft article with `author = U`, `project` null and `channel` null SHALL exist
- **AND** the editor SHALL open on it

#### Scenario: Entry point is not shown to visitors
- **WHEN** anyone views a profile that is not their own
- **THEN** no "Write article" entry point SHALL be rendered

#### Scenario: Anonymous create is rejected
- **WHEN** an unauthenticated client calls `POST /api/auth/me/articles`
- **THEN** the response SHALL be 401

### Requirement: Article routes addressed by id do not go through a project

`GET`, `PATCH`, `DELETE /api/articles/{id}`, `POST /api/articles/{id}/publish`, and the three image routes `POST /api/articles/{id}/images/upload-url`, `POST /api/articles/{id}/images/{image_id}/complete`, `DELETE /api/articles/{id}/images/{image_id}` SHALL address an article by id alone, for both project and author-owned articles. Authorisation SHALL be derived from the article: the caller is its author, or has `full_edit` on its project. A caller without that right SHALL get 404, not 403, so the id reveals nothing. The previous `/api/projects/{slug}/articles/{id}…` forms of these routes SHALL be removed.

Reads by slug stay per container: `GET /api/projects/{slug}/articles/by-slug/{article_slug}` as today, and `GET /api/users/{id}/articles/by-slug/{article_slug}` for an author-owned article, with the same draft and visibility rules as the project form.

`PATCH` on an author-owned article SHALL reject a `channel_id`.

#### Scenario: Author patches their own article
- **GIVEN** an author-owned article A by U
- **WHEN** U sends `PATCH /api/articles/{A.id}` with a new body
- **THEN** the response SHALL be 200 and the body persisted

#### Scenario: Contributor patches a project article by id
- **GIVEN** an article A on project P and user V with `full_edit` on P but not A's author
- **WHEN** V sends `PATCH /api/articles/{A.id}`
- **THEN** the response SHALL be 200

#### Scenario: Stranger gets 404
- **GIVEN** an article A and user W with no right to it
- **WHEN** W sends `PATCH /api/articles/{A.id}`
- **THEN** the response SHALL be 404

#### Scenario: Channel on an author-owned article is rejected
- **GIVEN** an author-owned article A by U
- **WHEN** U sends `PATCH /api/articles/{A.id}` with a `channel_id`
- **THEN** the response SHALL be 422

#### Scenario: Old project-nested id route is gone
- **WHEN** a client calls `PATCH /api/projects/{slug}/articles/{id}`
- **THEN** the response SHALL be 404

### Requirement: Public URL and render page for an author-owned article

A published author-owned article SHALL be served at `/users/{author_id}/articles/{slug}`. The page SHALL render the title, byline and body as a project article does, with the author's name and avatar where the project article shows the project's icon and title, and a back link to the author's profile. The "more from" footer SHALL list the author's other visible author-owned articles and carry a Follow button for the author.

Draft, visibility and 404 rules SHALL be those of the project render page: a draft 404s for everyone but the author; `pending` and `demoted` articles render at their own URL.

The page title and social-card metadata SHALL name the author where a project article names the project.

#### Scenario: Published author-owned article renders
- **GIVEN** a published author-owned article A by U with slug `hello`
- **WHEN** an unauthenticated visitor requests `/users/{U.id}/articles/hello`
- **THEN** the response SHALL be 200 with the rendered article, U's name in the header and a Follow button for U

#### Scenario: Draft 404s for the public
- **GIVEN** a draft author-owned article A by U
- **WHEN** an unauthenticated visitor requests A's URL
- **THEN** the response SHALL be 404

#### Scenario: Draft renders for the author
- **GIVEN** a draft author-owned article A by U
- **WHEN** U requests A's URL while authenticated
- **THEN** the response SHALL be 200

#### Scenario: Wrong author in the URL
- **GIVEN** an author-owned article A by U with slug `hello`
- **WHEN** a visitor requests `/users/{V.id}/articles/hello` for a different user V
- **THEN** the response SHALL be 404

### Requirement: The editor lives at one route for both kinds of article

The authoring page SHALL be served at `/articles/edit/{id}` and SHALL load the article first, then whatever container it has. For an author-owned article the channel dropdown SHALL NOT be rendered and the breadcrumb SHALL lead to the author's profile; for a project article the page SHALL behave as it does today, with the breadcrumb leading to the project in my-projects. After publish or delete the page SHALL return to the container it came from: the project, or the author's profile.

`/projects/{slug}/articles/edit/{id}` SHALL redirect to `/articles/edit/{id}`.

An unauthenticated visitor SHALL be redirected to login with the editor path as return target. An article the caller may not edit SHALL render an in-page message, not the global not-found page.

#### Scenario: Editor opens an author-owned article
- **GIVEN** an author-owned draft A by U
- **WHEN** U opens `/articles/edit/{A.id}`
- **THEN** the editor SHALL render without a channel dropdown and with a breadcrumb to U's profile

#### Scenario: Editor opens a project article
- **GIVEN** a draft A on project P and user V with `full_edit` on P
- **WHEN** V opens `/articles/edit/{A.id}`
- **THEN** the editor SHALL render with P's channel dropdown and a breadcrumb to P in my-projects

#### Scenario: Old editor URL redirects
- **WHEN** a client requests `/projects/{slug}/articles/edit/{id}`
- **THEN** it SHALL be redirected to `/articles/edit/{id}`

#### Scenario: Publish returns to the profile
- **GIVEN** U editing their author-owned draft
- **WHEN** U publishes it
- **THEN** the page SHALL navigate to U's profile

### Requirement: The owner's profile lists every article they wrote

`GET /api/auth/me/articles` SHALL return every article whose `author` is the caller — author-owned and on projects, in every state — newest first, each with its `state`, `global_visibility`, and its project (null for author-owned). The owner's own profile page SHALL render this list in place of the public one, with the same badges the my-projects article tab uses: draft, published, pending review, not shown. Each row SHALL link to the editor.

Nobody but the owner SHALL see drafts, pending or demoted articles on a profile.

#### Scenario: Owner sees all states
- **GIVEN** U with a draft, a published-visible, a pending-review and a demoted article
- **WHEN** U views their own profile
- **THEN** all four SHALL be listed with the matching badge

#### Scenario: Pending review is explained
- **GIVEN** U whose `article_trust` is false, with a published article awaiting review
- **WHEN** U views their own profile
- **THEN** the article SHALL carry a "pending review" badge

#### Scenario: Visitors see only the public list
- **GIVEN** U with a draft and a visible author-owned article
- **WHEN** another user views U's profile
- **THEN** only the visible article SHALL be listed

### Requirement: Public surfaces show the author where they showed the project

Wherever an article is listed with its project — the public profile list, the Latest feed row, a notification group, the article digest email, an article card — an author-owned article SHALL show the author's name instead, and link to the author's profile where the project article links to the project. The public profile list (`GET /api/users/{id}/articles`) SHALL include visible author-owned articles alongside visible articles on approved projects, with `project` null on the former.

#### Scenario: Profile list mixes both kinds
- **GIVEN** U with a visible article on approved project P and a visible author-owned article
- **WHEN** a visitor fetches `GET /api/users/{U.id}/articles`
- **THEN** both SHALL be returned, the project one with `project = {slug, title}` and the author-owned one with `project = null`

#### Scenario: Digest email byline
- **GIVEN** a recipient's article digest containing an author-owned article by U
- **WHEN** the digest is rendered
- **THEN** the entry's byline SHALL be U's name linking to U's profile, and the article link SHALL be its `/users/{U.id}/articles/{slug}` URL
