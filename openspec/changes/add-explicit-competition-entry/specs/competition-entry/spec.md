## ADDED Requirements

### Requirement: Competition entry is a recorded event

The system SHALL record a project's presence in a competition as a
`CompetitionEntry` row that also carries how the entry came about. The row SHALL
hold `competition`, `project`, `entered_at`, `entered_via` and `entered_by`.

`entered_via` SHALL be one of `publish` (chosen while publishing), `manual`
(entered later from the project page), `admin` (added through the Django admin)
or `backfill` (migrated from the pre-existing many-to-many rows). `entered_by`
SHALL identify the user who caused the entry — the contributor for `publish` and
`manual`, the acting staff user for `admin` — and SHALL be null for `backfill`
rows and wherever that account has since been deleted.

`CompetitionEntry` SHALL be the `through` model of `Competition.projects`, whose
`related_name` SHALL remain `competitions`, so that `project.competitions` and
`competition.projects` continue to resolve for every existing reader.

A project SHALL NOT hold more than one entry in the same competition.

#### Scenario: Entry records its provenance

- **WHEN** a project enters a competition by any route
- **THEN** a `CompetitionEntry` row SHALL exist for that project and competition
- **AND** `entered_at` SHALL hold the moment of entry
- **AND** `entered_via` SHALL identify the route taken

#### Scenario: Existing membership survives the migration

- **GIVEN** a database with rows in the pre-existing `Competition.projects`
  many-to-many table
- **WHEN** the migration runs
- **THEN** each row SHALL become a `CompetitionEntry` with
  `entered_via = backfill`
- **AND** `entered_at` SHALL be the project's `published_at`, or the
  competition's `start_date` where the project has none
- **AND** the number of entries SHALL equal the number of original rows

#### Scenario: Relation names are unchanged

- **WHEN** existing code reads `project.competitions` or `competition.projects`
- **THEN** the relation SHALL resolve as before the change

#### Scenario: Duplicate entry into the same competition is rejected

- **WHEN** a second `CompetitionEntry` is created for a project and competition
  that already have one
- **THEN** the write SHALL fail on a uniqueness violation

#### Scenario: Deleting the entering user preserves the entry

- **WHEN** the user recorded in `entered_by` is deleted
- **THEN** the `CompetitionEntry` SHALL remain
- **AND** its `entered_by` SHALL become null

### Requirement: Entry eligibility is decided by the server

The system SHALL expose a single evaluation of a project's competition standing,
used both to render entry affordances and to authorise entry requests. It SHALL
resolve to exactly one of four states, applying these rules in order and taking
the first match:

1. The project has a `CompetitionEntry` — state `entered`, naming that
   competition and the entry's `entered_at`.
2. The project is a community tipoff — state `not_eligible`, reason
   `community_project`.
3. The project's `status` is `REJECTED` or `ICE_BOX` — state `not_eligible`,
   reason `project_status`.
4. No competition has `status = ACCEPTING_APPLICATIONS` — state `no_open_round`.
5. Otherwise — state `eligible`, naming the competition with
   `status = ACCEPTING_APPLICATIONS` and the most recent `start_date`.

A project with `status = DRAFT` SHALL be `eligible` where the rules above allow,
because publishing is its route into the open round.

A project SHALL be eligible for at most one competition in its lifetime: rule 1
takes precedence over rule 5, so a project that has been in any round — open,
voting or closed — is never `eligible` again.

#### Scenario: Published project with an open round is eligible

- **GIVEN** a project with `status = PENDING` or `APPROVED`, no
  `CompetitionEntry`, and not a community tipoff
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL be `eligible`, naming that competition

#### Scenario: Draft project with an open round is eligible

- **GIVEN** a project with `status = DRAFT` that is not a community tipoff
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL be `eligible`, naming that competition

#### Scenario: Project already in a closed round is not eligible again

- **GIVEN** a project with a `CompetitionEntry` in a competition with
  `status = CLOSED`
- **WHEN** another competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL be `entered`, naming the closed competition
- **AND** the state SHALL NOT be `eligible`

#### Scenario: No open round

- **GIVEN** an un-entered, non-tipoff project
- **WHEN** no competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL be `no_open_round`

