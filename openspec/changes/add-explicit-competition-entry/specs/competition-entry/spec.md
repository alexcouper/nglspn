## ADDED Requirements

### Requirement: Competition entry is a recorded event

The system SHALL record a project's presence in a competition as a
`CompetitionEntry` row that also carries how the entry came about. The row SHALL
hold `competition`, `project`, `entered_at`, `entered_via` and `entered_by`.

`entered_via` SHALL be one of `manual` (entered by a contributor), `admin`
(added through the Django admin) or `backfill` (migrated from the pre-existing
many-to-many rows). `entered_by` SHALL identify the user who caused the entry —
the contributor for `manual`, the acting staff user for `admin` — and SHALL be
null for `backfill` rows and wherever that account has since been deleted.

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

### Requirement: A competition belongs to an entry series

Every competition SHALL carry an `entry_series` slug identifying the run of
competitions it belongs to. It SHALL default to `monthly`, so a competition
created without stating a series is treated as part of the recurring round, and
so every competition existing before this change becomes `monthly` on migration.

The series SHALL be the scope of entry exclusivity: a project holding an entry in
a competition of a given series SHALL NOT enter another competition of that same
series. A project SHALL be free to enter a competition of any series it holds no
entry in, whatever it has entered before and however long ago it was published.

The series SHALL be editable in the Django admin.

#### Scenario: Existing competitions become part of the monthly series

- **GIVEN** competitions created before this change
- **WHEN** the migration runs
- **THEN** each competition's `entry_series` SHALL be `monthly`

#### Scenario: A competition created without a series joins the monthly series

- **WHEN** a competition is created without `entry_series` being set
- **THEN** its `entry_series` SHALL be `monthly`

#### Scenario: A project may enter a different series

- **GIVEN** a project with a `CompetitionEntry` in a competition whose
  `entry_series` is `monthly`
- **WHEN** a competition with a different `entry_series` has
  `status = ACCEPTING_APPLICATIONS`
- **THEN** the project SHALL be eligible to enter that competition

#### Scenario: A project may not re-enter its own series

- **GIVEN** a project with a `CompetitionEntry` in a competition whose
  `entry_series` is `monthly`, in any status including `CLOSED`
- **WHEN** another competition with `entry_series = monthly` has
  `status = ACCEPTING_APPLICATIONS`
- **THEN** the project SHALL NOT be eligible to enter it
- **AND** the reason SHALL be `already_in_series`, identifying the competition
  the project is already in

### Requirement: Entry eligibility is decided per competition by the server

The system SHALL evaluate a project against every competition with
`status = ACCEPTING_APPLICATIONS` and expose the result as an *opportunity* per
competition, used both to render entry affordances and to authorise entry
requests. Each opportunity SHALL state whether the project is eligible for that
competition and, where it is not, why.

Eligibility for a single competition SHALL apply these rules in order, taking the
first match:

1. The project is a community tipoff — not eligible, reason `community_project`.
2. The project's `status` is `REJECTED` or `ICE_BOX` — not eligible, reason
   `project_status`.
3. The project holds a `CompetitionEntry` in a competition whose `entry_series`
   equals this competition's `entry_series` — not eligible, reason
   `already_in_series`, naming the competition already entered.
4. Otherwise — eligible.

A project with `status = DRAFT` SHALL be evaluated like any other, so that the
rounds it could enter are known before it is published.

Where no competition has `status = ACCEPTING_APPLICATIONS`, there SHALL be no
opportunities. The absence of open rounds SHALL NOT be reported as an
ineligibility reason.

#### Scenario: Published project with an open round is eligible

- **GIVEN** a project with `status = PENDING` or `APPROVED`, no
  `CompetitionEntry`, and not a community tipoff
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** there SHALL be an opportunity for that competition
- **AND** it SHALL be eligible

#### Scenario: Draft project is evaluated like any other

