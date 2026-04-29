## ADDED Requirements

### Requirement: Project creation accepts a community-owned flag

The Django backend SHALL accept an optional boolean `community_owned` on `POST /api/my-projects`, defaulting to `False`. When omitted or `False`, the existing self-owned creation flow runs unchanged. When `True`, the project SHALL be created with the calling user as `creator` and with two `ProjectContributor` rows inserted in the same transaction:

- `OWNER`: the Community/Unowned seed user, `full_edit = True`.
- `SUGGESTER`: the calling user, `full_edit = True`.

If the seed user does not exist when `community_owned = True` is requested, the system SHALL fail the request rather than auto-create it (the seed is established by migration; a missing seed indicates a deployment problem and should not be papered over).

#### Scenario: Self-owned creation is unchanged when the flag is False or omitted

- **WHEN** an authenticated user submits `POST /api/my-projects` with `website_url` and either no `community_owned` field or `community_owned = False`
- **THEN** the project is created in `DRAFT` state with the calling user as `creator`
- **AND** exactly one `ProjectContributor` row exists for the project: the calling user as `OWNER` with `full_edit = True`

#### Scenario: Community-owned creation attaches OWNER and SUGGESTER

- **WHEN** an authenticated user submits `POST /api/my-projects` with `community_owned = True`
- **THEN** the project is created in `DRAFT` state with the calling user as `creator`
- **AND** the project has exactly two `ProjectContributor` rows
- **AND** one row has `role = OWNER`, `user = <Community/Unowned seed user>`, `full_edit = True`
- **AND** the other row has `role = SUGGESTER`, `user = <calling user>`, `full_edit = True`

#### Scenario: Atomicity of community creation

- **GIVEN** the `community_owned = True` request reaches the project service handler
- **WHEN** any insert in the create-flow path raises an exception
- **THEN** none of the project, OWNER contributor, or SUGGESTER contributor rows remain in the database after rollback

#### Scenario: Missing seed user fails the request

- **GIVEN** the database has no `User` row with `is_system_user = True` matching the documented Community/Unowned seed
- **WHEN** an authenticated user submits `POST /api/my-projects` with `community_owned = True`
- **THEN** the response is a server error (5xx) and no project is created
- **AND** the failure is logged so operators can repair the seed

### Requirement: Suggestions endpoint lists projects where the caller is a SUGGESTER

The Django backend SHALL expose `GET /api/my-projects/suggestions` returning the list of projects on which the calling user has a `ProjectContributor` row with `role = SUGGESTER` and `full_edit = True`. The response SHALL use the same item shape as `GET /api/my-projects` so frontend rendering can be reused. The list MAY be empty.

The existing `GET /api/my-projects` endpoint SHALL continue to return projects where the calling user is the project's `creator` (i.e. unchanged from the previous change). Projects where the user is *only* a SUGGESTER SHALL NOT appear in `/api/my-projects`; they appear only in `/api/my-projects/suggestions`.

#### Scenario: Empty list when caller has no suggestions

- **GIVEN** an authenticated user has no `ProjectContributor` rows with `role = SUGGESTER`
- **WHEN** they call `GET /api/my-projects/suggestions`
- **THEN** the response is `200` with an empty list

#### Scenario: List contains community-suggested projects

- **GIVEN** an authenticated user has submitted two community-owned projects
- **WHEN** they call `GET /api/my-projects/suggestions`
- **THEN** the response is `200` containing both projects
- **AND** each project's `contributors` list includes the user as `SUGGESTER` and the seed user as `OWNER`

#### Scenario: Self-owned projects do not appear in suggestions

- **GIVEN** an authenticated user has created one self-owned project (no `community_owned`) and one community-owned project
- **WHEN** they call `GET /api/my-projects/suggestions`
- **THEN** only the community-owned project appears in the response

#### Scenario: SUGGESTER role with full_edit disabled is excluded

- **GIVEN** an authenticated user has a `ProjectContributor` row with `role = SUGGESTER` and `full_edit = False`
- **WHEN** they call `GET /api/my-projects/suggestions`
- **THEN** that project is not included in the response

### Requirement: Existing my-projects listing is creator-scoped

The Django backend SHALL keep `GET /api/my-projects` returning the list of projects where the calling user is the project's `creator`. This is unchanged from the contract established in the previous change and explicitly excludes projects where the calling user is *only* a SUGGESTER.

#### Scenario: Caller sees projects they created, including community-suggested ones

- **GIVEN** an authenticated user has created one self-owned project and one community-owned project
- **WHEN** they call `GET /api/my-projects`
- **THEN** both projects appear (the user is `creator` of both)

#### Scenario: Caller does not see projects of which they are only a SUGGESTER

- **GIVEN** the future "claim" feature has produced a project where user A is `creator` and user B is the only SUGGESTER (this scenario is forward-looking; in this change, the only contributor wiring that creates a SUGGESTER also makes the same user the creator)
- **WHEN** user B calls `GET /api/my-projects`
- **THEN** that project does not appear in the response (it appears in user B's `/suggestions` list instead)
