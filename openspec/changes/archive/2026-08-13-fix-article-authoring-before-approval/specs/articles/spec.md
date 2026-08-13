## MODIFIED Requirements

### Requirement: Authoring endpoint and entry point

The system SHALL provide a "Write article" entry point on the project page that is visible only to authenticated users who are a `ProjectContributor` of the project with `full_edit = True`.

The system SHALL provide an authoring page at `/projects/<project-slug>/articles/new` (Next.js route) and `/projects/<project-slug>/articles/edit/<id>` for an existing draft. The authoring page SHALL provide:
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
- **WHEN** they navigate to `/projects/<P-slug>/articles/new`
- **THEN** the page SHALL respond with 403 or redirect to the project page

#### Scenario: Authoring page opens on a draft project
- **GIVEN** a `full_edit` contributor on project P with `status = DRAFT`
- **WHEN** they navigate to `/projects/<P-identifier>/articles/new`
- **THEN** the page SHALL render the authoring UI and create a draft article, not a not-found page

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
- **WHEN** they navigate to `/projects/<P-identifier>/articles/new`
- **THEN** they SHALL be redirected to the login route carrying the authoring path as its return target

#### Scenario: Unresolvable project shows an in-page message
- **GIVEN** an authenticated user and an identifier that resolves to no project they may edit
- **WHEN** they navigate to that identifier's authoring route
- **THEN** the page SHALL render an in-page error with a link back to their projects