- **GIVEN** a project with `status = DRAFT` that is not a community tipoff and
  holds no `CompetitionEntry`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** there SHALL be an eligible opportunity for that competition

#### Scenario: Several open rounds each produce an opportunity

- **GIVEN** an un-entered, non-tipoff published project
- **WHEN** two competitions of different series have
  `status = ACCEPTING_APPLICATIONS`
- **THEN** there SHALL be one opportunity per competition
- **AND** both SHALL be eligible

#### Scenario: Entered in one series, eligible in another

- **GIVEN** a project with a `CompetitionEntry` in a `monthly` competition
- **WHEN** a `monthly` competition and a competition of another series both have
  `status = ACCEPTING_APPLICATIONS`
- **THEN** the opportunity for the `monthly` competition SHALL NOT be eligible,
  with reason `already_in_series`
- **AND** the opportunity for the other competition SHALL be eligible

#### Scenario: No open rounds means no opportunities

- **GIVEN** an un-entered, non-tipoff project
- **WHEN** no competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** there SHALL be no opportunities
- **AND** no ineligibility reason SHALL be reported

#### Scenario: Community tipoff is never eligible

- **GIVEN** a community tipoff project with no `CompetitionEntry`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the opportunity for it SHALL NOT be eligible, with reason
  `community_project`

#### Scenario: Rejected project is not eligible

- **GIVEN** an un-entered project with `status = REJECTED` or `ICE_BOX`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the opportunity for it SHALL NOT be eligible, with reason
  `project_status`

#### Scenario: A tipoff already in a series reports the tipoff reason

- **GIVEN** a community tipoff project holding a `CompetitionEntry` in a
  `monthly` competition
- **WHEN** a `monthly` competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the reason SHALL be `community_project`, the first matching rule

### Requirement: A project reports where it stands

`ProjectResponse` SHALL carry a `competition_standing` object holding two lists:

- `entries` — every competition the project is or was in, newest first, each
  with `entered_at` and `entered_via`.
- `opportunities` — one per competition with `status = ACCEPTING_APPLICATIONS`,
  each stating eligibility and, where ineligible, the reason and — for
  `already_in_series` — the competition that blocks it.

Every competition named anywhere in the object SHALL be identified by at least
`id`, `name`, `slug`, `status` and `submission_deadline`, so a caller can render
and link to it without a second request.

The field SHALL be populated on `/api/my-projects` responses and SHALL be null on
public project responses, where a viewer's entry standing has no meaning.

Resolving the field for a list of projects SHALL NOT issue a query per project.

#### Scenario: Owner sees standing on their project

- **WHEN** a contributor fetches `GET /api/my-projects/{id}`
- **THEN** the response SHALL contain `competition_standing` with the project's
  entries and opportunities

#### Scenario: Entered project lists its competitions

- **GIVEN** a project with `CompetitionEntry` rows in two competitions
- **WHEN** its owner fetches it from `/api/my-projects`
- **THEN** `competition_standing.entries` SHALL contain both competitions
- **AND** each SHALL carry its `entered_at` and `entered_via`
- **AND** they SHALL be ordered newest first

#### Scenario: Blocked opportunity names the competition in the way

- **GIVEN** a project entered in a `monthly` competition
- **WHEN** another `monthly` competition has `status = ACCEPTING_APPLICATIONS`
  and its owner fetches the project
- **THEN** that opportunity SHALL be ineligible with reason `already_in_series`
- **AND** SHALL identify the competition the project is already entered in

#### Scenario: Public project response omits standing

- **WHEN** any caller fetches `GET /api/projects/{identifier}`
- **THEN** `competition_standing` SHALL be null

#### Scenario: Listing projects does not scale queries with project count

- **WHEN** a contributor fetches `GET /api/my-projects` returning several
  projects
- **THEN** the number of database queries SHALL NOT grow with the number of
  projects returned

### Requirement: A published project can enter a named competition