#### Scenario: Community tipoff is never eligible

- **GIVEN** a community tipoff project with no `CompetitionEntry`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL be `not_eligible` with reason `community_project`

#### Scenario: Rejected project is not eligible

- **GIVEN** an un-entered project with `status = REJECTED` or `ICE_BOX`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL be `not_eligible` with reason `project_status`

#### Scenario: Newest open round wins

- **GIVEN** an eligible project
- **WHEN** more than one competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the state SHALL name the one with the most recent `start_date`

### Requirement: A project reports where it stands

`ProjectResponse` SHALL carry a `competition_entry` object holding the state, the
competition it refers to where one applies, `entered_at` where the state is
`entered`, and a reason where the state is `not_eligible`. The competition SHALL
be identified by at least `id`, `name`, `slug`, `status` and
`submission_deadline`, so a caller can render and link to it without a second
request.

The field SHALL be populated on `/api/my-projects` responses and SHALL be null on
public project responses, where a viewer's entry standing has no meaning.

Resolving the field for a list of projects SHALL NOT issue a query per project.

#### Scenario: Owner sees entry state on their project

- **WHEN** a contributor fetches `GET /api/my-projects/{id}`
- **THEN** the response SHALL contain `competition_entry` with the project's
  state

#### Scenario: Entered project names its competition

- **GIVEN** a project with a `CompetitionEntry`
- **WHEN** its owner fetches it from `/api/my-projects`
- **THEN** `competition_entry.state` SHALL be `entered`
- **AND** `competition_entry.competition` SHALL identify that competition
- **AND** `competition_entry.entered_at` SHALL be the entry's timestamp

#### Scenario: Public project response omits entry state

- **WHEN** any caller fetches `GET /api/projects/{identifier}`
- **THEN** `competition_entry` SHALL be null

#### Scenario: Listing projects does not scale queries with project count

- **WHEN** a contributor fetches `GET /api/my-projects` returning several
  projects
- **THEN** the number of database queries SHALL NOT grow with the number of
  projects returned

### Requirement: A published project can enter an open round

The system SHALL expose `POST /api/my-projects/{id}/competition-entry` for any
contributor with `full_edit = True`. On success it SHALL create a
`CompetitionEntry` in the currently open competition with
`entered_via = manual` and `entered_by` set to the calling user, and SHALL return
`200` with the updated project.

The endpoint SHALL re-evaluate eligibility at the moment of the call rather than
trusting the caller. It SHALL return `400` where the project's state is not
`eligible`, and `400` where the project's `status` is `DRAFT`, since a draft
enters by publishing. It SHALL return `404` for a caller without `full_edit`,
consistent with the other `/api/my-projects` endpoints. Where a competing write
has already entered the project, it SHALL return `409`.

Eligibility SHALL NOT depend on when the project was published: a project
published before this capability existed SHALL be able to enter the next open
round.

#### Scenario: Entering an open round from the project page

- **GIVEN** a project whose state is `eligible` and whose `status` is `PENDING`
  or `APPROVED`
- **WHEN** a `full_edit` contributor POSTs to
  `/api/my-projects/{id}/competition-entry`
- **THEN** the endpoint SHALL return `200` with the updated project
- **AND** a `CompetitionEntry` SHALL exist in the open competition with
  `entered_via = manual` and `entered_by` set to the caller
- **AND** the project's `competition_entry.state` SHALL be `entered`

#### Scenario: A project published between rounds enters the next one

- **GIVEN** a project published while no competition was accepting applications,
  and which therefore holds no `CompetitionEntry`
- **WHEN** a competition later reaches `status = ACCEPTING_APPLICATIONS` and its
  contributor POSTs to `/api/my-projects/{id}/competition-entry`
- **THEN** the endpoint SHALL return `200`
- **AND** the project SHALL be entered in that competition

#### Scenario: Entry is refused when no round is open

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/competition-entry` while
  no competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the endpoint SHALL return `400`
- **AND** no `CompetitionEntry` SHALL be created

#### Scenario: Entry is refused for an already-entered project

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/competition-entry` for a
  project that already holds a `CompetitionEntry` in any competition
- **THEN** the endpoint SHALL return `400`
- **AND** the existing entry SHALL be unchanged

