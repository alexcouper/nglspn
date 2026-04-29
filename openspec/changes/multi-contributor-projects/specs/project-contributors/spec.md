## ADDED Requirements

### Requirement: Project contributors are stored in a join model

The system SHALL persist project contributors in a `ProjectContributor` model with the following fields:

- `id`: UUID primary key
- `project`: FK to `Project` (`on_delete=CASCADE`, `related_name="contributors"`)
- `user`: FK to the user model (`on_delete=CASCADE`, `related_name="project_contributions"`)
- `role`: a `TextChoices` field with values `OWNER` and `SUGGESTER`
- `full_edit`: boolean, default `True`
- `created_at`: auto-now-add datetime

The model SHALL declare `db_table = "project_contributors"` and a `unique_together` constraint on `(project, user)`. Default ordering SHALL place `OWNER` rows before `SUGGESTER` rows, then by `created_at` ascending, so consumers iterating contributors get a stable, role-prioritised order without additional sorting.

#### Scenario: Each (project, user) pair is unique

- **WHEN** an attempt is made to insert a second `ProjectContributor` row for a `(project, user)` pair that already has a row
- **THEN** the insert is rejected by the database unique constraint

#### Scenario: Default role is not implied

- **WHEN** a `ProjectContributor` row is created
- **THEN** the caller MUST set `role` and `full_edit` explicitly (no implicit default for `role`); `full_edit` defaults to `True`

#### Scenario: Default ordering returns OWNER before SUGGESTER

- **GIVEN** a project with one `OWNER` contributor (created later) and one `SUGGESTER` contributor (created earlier)
- **WHEN** the project's `contributors` related manager is iterated with the default ordering
- **THEN** the `OWNER` row is yielded before the `SUGGESTER` row

### Requirement: Write access to a project is gated on a contributor row with full edit

The system SHALL grant write access to a project to any authenticated user who has a `ProjectContributor` row for that project with `full_edit = True`. No other user SHALL be able to update, delete, publish, resubmit, or otherwise mutate the project (administrative or moderator paths excepted, which are governed by their own specs).

A single permission helper SHALL encapsulate this rule and be the only source of truth used by routers, services, and signals.

#### Scenario: Contributor with full_edit can update

- **GIVEN** user A has a `ProjectContributor` row on project P with `full_edit = True`
- **WHEN** user A calls `PUT /api/my-projects/{P.id}` with valid fields
- **THEN** the update is applied and a `200` response is returned

#### Scenario: Contributor with full_edit disabled cannot update

- **GIVEN** user A has a `ProjectContributor` row on project P with `full_edit = False`
- **WHEN** user A calls `PUT /api/my-projects/{P.id}` with valid fields
- **THEN** the response is `404` (consistent with other `/api/my-projects` endpoints when access is denied)
- **AND** the project is unchanged

#### Scenario: Non-contributor cannot update

- **GIVEN** user A has no `ProjectContributor` row on project P
- **WHEN** user A calls `PUT /api/my-projects/{P.id}` with valid fields
- **THEN** the response is `404`
- **AND** the project is unchanged

#### Scenario: Non-contributor cannot publish, resubmit, or delete

- **GIVEN** user A has no `ProjectContributor` row on project P, or has one with `full_edit = False`
- **WHEN** user A calls `POST /api/my-projects/{P.id}/publish`, `POST /api/my-projects/{P.id}/resubmit`, or `DELETE /api/my-projects/{P.id}`
- **THEN** each endpoint returns `404`
- **AND** the project is unchanged

### Requirement: Existing projects are backfilled as OWNER contributors

The system SHALL, during the migration that introduces `ProjectContributor`, insert exactly one `ProjectContributor` row for every existing `Project` with `role = OWNER`, `full_edit = True`, and `user = <existing project owner>`. The data migration SHALL be idempotent: re-running it MUST NOT create duplicate rows for any `(project, user)` pair.

#### Scenario: Backfill produces one OWNER per existing project

- **GIVEN** the database contains N projects before the migration
- **WHEN** the migration runs
- **THEN** N `ProjectContributor` rows exist with `role = OWNER` and `full_edit = True`
- **AND** for each project, the contributor's `user` equals the project's previous owner

#### Scenario: Migration is idempotent

- **GIVEN** the migration has already run once
- **WHEN** the migration is run a second time (e.g. after a partial failure)
- **THEN** no duplicate `ProjectContributor` rows are created
- **AND** the count of `ProjectContributor` rows is unchanged

### Requirement: Project creation inserts the creator as an OWNER contributor

The system SHALL, whenever a project is created via the project service handler, insert a `ProjectContributor` row for the creating user with `role = OWNER` and `full_edit = True` in the same transaction as the project insert.

#### Scenario: Creating a project creates an OWNER contributor

- **WHEN** an authenticated user calls `POST /api/my-projects` with a `website_url`
- **THEN** the new `Project` is created
- **AND** a `ProjectContributor` row exists for that project with `user` = the calling user, `role = OWNER`, and `full_edit = True`

#### Scenario: Project create and contributor insert are atomic

- **GIVEN** the contributor insert raises an unexpected exception during project creation
- **WHEN** the transaction is rolled back
- **THEN** neither the project row nor the contributor row remains in the database

### Requirement: Project responses expose creator and contributors

The Django backend SHALL include the following fields on every project response that returns a full project representation (currently `/api/projects/{identifier}`, `/api/my-projects`, `/api/my-projects/{id}`, and any list responses that already return full projects):

- `creator`: a user summary representing the project's `creator` field (the original submitter).
- `contributors`: a list of contributor summaries, each containing `{ user: UserSummary, role: "OWNER" | "SUGGESTER", full_edit: bool }`. The list is ordered using the model's default ordering (OWNER first, then by `created_at`).

Both fields SHALL be present even when the list is a single self-contributor row, so frontend consumers do not need to special-case the empty case.

The OpenAPI specification and the generated TypeScript types SHALL include these fields.

#### Scenario: Single-contributor project exposes one contributor

- **GIVEN** a project that has only one `ProjectContributor` row (the creator as `OWNER`)
- **WHEN** a client calls `GET /api/projects/{identifier}`
- **THEN** the response includes `creator` set to that user's summary
- **AND** `contributors` is a list with exactly one entry, role `"OWNER"`, `full_edit = true`

#### Scenario: Generated types include the new fields

- **WHEN** `make extract-openapi` and `npm run generate-types` run after the change
- **THEN** the generated TypeScript project type includes `creator` and `contributors` as required fields with the documented shapes

### Requirement: Project notifications fan out across editing contributors

The system SHALL deliver any notification that previously targeted `Project.owner` (including discussion notifications, project state-change emails, and the admin "new project" trigger only insofar as it currently uses owner data for its body) to every `ProjectContributor` row for the project where `full_edit = True`. Each contributor SHALL receive at most one notification per triggering event.

#### Scenario: Single-contributor project receives one notification

- **GIVEN** a project P with exactly one contributor (the creator) who has `full_edit = True`
- **WHEN** an event occurs that previously notified `project.owner`
- **THEN** exactly one notification is created, addressed to that contributor

#### Scenario: Multi-contributor project notifies every full-edit contributor

- **GIVEN** a project P with two contributors A and B, both `full_edit = True`
- **WHEN** an event occurs that previously notified `project.owner`
- **THEN** one notification is created for A and one for B
- **AND** no notification is created for any contributor whose `full_edit` is `False`
