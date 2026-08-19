## MODIFIED Requirements

### Requirement: Publishing validates preconditions and is authoritative

The Django backend SHALL expose `POST /api/my-projects/{id}/publish` for any contributor with `full_edit = True`. The endpoint SHALL validate that the project has a non-empty `title`, a non-empty `description`, and at least one uploaded image with `is_main = True`. If any precondition is unmet, the endpoint SHALL return `400` with a response body containing a `detail` message and a `missing` array enumerating the failed fields. The set of missing field identifiers SHALL be drawn from `title`, `description`, `main_image`.

**BREAKING**: publishing SHALL NOT enter the project into any competition, under any circumstances. The endpoint SHALL create no `CompetitionEntry` and SHALL leave `project.competitions` untouched. This replaces the previous behaviour, where a successful publish added a non-community-owned project to the competition with `status = ACCEPTING_APPLICATIONS` and the most recent `start_date`. Whether the project is community-owned no longer affects publishing at all; it is an input to competition eligibility, which is evaluated by the competition entry capability.

The endpoint's request and response shapes are unchanged. A caller that publishes and expects entry SHALL now call `POST /api/my-projects/{id}/competition-entry` afterwards, naming the competition.

The web UI SHALL offer competition entry after a successful publish rather than confirming it beforehand; see the `competition-entry` capability's **Publishing offers entry once it has succeeded** requirement.

#### Scenario: Publish succeeds when preconditions are met

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project with title, description, and a main uploaded image
- **THEN** the endpoint returns `200` with the updated project
- **AND** the project's `status` is `PENDING`
- **AND** `published_at` is set to the current time
- **AND** `submission_month` is set to the current year-month (`YYYY-MM`)
- **AND** `slug` is populated
- **AND** the admin "new project" notification email is enqueued

#### Scenario: Publish enters no competition even when a round is open

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/publish` for a publishable `DRAFT` project while a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the endpoint returns `200`
- **AND** no `CompetitionEntry` is created
- **AND** the project's `competition_standing` reports an eligible opportunity for that competition, so it can be entered by a subsequent request

#### Scenario: Publish behaves identically for a community-owned project

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project that has a system-user OWNER (the Community/Unowned seed) and the project meets all publish preconditions
- **THEN** the endpoint returns `200` with the updated project
- **AND** `published_at`, `submission_month`, and `slug` are populated as for any other publish
- **AND** the admin "new project" notification email is enqueued
- **AND** no `CompetitionEntry` is created — as for every publish

#### Scenario: Web UI redirects to user's project list after publish

- **WHEN** a contributor clicks "Publish" on `/my-projects/[id]`, the backend returns `200`, and any competition entry prompt has been resolved or dismissed
- **THEN** the web UI navigates to `/my-projects`
- **AND** not to `/projects/{slug}`, because the project is still `PENDING` (not yet approved) and the public page would return 404 for a server-side fetch with no auth context

#### Scenario: Publish rejects a project missing required fields

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project whose `description` is empty
- **THEN** the endpoint returns `400`
- **AND** the response body contains `missing` including `"description"`
- **AND** the project status remains `DRAFT`
- **AND** no email is enqueued
- **AND** no competition entry prompt is shown

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