#### Scenario: Entry is refused for a draft

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/competition-entry` for a
  project with `status = DRAFT`
- **THEN** the endpoint SHALL return `400`
- **AND** the project SHALL remain unpublished and un-entered

#### Scenario: Entry is refused for a community tipoff

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/competition-entry` for a
  community tipoff project
- **THEN** the endpoint SHALL return `400`

#### Scenario: Entry is refused for a non-contributor

- **WHEN** an authenticated user with no `full_edit` on the project POSTs to
  `/api/my-projects/{id}/competition-entry`
- **THEN** the endpoint SHALL return `404`

#### Scenario: Round closes between page load and button press

- **GIVEN** a client showing an Enter button for a project whose state was
  `eligible` when the page loaded
- **WHEN** the competition's status changes to `VOTING` and the contributor then
  POSTs to `/api/my-projects/{id}/competition-entry`
- **THEN** the endpoint SHALL return `400`
- **AND** no `CompetitionEntry` SHALL be created

#### Scenario: Concurrent entry is resolved without duplication

- **WHEN** two requests to enter the same project into the same competition are
  processed concurrently
- **THEN** exactly one `CompetitionEntry` SHALL exist afterwards
- **AND** the losing request SHALL return `409`

### Requirement: The web UI shows and offers competition entry

The web UI SHALL show a project's competition standing on its detail page at
`/my-projects/[id]` and on each card in the project list, rendered from
`competition_entry` without the client re-deriving eligibility:

- `entered` — the competition's name, linking to its page.
- `eligible` on a published project — an **Enter in \<competition name\>**
  control that calls the entry endpoint, plus the submission deadline.
- `eligible` on a draft — no entry control; the publish flow owns that decision.
- `no_open_round` — a statement that no round is currently open and that the
  project can enter the next one.
- `not_eligible` — no entry control and no competition messaging.

Where the entry request fails, the UI SHALL show the error and re-fetch the
project rather than leaving a stale control on screen.

#### Scenario: Entered project shows its competition

- **GIVEN** a project whose `competition_entry.state` is `entered`
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the page SHALL name the competition and link to its page
- **AND** SHALL NOT offer an entry control

#### Scenario: Eligible published project offers entry

- **GIVEN** a published project whose `competition_entry.state` is `eligible`
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the page SHALL offer a control to enter the named competition
- **AND** SHALL show that competition's submission deadline

#### Scenario: Entry control updates the page

- **GIVEN** a published, eligible project
- **WHEN** its owner activates the entry control and the request succeeds
- **THEN** the page SHALL show the project as entered in that competition
- **AND** the entry control SHALL no longer be offered

#### Scenario: Failed entry surfaces the reason

- **GIVEN** a published, eligible project
- **WHEN** its owner activates the entry control and the request fails
- **THEN** the page SHALL show an error message
- **AND** SHALL re-fetch the project so the control reflects current state

#### Scenario: No open round is stated plainly

- **GIVEN** a project whose `competition_entry.state` is `no_open_round`
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the page SHALL state that no round is currently open and that the
  project can enter the next one

#### Scenario: Project list shows standing per project

- **WHEN** an owner views `/my-projects`
- **THEN** each project card SHALL show that project's competition standing

### Requirement: Entering an existing project is reachable from the competition

The competition page and the project submission page SHALL offer an
authenticated user with at least one `eligible` published project a route to
enter that project, distinct from creating a new one. Creating a new project
SHALL remain available and SHALL NOT be the only option presented.

#### Scenario: Competition page offers an existing project

- **GIVEN** an authenticated user with a published project whose state is
  `eligible`
- **WHEN** they view a competition with `status = ACCEPTING_APPLICATIONS`
- **THEN** the page SHALL offer a route to enter an existing project alongside
  the route to create a new one

#### Scenario: Submission page offers existing projects

- **GIVEN** an authenticated user with at least one `eligible` published project
- **WHEN** they open `/submit`
- **THEN** the page SHALL list their eligible projects with a route to each

#### Scenario: User with no eligible projects sees only creation

- **GIVEN** an authenticated user with no `eligible` project
- **WHEN** they open `/submit`
- **THEN** the page SHALL offer only the route to create a new project