The system SHALL expose `POST /api/my-projects/{id}/competition-entry` for any
contributor with `full_edit = True`, taking a required request body naming the
competition to enter:

```json
{ "competition_id": "<uuid>" }
```

On success it SHALL create a `CompetitionEntry` in that competition with
`entered_via = manual` and `entered_by` set to the calling user, and SHALL return
`200` with the updated project.

The endpoint SHALL re-evaluate the project's opportunities at the moment of the
call rather than trusting the caller. It SHALL return `400` where the named
competition is not among the project's eligible opportunities — because it is not
accepting applications, does not exist, or the project is ineligible for it — and
`400` where the project's `status` is `DRAFT`, since a draft must publish first.
It SHALL return `404` for a caller without `full_edit`, consistent with the other
`/api/my-projects` endpoints. Where a competing write has already entered the
project, it SHALL return `409`.

The endpoint SHALL NOT infer a competition where none is named.

Eligibility SHALL NOT depend on when the project was published: a project
published before this capability existed SHALL be able to enter the next open
round of a series it has not run in.

#### Scenario: Entering a named open competition

- **GIVEN** a project with `status = PENDING` or `APPROVED` holding an eligible
  opportunity for a competition
- **WHEN** a `full_edit` contributor POSTs that competition's id to
  `/api/my-projects/{id}/competition-entry`
- **THEN** the endpoint SHALL return `200` with the updated project
- **AND** a `CompetitionEntry` SHALL exist in that competition with
  `entered_via = manual` and `entered_by` set to the caller
- **AND** the project's `competition_standing.entries` SHALL include it

#### Scenario: A project published between rounds enters the next one

- **GIVEN** a project published while no competition was accepting applications,
  and which therefore holds no `CompetitionEntry`
- **WHEN** a competition later reaches `status = ACCEPTING_APPLICATIONS` and its
  contributor POSTs that competition's id
- **THEN** the endpoint SHALL return `200`
- **AND** the project SHALL be entered in that competition

#### Scenario: A past entrant enters a different series

- **GIVEN** a project holding a `CompetitionEntry` in a closed `monthly`
  competition
- **WHEN** its contributor POSTs the id of an open competition of another series
- **THEN** the endpoint SHALL return `200`
- **AND** the project SHALL hold entries in both competitions

#### Scenario: Entry is refused for a competition of a series already entered

- **WHEN** a contributor POSTs the id of an open `monthly` competition for a
  project already entered in any `monthly` competition
- **THEN** the endpoint SHALL return `400`
- **AND** the existing entry SHALL be unchanged
- **AND** no new `CompetitionEntry` SHALL be created

#### Scenario: Entry is refused for a competition that is not open

- **WHEN** a contributor POSTs the id of a competition whose `status` is not
  `ACCEPTING_APPLICATIONS`
- **THEN** the endpoint SHALL return `400`
- **AND** no `CompetitionEntry` SHALL be created

#### Scenario: Entry is refused without a competition id

- **WHEN** a contributor POSTs to `/api/my-projects/{id}/competition-entry` with
  no `competition_id`
- **THEN** the endpoint SHALL reject the request
- **AND** no `CompetitionEntry` SHALL be created

#### Scenario: Entry is refused for a draft

- **WHEN** a contributor POSTs a competition id for a project with
  `status = DRAFT`
- **THEN** the endpoint SHALL return `400`
- **AND** the project SHALL remain unpublished and un-entered

#### Scenario: Entry is refused for a community tipoff

- **WHEN** a contributor POSTs a competition id for a community tipoff project
- **THEN** the endpoint SHALL return `400`

#### Scenario: Entry is refused for a non-contributor

- **WHEN** an authenticated user with no `full_edit` on the project POSTs to
  `/api/my-projects/{id}/competition-entry`
- **THEN** the endpoint SHALL return `404`

#### Scenario: Round closes between page load and button press

