## MODIFIED Requirements

### Requirement: Publishing validates preconditions and is authoritative

The Django backend SHALL expose `POST /api/my-projects/{id}/publish` for any contributor with `full_edit = True`. The endpoint SHALL validate that the project has a non-empty `title`, a non-empty `description`, and at least one uploaded image with `is_main = True`. If any precondition is unmet, the endpoint SHALL return `400` with a response body containing a `detail` message and a `missing` array enumerating the failed fields. The set of missing field identifiers SHALL be drawn from `title`, `description`, `main_image`.

The endpoint SHALL accept an optional request body `{ "enter_competition": boolean }`. The field SHALL default to `true`, so a request with no body behaves as it did before this change.

When publishing succeeds, competition entry SHALL depend on three things: the caller's `enter_competition` choice, whether the project is community-owned, and whether a round is open. The project SHALL be added to the competition with `status = ACCEPTING_APPLICATIONS` and the most recent `start_date` only when `enter_competition` is true, the project is not community-owned (no `ProjectContributor` row with `role = OWNER` belonging to a user with `is_system_user = True`), and such a competition exists. The resulting entry SHALL be recorded with `entered_via = publish` and `entered_by` set to the publishing user.

Where the project is not entered at publish — because the caller declined, or because no competition was accepting applications — publishing SHALL still succeed, and the project SHALL remain able to enter a later round through the competition entry endpoint. Declining entry at publish SHALL NOT be permanent and SHALL NOT be recorded as a preference.

#### Scenario: Publish succeeds when preconditions are met for a self-owned project

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project with title, description, and a main uploaded image, and the project's OWNER is a non-system user
- **THEN** the endpoint returns `200` with the updated project
- **AND** the project's `status` is `PENDING`
- **AND** `published_at` is set to the current time
- **AND** `submission_month` is set to the current year-month (`YYYY-MM`)
- **AND** `slug` is populated
- **AND** the admin "new project" notification email is enqueued
- **AND** if a competition currently has `status = ACCEPTING_APPLICATIONS`, the project is entered into it with `entered_via = publish` and `entered_by` set to the caller

#### Scenario: Publish with no request body enters the open competition

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/publish` with no request body for a publishable, non-community-owned `DRAFT` project while a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the endpoint returns `200`
- **AND** the project is entered into that competition, as it was before `enter_competition` existed

#### Scenario: Publish declining competition entry

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/publish` with `{"enter_competition": false}` for a publishable `DRAFT` project while a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the endpoint returns `200` with the updated project
- **AND** `status`, `published_at`, `submission_month` and `slug` are set exactly as for any other publish
- **AND** the admin "new project" notification email is enqueued
- **AND** the project is NOT entered into any competition
- **AND** the project's competition entry state is `eligible`, so it can still enter that round afterwards

#### Scenario: Publish requesting entry while no competition is open

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/publish` with `{"enter_competition": true}` while no competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the endpoint returns `200` with the updated project
- **AND** no `CompetitionEntry` is created
- **AND** the project's competition entry state is `no_open_round`, so it can enter the next round when one opens

#### Scenario: Publish succeeds for a community-owned project but skips competition entry

- **WHEN** a contributor with `full_edit = True` POSTs to `/api/my-projects/{id}/publish` for a `DRAFT` project that has a system-user OWNER (the Community/Unowned seed) and the project meets all publish preconditions
- **THEN** the endpoint returns `200` with the updated project
- **AND** `published_at`, `submission_month`, and `slug` are populated as for any other publish
- **AND** the admin "new project" notification email is enqueued
- **AND** the project is NOT added to any competition, even if a competition currently has `status = ACCEPTING_APPLICATIONS` and `enter_competition` is true

#### Scenario: Web UI confirms what publishing will do

- **WHEN** a contributor activates "Publish" on `/my-projects/[id]`
- **THEN** the web UI SHALL present a confirmation naming the competition that publishing would enter the project into, together with its submission deadline, and a control to decline entry
- **AND** where no competition has `status = ACCEPTING_APPLICATIONS`, the confirmation SHALL state that no round is currently open and that the project can enter the next one from its page
- **AND** the project SHALL NOT be published until the contributor confirms

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
- **AND** no `CompetitionEntry` is created, whatever `enter_competition` was set to

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
