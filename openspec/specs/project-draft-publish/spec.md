## Purpose

Provide a draft-and-publish lifecycle for projects. Owners create and shape a project privately in `DRAFT` status, and the explicit act of publishing is the single moment when the project becomes reviewable, is tied to a competition and submission month, triggers the admin notification email, and receives its permanent slug and publish timestamp. Drafts can only be deleted or published, and the `DRAFT → PENDING` transition is one-way.
## Requirements
### Requirement: Projects are created in draft status

The system SHALL create new projects in a `DRAFT` status that is private to the project's contributors, and SHALL require only a website URL at creation. Project creation SHALL also create one `ProjectContributor` row in the same transaction with `role = OWNER`, `full_edit = True`, and `user` set to the creating user (see the `project-contributors` capability).

#### Scenario: Creator submits a project with only a URL

- **WHEN** an authenticated user submits `POST /api/my-projects` with only `website_url`
- **THEN** a project is created with `status = DRAFT`
- **AND** its `title` is auto-derived from the URL
- **AND** its `description`, `tagline`, `long_description`, `slug`, `published_at`, and `submission_month` are empty/null
- **AND** no admin notification email is enqueued
- **AND** no competition is auto-assigned
- **AND** a `ProjectContributor` row exists for the project with `user` set to the calling user, `role = OWNER`, and `full_edit = True`

#### Scenario: Draft projects are excluded from public listings

- **WHEN** any public Django endpoint (`GET /api/projects`, `GET /api/projects/featured`, `GET /api/projects/new-arrivals`, `GET /api/projects/winners`, `GET /api/projects/most-discussed`, `GET /api/projects/by-category/*`) returns results
- **THEN** projects with `status = DRAFT` MUST NOT appear

#### Scenario: Draft projects are visible to contributors with full edit

- **WHEN** a user with a `ProjectContributor` row on the draft (where `full_edit = True`) fetches `GET /api/my-projects` or `GET /api/my-projects/{id}`
- **THEN** the draft is returned

### Requirement: Draft projects have a restricted lifecycle

The system SHALL only allow draft projects to transition to `PENDING` via the publish endpoint, or to be deleted by a contributor with `full_edit = True`.

#### Scenario: Draft cannot be approved, rejected, or iced

- **WHEN** an admin or handler attempts to set `status` from `DRAFT` directly to `APPROVED`, `REJECTED`, or `ICE_BOX`
- **THEN** the operation MUST be rejected with an error

#### Scenario: Published project cannot return to draft

- **WHEN** a handler attempts to set `status` from any non-draft state back to `DRAFT`
- **THEN** the operation MUST be rejected with an error

#### Scenario: Contributor with full edit deletes a draft

- **WHEN** a user with a `ProjectContributor` row on the project where `full_edit = True` sends `DELETE /api/my-projects/{id}` for a project with `status = DRAFT`
- **THEN** the project is deleted (unchanged delete behavior)

### Requirement: Publishing validates preconditions and is authoritative

The Django backend SHALL expose `POST /api/my-projects/{id}/publish` for any contributor with `full_edit = True`. The endpoint SHALL validate that the project has a non-empty `title`, a non-empty `description`, and at least one uploaded image with `is_main = True`. If any precondition is unmet, the endpoint SHALL return `400` with a response body containing a `detail` message and a `missing` array enumerating the failed fields. The set of missing field identifiers SHALL be drawn from `title`, `description`, `main_image`.

#### Scenario: Publish succeeds when preconditions are met

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project that has a title, description, and a main uploaded image
- **THEN** the endpoint returns `200` with the updated project
- **AND** the project's `status` is `PENDING`
- **AND** `published_at` is set to the current time
- **AND** `submission_month` is set to the current year-month (`YYYY-MM`)
- **AND** `slug` is populated
- **AND** the admin "new project" notification email is enqueued
- **AND** if a competition currently has `status = ACCEPTING_APPLICATIONS`, the project is added to it

#### Scenario: Web UI redirects to user's project list after publish

- **WHEN** a contributor clicks "Publish" on `/my-projects/[id]` and the backend returns `200`
- **THEN** the web UI navigates to `/my-projects`
- **AND** not to `/projects/{slug}`, because the project is still `PENDING` (not yet approved) and the public page would return 404 for a server-side fetch with no auth context

#### Scenario: Publish rejects a project missing required fields

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project whose `description` is empty
- **THEN** the endpoint returns `400`
- **AND** the response body contains `missing` including `"description"`
- **AND** the project status remains `DRAFT`
- **AND** no email is enqueued

#### Scenario: Publish rejects a project with no main image

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project with no image where `is_main = True` and `upload_status = UPLOADED`
- **THEN** the endpoint returns `400` with `missing` containing `"main_image"`
- **AND** the project status remains `DRAFT`

#### Scenario: Publish rejects a non-draft project

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a project with any status other than `DRAFT`
- **THEN** the endpoint returns `400` with an `InvalidProjectStateError`
- **AND** the project is unchanged

#### Scenario: Publish rejects a request from a non-contributor

- **WHEN** an authenticated user who has no `ProjectContributor` row on the project (or whose row has `full_edit = False`) POSTs to `/api/my-projects/{id}/publish`
- **THEN** the endpoint returns `404` (not found) — consistent with other `/api/my-projects` endpoints

### Requirement: Publish is a one-way transition

The system SHALL NOT expose any endpoint that returns a published project to the `DRAFT` state. Once published, the only removal path is deletion.

#### Scenario: No unpublish endpoint exists

- **WHEN** reviewing the API surface
- **THEN** there is no endpoint that transitions a project from `PENDING`, `APPROVED`, `REJECTED`, or `ICE_BOX` to `DRAFT`

### Requirement: Project creation no longer triggers side effects

The system SHALL NOT enqueue the admin notification email, assign a competition, or stamp a `submission_month` when a project is created. Those side effects SHALL occur only on publish.

#### Scenario: Creating a project does not email the admin

- **WHEN** a user creates a project via `POST /api/my-projects`
- **THEN** no "new project" admin notification email is enqueued

#### Scenario: Creating a project does not assign a competition

- **WHEN** a user creates a project while a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the new draft is not added to that competition

### Requirement: Project model records the publish timestamp

The system SHALL persist a `published_at` datetime on the project, set to the moment of publish. It SHALL be null for drafts and non-null for every non-draft project.

#### Scenario: Drafts have no publish timestamp

- **WHEN** a project has `status = DRAFT`
- **THEN** `published_at` is `null`

#### Scenario: Published projects carry a publish timestamp

- **WHEN** a project has been published
- **THEN** `published_at` is set to the time of the publish call and is not modified thereafter

### Requirement: Existing projects are backfilled as already published

The system SHALL, during migration, treat every existing non-draft project as already published: `slug` is generated, and `published_at` is set to `approved_at` if present, otherwise `created_at`.

#### Scenario: Approved project backfilled with published_at = approved_at

- **WHEN** the data migration runs against an `APPROVED` project whose `approved_at` is set
- **THEN** its `published_at` equals its `approved_at`
- **AND** its `slug` is generated from its `title`

#### Scenario: Non-approved existing project backfilled with published_at = created_at

- **WHEN** the data migration runs against a `PENDING`, `REJECTED`, or `ICE_BOX` project
- **THEN** its `published_at` equals its `created_at`
- **AND** its `slug` is generated from its `title`