- **GIVEN** a client showing an Enter control for a competition that was an
  eligible opportunity when the page loaded
- **WHEN** the competition's status changes to `VOTING` and the contributor then
  POSTs its id
- **THEN** the endpoint SHALL return `400`
- **AND** no `CompetitionEntry` SHALL be created

#### Scenario: Concurrent entry is resolved without duplication

- **WHEN** two requests to enter the same project into the same competition are
  processed concurrently
- **THEN** exactly one `CompetitionEntry` SHALL exist afterwards
- **AND** the losing request SHALL return `409`

### Requirement: The project page shows every competition a project is and was in

The web UI SHALL render a project's competitions on its detail page at
`/my-projects/[id]` as a single section driven by `competition_standing`, with no
eligibility logic of its own. The section SHALL show:

- **Rounds entered** — one row per `entries` item, naming the competition and
  linking to its page, with the date entered and the competition's current
  status, marking any the project won.
- **Rounds open now** — one row per `opportunities` item, naming the competition
  and its submission deadline. An eligible row SHALL carry an **Enter** control
  that names the competition; an ineligible row SHALL state its reason in place
  of the control.

A community tipoff SHALL NOT show the section at all. It can never enter a
competition, so listing rounds and explaining why each is out of reach is noise
on a page about somebody else's project.

Where an ineligibility reason applies to the project as a whole rather than to
one competition — `project_status` — the UI SHALL state it once rather than
repeating it on every row.

Where a project has neither entries nor opportunities, the section SHALL remain
present and state that no round is currently open and that the project can enter
the next one.

Where an entry request fails, the UI SHALL show the error and re-fetch the
project rather than leaving a stale control on screen.

The project list at `/my-projects` SHALL show each project's competitions in a
compressed read-only form, with no entry controls, and SHALL show nothing for a
community tipoff.

#### Scenario: Entered project lists its rounds

- **GIVEN** a project with entries in two competitions
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the section SHALL name both competitions and link to their pages
- **AND** SHALL show when the project entered each

#### Scenario: Won competition is marked

- **GIVEN** a project that won a competition it is entered in
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** that row SHALL be marked as won

#### Scenario: Each open round it can enter offers its own control

- **GIVEN** a project with eligible opportunities for two competitions
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the section SHALL show a row per competition
- **AND** each SHALL carry an Enter control naming that competition and showing
  its submission deadline

#### Scenario: A blocked open round explains itself

- **GIVEN** a project entered in a `monthly` competition, with an open `monthly`
  competition it cannot enter
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** that row SHALL appear without an Enter control
- **AND** SHALL state that the project is already in that series, naming the
  competition it is in

#### Scenario: A project-wide reason is stated once

- **GIVEN** a project with `status = REJECTED` and opportunities for two open
  competitions, both ineligible with reason `project_status`
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the section SHALL state the reason once
- **AND** SHALL NOT repeat it per competition

#### Scenario: A community tipoff shows no competitions section

- **GIVEN** a community tipoff project
- **WHEN** its tipster views `/my-projects/[id]`
- **THEN** the page SHALL NOT show the competitions section
- **AND** SHALL show no competition messaging of any kind, whether or not a
  round is open

#### Scenario: Entering updates the section

- **GIVEN** a project with an eligible opportunity
- **WHEN** its owner activates that row's Enter control and the request succeeds
- **THEN** the competition SHALL move into the entered rounds
- **AND** its Enter control SHALL no longer be offered

#### Scenario: Failed entry surfaces the reason

- **GIVEN** a project with an eligible opportunity
- **WHEN** its owner activates the Enter control and the request fails
- **THEN** the page SHALL show an error message
- **AND** SHALL re-fetch the project so the section reflects current state

#### Scenario: Nothing entered and nothing open is stated plainly

