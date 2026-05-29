## Purpose

Allow community members to submit projects on behalf of others (e.g. projects whose owners are not present on Naglasúpan). Such projects are owned by a system "Community/Unowned" placeholder user, while the actual submitter is recorded as a `SUGGESTER` contributor with full edit rights so they can shape the listing without claiming ownership.

## Requirements

### Requirement: Project creation accepts a community tip-off flag

The Django backend SHALL accept an optional boolean `is_community_tipoff` on `POST /api/my-projects`, defaulting to `False`. The previous field name `community_owned` is removed; clients SHALL send `is_community_tipoff` instead.

When `is_community_tipoff` is omitted or `False`, the existing self-owned creation flow runs unchanged. When `True`, the project SHALL be created with the calling user as `creator`, with two `ProjectContributor` rows inserted in the same transaction:

- `OWNER`: the Community/Unowned seed user, `full_edit = True`.
- `SUGGESTER`: the calling user, `full_edit = True`.

If the seed user does not exist when `is_community_tipoff = True` is requested, the system SHALL fail the request rather than auto-create it.

The contributor writes SHALL trigger the `post_save` signal handler that recomputes `Project.is_community_tipoff`, leaving the column in agreement with the contributor truth at the end of the create transaction.

#### Scenario: Self-owned creation is unchanged when the flag is False or omitted

- **WHEN** an authenticated user submits `POST /api/my-projects` with `website_url` and either no `is_community_tipoff` field or `is_community_tipoff = False`
- **THEN** the project is created in `DRAFT` state with the calling user as `creator`
- **AND** exactly one `ProjectContributor` row exists for the project: the calling user as `OWNER` with `full_edit = True`
- **AND** the project's `is_community_tipoff` column is `False`

#### Scenario: Tip-off creation attaches OWNER and SUGGESTER and sets the column

- **WHEN** an authenticated user submits `POST /api/my-projects` with `is_community_tipoff = True`
- **THEN** the project is created in `DRAFT` state with the calling user as `creator`
- **AND** the project has exactly two `ProjectContributor` rows
- **AND** one row has `role = OWNER`, `user = <Community/Unowned seed user>`, `full_edit = True`
- **AND** the other row has `role = SUGGESTER`, `user = <calling user>`, `full_edit = True`
- **AND** the project's `is_community_tipoff` column is `True`

#### Scenario: Atomicity of tip-off creation

- **GIVEN** the `is_community_tipoff = True` request reaches the project service handler
- **WHEN** any insert in the create-flow path raises an exception
- **THEN** none of the project, OWNER contributor, or SUGGESTER contributor rows remain in the database after rollback

#### Scenario: Missing seed user fails the request

- **GIVEN** the database has no `User` row with `is_system_user = True` matching the documented Community/Unowned seed
- **WHEN** an authenticated user submits `POST /api/my-projects` with `is_community_tipoff = True`
- **THEN** the response is a server error (5xx) and no project is created

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

### Requirement: Project has a denormalized `is_community_tipoff` boolean column

The `Project` model SHALL include a non-nullable boolean column `is_community_tipoff` with `default=False` and a database index. The column is a denormalized cache derived from the contributor truth: it SHALL be `True` if and only if the project has at least one `ProjectContributor` row with `role = OWNER` and `user.is_system_user = True`.

The contributor relationship remains the source of truth. The column SHALL never be set independently of the contributor truth: a flow that wants to mark a project as a tip-off MUST do so by writing the appropriate `ProjectContributor` rows, not by editing the column directly.

#### Scenario: Self-owned project has the column set to False

- **WHEN** a project is created with the calling user as `OWNER` and no system-user contributors
- **THEN** `Project.is_community_tipoff` is `False`

#### Scenario: Tip-off project has the column set to True

- **WHEN** a project is created with `is_community_tipoff = True` (system user as `OWNER`, calling user as `SUGGESTER`)
- **THEN** `Project.is_community_tipoff` is `True` after the create transaction commits

### Requirement: Contributor changes recompute `is_community_tipoff` via signals

When a `ProjectContributor` row is created or updated (`post_save`) or deleted (`post_delete`), the project the row points to SHALL have its `is_community_tipoff` column recomputed from the current contributor set. The recompute SHALL be idempotent and SHALL save with `update_fields=["is_community_tipoff"]` only when the value would change.

Bulk ORM operations on `ProjectContributor` (`bulk_create`, queryset `update()`/`delete()`) bypass Django signals by design. Callers using such operations SHALL invoke `Project.recompute_community_tipoff()` explicitly after the bulk operation. The system does not run a periodic reconciliation job; the column may diverge from the contributor truth if a bulk caller forgets this.

#### Scenario: Adding a system-user OWNER flips the column to True

- **GIVEN** a project with `is_community_tipoff = False` and no system-user contributors
- **WHEN** a `ProjectContributor` row with `role = OWNER` and a system user is saved against that project
- **THEN** the project's `is_community_tipoff` is `True` after the save signal runs

#### Scenario: Removing the system-user OWNER flips the column to False

