## MODIFIED Requirements

### Requirement: Projects are created in draft status

The system SHALL create new projects in a `DRAFT` status that is private to the project's contributors, and SHALL require only a website URL at creation. Project creation SHALL also create one or more `ProjectContributor` rows in the same transaction:

- If the request omits `community_owned` or sets it to `False`, exactly one row is created: the calling user as `OWNER` with `full_edit = True`.
- If the request sets `community_owned = True`, two rows are created: the Community/Unowned seed user as `OWNER` with `full_edit = True`, and the calling user as `SUGGESTER` with `full_edit = True`.

In both cases the project's `creator` field is set to the calling user (the original submitter, regardless of ownership shape).

#### Scenario: Self-owned create produces one OWNER contributor

- **WHEN** an authenticated user submits `POST /api/my-projects` with only `website_url`
- **THEN** a project is created with `status = DRAFT` and `creator` set to the calling user
- **AND** its `title` is auto-derived from the URL
- **AND** its `description`, `tagline`, `long_description`, `slug`, `published_at`, and `submission_month` are empty/null
- **AND** no admin notification email is enqueued
- **AND** no competition is auto-assigned
- **AND** a single `ProjectContributor` row exists for the project: the calling user as `OWNER`, `full_edit = True`

#### Scenario: Community-owned create produces OWNER + SUGGESTER contributors

- **WHEN** an authenticated user submits `POST /api/my-projects` with `community_owned = True` and a `website_url`
- **THEN** a project is created with `status = DRAFT` and `creator` set to the calling user
- **AND** two `ProjectContributor` rows exist for the project: the Community/Unowned seed user as `OWNER` with `full_edit = True`, and the calling user as `SUGGESTER` with `full_edit = True`
- **AND** no admin notification email is enqueued
- **AND** no competition is auto-assigned

#### Scenario: Draft projects are excluded from public listings

- **WHEN** any public Django endpoint (`GET /api/projects`, `GET /api/projects/featured`, `GET /api/projects/new-arrivals`, `GET /api/projects/winners`, `GET /api/projects/most-discussed`, `GET /api/projects/by-category/*`) returns results
- **THEN** projects with `status = DRAFT` MUST NOT appear

#### Scenario: Draft projects are visible to contributors with full edit

- **WHEN** a user with a `ProjectContributor` row on the draft (where `full_edit = True`) fetches `GET /api/my-projects` or `GET /api/my-projects/{id}`
- **THEN** the draft is returned

### Requirement: Publishing validates preconditions and is authoritative

The Django backend SHALL expose `POST /api/my-projects/{id}/publish` for any contributor with `full_edit = True`. The endpoint SHALL validate that the project has a non-empty `title`, a non-empty `description`, and at least one uploaded image with `is_main = True`. If any precondition is unmet, the endpoint SHALL return `400` with a response body containing a `detail` message and a `missing` array enumerating the failed fields. The set of missing field identifiers SHALL be drawn from `title`, `description`, `main_image`.

When publishing succeeds, competition entry SHALL depend on whether the project is community-owned: if any `ProjectContributor` row with `role = OWNER` on the project belongs to a user with `is_system_user = True`, the project SHALL NOT be added to a currently-open competition. Otherwise, behaviour is unchanged from the previous spec — if a competition currently has `status = ACCEPTING_APPLICATIONS`, the project is added to it.

#### Scenario: Publish succeeds when preconditions are met for a self-owned project

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project with title, description, and a main uploaded image, and the project's OWNER is a non-system user
- **THEN** the endpoint returns `200` with the updated project
- **AND** the project's `status` is `PENDING`
- **AND** `published_at` is set to the current time
- **AND** `submission_month` is set to the current year-month (`YYYY-MM`)
- **AND** `slug` is populated
- **AND** the admin "new project" notification email is enqueued
- **AND** if a competition currently has `status = ACCEPTING_APPLICATIONS`, the project is added to it

#### Scenario: Publish succeeds for a community-owned project but skips competition entry

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project that has a system-user OWNER (the Community/Unowned seed) and the project meets all publish preconditions
- **THEN** the endpoint returns `200` with the updated project
- **AND** the project's `status` is `PENDING`
- **AND** `published_at`, `submission_month`, and `slug` are populated as for any other publish
- **AND** the admin "new project" notification email is enqueued
- **AND** the project is NOT added to any competition, even if a competition currently has `status = ACCEPTING_APPLICATIONS`

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

#### Scenario: Web UI redirects to user's project list after publish

- **WHEN** a contributor clicks "Publish" on `/my-projects/[id]` and the backend returns `200`
- **THEN** the web UI navigates to `/my-projects`
- **AND** not to `/projects/{slug}`, because the project is still `PENDING` (not yet approved) and the public page would return 404 for a server-side fetch with no auth context