- **GIVEN** a project with no entries and no opportunities
- **WHEN** its owner views `/my-projects/[id]`
- **THEN** the section SHALL state that no round is currently open and that the
  project can enter the next one

#### Scenario: Project list shows competitions per project

- **WHEN** an owner views `/my-projects`
- **THEN** each project card SHALL show that project's competitions
- **AND** SHALL NOT offer an entry control

### Requirement: Publishing offers entry once it has succeeded

The web UI SHALL offer competition entry immediately after a successful publish
rather than before it. Where the newly published project has at least one
eligible opportunity, the UI SHALL present the open rounds with their submission
deadlines and allow the contributor to enter one or dismiss without entering.
Dismissing SHALL NOT be recorded as a preference: the same rounds SHALL remain
available from the project page.

Where the published project has no eligible opportunity, the UI SHALL NOT
interrupt the publish flow.

#### Scenario: Publish offers the open rounds

- **GIVEN** a draft project that will have eligible opportunities once published
- **WHEN** its contributor publishes it and the request returns `200`
- **THEN** the UI SHALL present those competitions with their submission
  deadlines
- **AND** entering one SHALL call the competition entry endpoint with that
  competition's id

#### Scenario: Declining leaves the rounds available

- **GIVEN** a contributor presented with open rounds after publishing
- **WHEN** they dismiss without entering
- **THEN** no `CompetitionEntry` SHALL be created
- **AND** the project page SHALL still offer those rounds

#### Scenario: Publish with nothing on offer does not interrupt

- **GIVEN** a draft project with no eligible opportunity
- **WHEN** its contributor publishes it
- **THEN** the UI SHALL NOT present an entry prompt

### Requirement: Entering an existing project is reachable from the competition

`/submit` SHALL offer an authenticated user their eligible published projects
with a control to enter each, above the existing form for creating a new project.
Creating a new project SHALL remain available and SHALL NOT be the only option
presented.

`/submit` SHALL accept an optional `competition` query parameter. Where present,
the page SHALL head the list with that competition and list only the projects
eligible for it. Where absent, it SHALL list every project with at least one
eligible opportunity.

Where the user has no eligible project, the page SHALL render as it does today,
offering only project creation.

The competition page's submission call to action SHALL send an authenticated user
to `/submit?competition=<id>` for that competition.

#### Scenario: Submission page offers existing projects for a competition

- **GIVEN** an authenticated user with a published project eligible for a
  competition
- **WHEN** they open `/submit?competition=<that competition's id>`
- **THEN** the page SHALL name that competition
- **AND** SHALL list the project with a control to enter it in that competition
- **AND** SHALL still offer the new-project form

#### Scenario: Entering from the submission page

- **GIVEN** an authenticated user viewing their eligible projects on `/submit`
- **WHEN** they activate the entry control for one of them
- **THEN** the competition entry endpoint SHALL be called with that project and
  competition
- **AND** the page SHALL reflect that the project is entered

#### Scenario: Submission page without a competition lists all eligible projects

- **GIVEN** an authenticated user with projects eligible for different open
  competitions
- **WHEN** they open `/submit` with no `competition` parameter
- **THEN** the page SHALL list every project with at least one eligible
  opportunity

#### Scenario: Projects ineligible for the named competition are not listed

- **GIVEN** an authenticated user whose only published project is already
  entered in the `monthly` series
- **WHEN** they open `/submit?competition=<an open monthly competition>`
- **THEN** the page SHALL NOT list that project
- **AND** SHALL offer only the route to create a new project

#### Scenario: User with no eligible projects sees only creation

- **GIVEN** an authenticated user with no eligible project
- **WHEN** they open `/submit`
- **THEN** the page SHALL offer only the route to create a new project

#### Scenario: Competition page routes to the chooser

- **GIVEN** an authenticated user
- **WHEN** they view a competition with `status = ACCEPTING_APPLICATIONS`
- **THEN** its submission call to action SHALL link to `/submit` for that
  competition