- **GIVEN** a project with `is_community_tipoff = True` whose only system-user contributor is an `OWNER`
- **WHEN** that `ProjectContributor` row is deleted
- **THEN** the project's `is_community_tipoff` is `False` after the delete signal runs

#### Scenario: Adding a non-OWNER contributor does not change the column

- **GIVEN** a project with `is_community_tipoff = False`
- **WHEN** a `ProjectContributor` row with `role = SUGGESTER` (or any role other than `OWNER`) is saved against that project
- **THEN** the project's `is_community_tipoff` remains `False`

### Requirement: Project responses expose tip-off status as `is_community_tipoff`

Every project response schema (`ProjectResponse`, `DiscoverProjectResponse`, and any other schema that exposes the field) SHALL include `is_community_tipoff: bool`. The previous field name `community_owned` is removed from all response schemas.

The serialized value SHALL be read from the `Project.is_community_tipoff` column directly. The previously used query annotation SHALL be removed.

#### Scenario: Response includes the renamed field

- **WHEN** a client fetches any project via the public API
- **THEN** the response body includes `is_community_tipoff` as a boolean
- **AND** the response body does NOT include `community_owned`

### Requirement: New Arrivals endpoint excludes tip-off projects

`GET /api/projects/new-arrivals` SHALL return only projects with `is_community_tipoff = False`. Tip-off projects SHALL NOT appear in the New Arrivals response under any circumstances.

#### Scenario: New Arrivals returns no tip-offs

- **GIVEN** a mix of self-owned and tip-off projects, all approved and published
- **WHEN** a client calls `GET /api/projects/new-arrivals`
- **THEN** every project in the response has `is_community_tipoff = False`

### Requirement: Recent tip-offs endpoint returns the most recent community tip-offs

The Django backend SHALL expose `GET /api/projects/recent-tipoffs`, returning a list of recent tip-off projects in `DiscoverProjectResponse` shape. The endpoint SHALL:

- Apply the same approval / publish gating as `GET /api/projects/new-arrivals` (e.g., approved, published projects only).
- Filter to `is_community_tipoff = True`.
- Order by `created_at` descending.
- Cap the result at the same limit as `/new-arrivals`.

The endpoint's authentication and rate-limit policy SHALL match `/new-arrivals`.

#### Scenario: Endpoint returns only tip-off projects

- **GIVEN** a mix of self-owned and tip-off projects, all approved and published
- **WHEN** a client calls `GET /api/projects/recent-tipoffs`
- **THEN** every project in the response has `is_community_tipoff = True`
- **AND** no self-owned project is in the response

#### Scenario: Empty list when no tip-offs exist

- **GIVEN** the database has no approved, published projects with `is_community_tipoff = True`
- **WHEN** a client calls `GET /api/projects/recent-tipoffs`
- **THEN** the response is `200 OK` with an empty array

### Requirement: New-project notification email distinguishes tip-offs

The notification email sent to staff when a project is submitted SHALL distinguish tip-off projects from self-owned projects:

- The subject SHALL be "New tip-off submitted - Naglasúpan" when `is_community_tipoff = True`, and "New project submitted - Naglasúpan" otherwise.
- The body SHALL include a single sentence at the top of the project block — "This is a community tip-off — the submitter is not the project's maker." — when `is_community_tipoff = True`. Otherwise the body SHALL render unchanged from prior behaviour.

The email handler SHALL pass `is_community_tipoff` into the template context.

#### Scenario: Self-owned submission produces the existing email

- **WHEN** a self-owned project is submitted
- **THEN** the notification email subject is "New project submitted - Naglasúpan"
- **AND** the email body renders without any tip-off explainer line

#### Scenario: Tip-off submission produces the tip-off variant

- **WHEN** a tip-off project is submitted
- **THEN** the notification email subject is "New tip-off submitted - Naglasúpan"
- **AND** the email body includes the line "This is a community tip-off — the submitter is not the project's maker." at the top of the project block

### Requirement: Django admin surfaces tip-off status on the Project list and change pages

The `ProjectAdmin` SHALL include `is_community_tipoff` in `list_display` (rendered as the standard boolean checkmark/cross), `list_filter` (so staff can narrow to tip-offs or non-tip-offs), and as a read-only field on the change page within the "Ownership" fieldset.

The change page field SHALL be read-only because the column is a derived cache; staff who want to change a project's tip-off status edit the contributor list, which the signals then propagate.

#### Scenario: List view shows the column

- **WHEN** a staff member opens the Django admin Project list
- **THEN** there is a column for `is_community_tipoff` showing the boolean value for each project

#### Scenario: List filter narrows by tip-off status

- **WHEN** a staff member selects the "Yes" option of the `is_community_tipoff` filter
- **THEN** the listing shows only projects whose `is_community_tipoff` is `True`

#### Scenario: Change page shows the field as read-only

- **WHEN** a staff member opens the change page for any project
- **THEN** the "Ownership" fieldset shows `is_community_tipoff` as read-only
- **AND** the field cannot be edited directly through the form
