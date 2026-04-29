## MODIFIED Requirements

### Requirement: Slugs are immutable after publish

The system SHALL NOT regenerate or modify a project's slug after publish, even when a contributor edits the project's title or other fields.

#### Scenario: Editing title after publish does not change slug

- **GIVEN** a published project with `title = "Old Name"` and `slug = "old-name"`
- **WHEN** a contributor with `full_edit = True` updates the title to "New Name" via `PUT /api/my-projects/{id}`
- **THEN** the project's slug remains `"old-name"`

#### Scenario: Resubmit does not change slug

- **GIVEN** a rejected project with `slug = "some-slug"`
- **WHEN** a contributor with `full_edit = True` resubmits the project
- **THEN** the slug remains `"some-slug"`

### Requirement: Public project endpoint accepts either slug or UUID

The Django backend SHALL expose `GET /api/projects/{identifier}` that resolves `identifier` as either a slug or a UUID, returning the same project representation in both cases. The response body SHALL always include the project's canonical `slug`.

#### Scenario: Lookup by slug

- **WHEN** a client calls `GET /api/projects/cool-app`
- **AND** a published project with that slug exists
- **THEN** the response is `200` with the project, and `response.slug == "cool-app"`

#### Scenario: Lookup by UUID

- **WHEN** a client calls `GET /api/projects/{uuid}` and that UUID identifies a published project with slug `"cool-app"`
- **THEN** the response is `200` with the project, and `response.slug == "cool-app"`

#### Scenario: Draft is not returned to non-contributors

- **WHEN** an unauthenticated client, or an authenticated user who has no `ProjectContributor` row on the project (or whose row has `full_edit = False`), calls `GET /api/projects/{identifier}` for a draft project
- **THEN** the response is `404`

#### Scenario: Draft is returned to a contributor with full edit

- **WHEN** an authenticated user with a `ProjectContributor` row on the project (`full_edit = True`) calls `GET /api/projects/{identifier}` for that draft
- **THEN** the response is `200` with the project

#### Scenario: Unknown identifier

- **WHEN** a client calls `GET /api/projects/{identifier}` and no project matches the identifier by slug or UUID
- **THEN** the response is `404`
