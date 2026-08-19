# competition-entry Specification

## Purpose
Entering a competition is an explicit, recorded act rather than a side effect of
publishing. Covers the `CompetitionEntry` row and its `entered_via` provenance,
entry series, the server-side eligibility rules, the surfaces that offer entry
(post-publish dialog, project page, the competition itself), and how a project's
standing is reported back — including entries still waiting on review.

## Requirements
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

The system SHALL evaluate a project against every competition that is
`status = ACCEPTING_APPLICATIONS` **and that the project does not already hold an
entry in**, and expose the result as an *opportunity* per competition, used both
to render entry affordances and to authorise entry requests. Each opportunity
SHALL state whether the project is eligible for that competition and, where it is
not, why.

A competition the project already holds a `CompetitionEntry` in SHALL NOT be
reported as an opportunity. That round is reported as an entry, which says more
than an opportunity could; reporting it as both listed it twice and named it as
its own blocker.

Eligibility for a single competition SHALL apply these rules in order, taking the
first match:

1. The project is a community tipoff — not eligible, reason `community_project`.
2. The project's `status` is `REJECTED` or `ICE_BOX` — not eligible, reason
   `project_status`.
3. The project's `status` is `DRAFT` — not eligible, reason `project_draft`.
4. The project holds a `CompetitionEntry` in a competition whose `entry_series`
   equals this competition's `entry_series` — not eligible, reason
   `already_in_series`, naming the competition already entered.
5. Otherwise — eligible.

A `DRAFT` project SHALL NOT be reported as eligible for any competition. The
entry endpoint refuses a draft, so a standing that called one eligible would
make every surface offer a control that fails. `project_draft` is distinct from
`project_status` because a draft is one publish away from entering, where a
rejected project is not.

Where no competition is open to the project, there SHALL be no opportunities. The
absence of open rounds SHALL NOT be reported as an ineligibility reason.

#### Scenario: Published project with an open round is eligible

- **GIVEN** a project with `status = PENDING` or `APPROVED`, no
  `CompetitionEntry`, and not a community tipoff
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** there SHALL be an opportunity for that competition
- **AND** it SHALL be eligible

#### Scenario: A round the project is already in is not an opportunity

- **GIVEN** a project holding a `CompetitionEntry` in a competition with
  `status = ACCEPTING_APPLICATIONS`
- **WHEN** its owner fetches the project
- **THEN** that competition SHALL appear in `entries`
- **AND** SHALL NOT appear in `opportunities`

#### Scenario: Entering an open round removes it from the opportunities

- **GIVEN** a project with an eligible opportunity for an open competition
- **WHEN** it enters that competition
- **THEN** the competition SHALL move from `opportunities` into `entries`

#### Scenario: A draft cannot enter until it is published

- **GIVEN** a project with `status = DRAFT` that is not a community tipoff and
  holds no `CompetitionEntry`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the opportunity for it SHALL NOT be eligible, with reason
  `project_draft`

#### Scenario: A tipoff draft reports the tipoff reason

- **GIVEN** a community tipoff project with `status = DRAFT`
- **WHEN** a competition has `status = ACCEPTING_APPLICATIONS`
- **THEN** the reason SHALL be `community_project`, the first matching rule

#### Scenario: Several open rounds each produce an opportunity

- **GIVEN** an un-entered, non-tipoff published project
- **WHEN** two competitions of different series have
  `status = ACCEPTING_APPLICATIONS`
- **THEN** there SHALL be one opportunity per competition
- **AND** both SHALL be eligible

#### Scenario: Entered in one series, eligible in another

- **GIVEN** a project with a `CompetitionEntry` in a closed `monthly` competition
- **WHEN** an open `monthly` competition and an open competition of another
  series both exist
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

- **GIVEN** a community tipoff project holding a `CompetitionEntry` in a closed
  `monthly` competition
- **WHEN** an open `monthly` competition exists
- **THEN** the reason SHALL be `community_project`, the first matching rule

### Requirement: A project reports where it stands

`ProjectResponse` SHALL carry a `competition_standing` object holding two lists:

- `entries` — every competition the project is or was in, newest first, each
  with `entered_at` and `entered_via`.
- `opportunities` — one per competition that is accepting applications and that
  the project does not already hold an entry in, each stating eligibility and,
  where ineligible, the reason and — for `already_in_series` — the competition
  that blocks it.

The two lists SHALL NOT name the same competition.

Every competition named anywhere in the object SHALL be identified by at least
`id`, `name`, `slug`, `status`, `submission_deadline` and `image_url`, so a
caller can render and link to it, image included, without a second request.
`image_url` SHALL be null where the competition has no image.

The field SHALL be populated on `/api/my-projects` responses and SHALL be null on
public project responses, where a viewer's entry standing has no meaning. It
SHALL be populated on the `/api/my-projects` list as well as the detail route,
whether or not the project list renders it.

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

#### Scenario: A competition is never in both lists

- **GIVEN** a project entered in an open competition
- **WHEN** its owner fetches it
- **THEN** no competition SHALL appear in both `entries` and `opportunities`

#### Scenario: A named competition carries its image

- **GIVEN** a competition with an image, named in a project's entries or
  opportunities
- **WHEN** its owner fetches the project from `/api/my-projects`
- **THEN** that competition SHALL carry `image_url`

#### Scenario: A competition without an image reports null

- **GIVEN** a competition with no image, named in a project's standing
- **WHEN** its owner fetches the project
- **THEN** that competition's `image_url` SHALL be null

#### Scenario: Blocked opportunity names the competition in the way

- **GIVEN** a project entered in a `monthly` competition
- **WHEN** a different `monthly` competition has
  `status = ACCEPTING_APPLICATIONS` and its owner fetches the project
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

The web UI SHALL render a project's competitions in the **Settings** tab of the
project page's edit mode at `/my-projects/[id]`, as a section driven by
`competition_standing` with no eligibility logic of its own. The section SHALL
show:

- **Rounds entered** — one row per `entries` item, naming the competition and
  linking to its page, with the date entered and the competition's current
  status, marking any the project won.
- **Other rounds open now** — one row per `opportunities` item, naming the
  competition and its submission deadline. An eligible row SHALL carry an
  **Enter** control that names the competition; an ineligible row SHALL state its
  reason in place of the control. The heading SHALL say *other*, because rounds
  the project is already in are listed above and never here.

The section SHALL NOT be rendered outside the tabbed layout, and SHALL NOT be
rendered in preview mode, which shows the public view of the project.

A community tipoff SHALL NOT show the section at all. It can never enter a
competition, so listing rounds and explaining why each is out of reach is noise
on a page about somebody else's project.

Where an ineligibility reason applies to the project as a whole rather than to
one competition — `project_status`, `project_draft` — the UI SHALL state it once
rather than repeating it on every row, and SHALL offer no entry control.

Where there are no opportunities, the section SHALL say so in terms of what the
project is already in:

- with entries — that no *other* round is open.
- with no entries — that no round is currently open, and that the project can
  enter the next one.

Where an entry request fails, the UI SHALL show the error and re-fetch the
project rather than leaving a stale control on screen.

The project list at `/my-projects` SHALL NOT show a project's competitions. A
project's standing has one home, and it is the project page.

#### Scenario: Entered project lists its rounds

- **GIVEN** a project with entries in two competitions
- **WHEN** its owner opens the Settings tab on `/my-projects/[id]`
- **THEN** the section SHALL name both competitions and link to their pages
- **AND** SHALL show when the project entered each

#### Scenario: An entered open round is not repeated below

- **GIVEN** a project entered in a competition that is still open
- **WHEN** its owner opens the Settings tab
- **THEN** that competition SHALL appear once, among the rounds entered
- **AND** SHALL NOT appear among the other rounds open now

#### Scenario: In every open round, nothing else on offer

- **GIVEN** a project entered in every currently open competition
- **WHEN** its owner opens the Settings tab
- **THEN** the section SHALL state that no other round is open
- **AND** SHALL NOT state that no round is open

#### Scenario: Won competition is marked

- **GIVEN** a project that won a competition it is entered in
- **WHEN** its owner opens the Settings tab
- **THEN** that row SHALL be marked as won

#### Scenario: Each open round it can enter offers its own control

- **GIVEN** a project with eligible opportunities for two competitions
- **WHEN** its owner opens the Settings tab
- **THEN** the section SHALL show a row per competition
- **AND** each SHALL carry an Enter control naming that competition and showing
  its submission deadline

#### Scenario: A blocked open round explains itself

- **GIVEN** a project entered in a `monthly` competition, with a different open
  `monthly` competition it cannot enter
- **WHEN** its owner opens the Settings tab
- **THEN** that row SHALL appear without an Enter control
- **AND** SHALL state that the project is already in that series, naming the
  competition it is in

#### Scenario: A project-wide reason is stated once

- **GIVEN** a project with `status = REJECTED` and opportunities for two open
  competitions, both ineligible with reason `project_status`
- **WHEN** its owner opens the Settings tab
- **THEN** the section SHALL state the reason once
- **AND** SHALL NOT repeat it per competition

#### Scenario: A draft offers no entry control

- **GIVEN** a project with `status = DRAFT` and an open competition
- **WHEN** its owner opens the Settings tab
- **THEN** the section SHALL state that the project must be published first
- **AND** SHALL offer no Enter control

#### Scenario: A community tipoff shows no competitions section

- **GIVEN** a community tipoff project
- **WHEN** its tipster opens the Settings tab
- **THEN** the tab SHALL NOT show the competitions section
- **AND** SHALL show no competition messaging of any kind, whether or not a
  round is open

#### Scenario: Preview mode shows no competitions

- **GIVEN** a project with entries and open opportunities
- **WHEN** its owner switches the project page to preview
- **THEN** the page SHALL show no competitions section

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
- **WHEN** its owner opens the Settings tab
- **THEN** the section SHALL state that no round is currently open and that the
  project can enter the next one

#### Scenario: Project list shows no competitions

- **GIVEN** a project entered in a competition
- **WHEN** its owner views `/my-projects`
- **THEN** the card SHALL show nothing about competitions

### Requirement: Publishing offers entry once it has succeeded

The web UI SHALL offer competition entry immediately after a successful publish
rather than before it. Where the newly published project has at least one
eligible opportunity, the UI SHALL present the open rounds and allow the
contributor to enter one or dismiss without entering. Dismissing SHALL NOT be
recorded as a preference: the same rounds SHALL remain available from the
project page.

The offer SHALL describe what publishing actually did. Publishing submits the
project for review and does not make it live, so the UI SHALL NOT say the project
is published. It SHALL state that the project goes live once reviewed, and that
entering a round now is nevertheless effective — the project joins that round
when it is approved.

The offer SHALL be presented as a dialog in which the open rounds are a list of
choices and the actions are a single confirming control and a single dismissing
control, presented together. Each round SHALL be shown with its name, its
submission deadline and its image. Where more than one round is open the rounds
SHALL be individually selectable with the first selected; where exactly one is
open it SHALL be presented without a selection control, already chosen. No round
SHALL be entered without the confirming control being activated.

Where the published project has no eligible opportunity, the UI SHALL NOT
interrupt the publish flow.

#### Scenario: The offer says the project is under review, not live

- **GIVEN** a draft project that will have eligible opportunities once published
- **WHEN** its contributor publishes it and the request returns `200`
- **THEN** the dialog SHALL NOT describe the project as published
- **AND** SHALL state that it goes live once reviewed
- **AND** SHALL state that entering a round now takes effect on approval

#### Scenario: Publish offers the open rounds

- **GIVEN** a draft project that will have eligible opportunities once published
- **WHEN** its contributor publishes it and the request returns `200`
- **THEN** the UI SHALL present those competitions with their submission
  deadlines and images
- **AND** confirming SHALL call the competition entry endpoint with the selected
  competition's id

#### Scenario: A single open round needs no selection

- **GIVEN** a newly published project with exactly one eligible opportunity
- **WHEN** the offer is presented
- **THEN** that round SHALL be shown without a selection control
- **AND** confirming SHALL enter it

#### Scenario: Choosing between several open rounds

- **GIVEN** a newly published project with eligible opportunities for two
  competitions
- **WHEN** its contributor selects the second and confirms
- **THEN** the entry endpoint SHALL be called with the second competition's id
- **AND** the first SHALL NOT be entered

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

A competition with `status = ACCEPTING_APPLICATIONS` SHALL offer an
authenticated user a way to enter one of their existing projects without leaving
the competition page. Activating the competition's submission call to action
SHALL open a dialog rather than navigating.

The dialog SHALL report where the user already stands in this round before it
reports what they can do about it. It SHALL list the user's projects that hold an
entry in this competition, each labelled by what that project is waiting on:

- a project with `status = APPROVED` SHALL be shown as live in the round.
- a project with `status = PENDING` SHALL be shown as awaiting review, because it
  is in the round and will appear in it once approved.
- any other status SHALL be shown with that status.

Only this competition SHALL be reported this way. A project held back by an entry
in a *different* round of the same series is the project page's story, not this
dialog's.

The dialog SHALL then list the user's projects holding an eligible opportunity
for that competition, each with its title, its tagline and its image, as a list
of choices with a single confirming control and a single dismissing control
presented together. Where more than one project is listed they SHALL be
individually selectable with the first selected; where exactly one is listed it
SHALL be presented without a selection control, already chosen. Confirming SHALL
call the competition entry endpoint with the selected project and that
competition.

Projects the user owns that are not eligible for that competition SHALL NOT be
offered as choices. An unpublished draft is not eligible, so it SHALL NOT appear.

Where the user has nothing to enter, the dialog SHALL say which of these is true
rather than reporting a flat refusal:

- projects already in this round, but nothing further to enter — that nothing
  else of theirs can enter this round.
- no project in this round and none eligible — that none of their projects can
  enter this round, and why.
- no projects at all — that they have not added a project yet.

In every case where nothing can be entered, the dialog SHALL offer a route to
create a project, stating that publishing it will offer this round.

An unauthenticated user's call to action SHALL remain a link to the project
creation route, which requires them to sign in.

The dialog SHALL read the standing already carried by `GET /api/my-projects` and
SHALL NOT require an endpoint of its own. It SHALL fetch when opened rather than
when the competition page loads.

#### Scenario: The call to action opens a chooser

- **GIVEN** an authenticated user with a published project eligible for an open
  competition
- **WHEN** they activate that competition's submission call to action
- **THEN** a dialog SHALL open naming the competition
- **AND** SHALL list that project
- **AND** the page SHALL NOT navigate

#### Scenario: A project awaiting review is reported as in the round

- **GIVEN** an authenticated user whose `PENDING` project holds an entry in this
  competition
- **WHEN** they open the chooser
- **THEN** the dialog SHALL list that project as already in this round
- **AND** SHALL show it as awaiting review
- **AND** SHALL NOT say that none of their projects can enter

#### Scenario: An approved project is reported as live in the round

- **GIVEN** an authenticated user whose `APPROVED` project holds an entry in this
  competition
- **WHEN** they open the chooser
- **THEN** the dialog SHALL list that project as live in the round

#### Scenario: Already in, with nothing left to enter

- **GIVEN** an authenticated user whose only projects already hold entries in
  this competition
- **WHEN** they open the chooser
- **THEN** the dialog SHALL list those projects and their states
- **AND** SHALL state that nothing else of theirs can enter this round
- **AND** SHALL offer a route to create a project

#### Scenario: Already in, with something still to enter

- **GIVEN** an authenticated user with one project already in this round and one
  eligible for it
- **WHEN** they open the chooser
- **THEN** the dialog SHALL list the first as already in the round
- **AND** SHALL offer the second as a choice with a confirming control

#### Scenario: Entering from the competition page

- **GIVEN** an authenticated user viewing the chooser for a competition
- **WHEN** they select a project and confirm
- **THEN** the competition entry endpoint SHALL be called with that project and
  competition
- **AND** the competition page SHALL reflect the new entry

#### Scenario: Projects ineligible for this competition are not offered

- **GIVEN** an authenticated user with one project already entered in another
  round of the `monthly` series and one eligible for the open `monthly` round
- **WHEN** they open the chooser for that round
- **THEN** only the eligible project SHALL be offered as a choice

#### Scenario: An unpublished draft is not offered

- **GIVEN** an authenticated user whose only project is a `DRAFT`
- **WHEN** they open the chooser for an open competition
- **THEN** the draft SHALL NOT be offered as a choice
- **AND** the dialog SHALL offer a route to create a project

#### Scenario: A user with projects but none eligible and none entered is told why

- **GIVEN** an authenticated user with no project in this round and none eligible
  for it
- **WHEN** they open the chooser
- **THEN** the dialog SHALL state that none of their projects can enter this
  round
- **AND** SHALL offer a route to create a project

#### Scenario: A user with no projects is told so

- **GIVEN** an authenticated user with no projects
- **WHEN** they open the chooser
- **THEN** the dialog SHALL state that they have not added a project yet
- **AND** SHALL offer a route to create a project

#### Scenario: Dismissing the chooser enters nothing

- **GIVEN** an authenticated user viewing the chooser
- **WHEN** they dismiss it
- **THEN** no `CompetitionEntry` SHALL be created

#### Scenario: Anonymous visitor is sent to create a project

- **GIVEN** an unauthenticated visitor
- **WHEN** they view a competition with `status = ACCEPTING_APPLICATIONS`
- **THEN** its submission call to action SHALL link to the project creation
  route

### Requirement: Creating a project has its own route

The web UI SHALL offer project creation at `/create`, a page holding only the
form that creates a project — its URL field, its ownership choice between a
project the user made and a community tipoff, and its submit control. The page
SHALL NOT mention competitions, SHALL NOT accept a competition parameter, and
SHALL NOT enter the created project in anything. A project created there is a
draft, and entry is offered when it is published.

Every call to action that leads to project creation SHALL name that action —
"create", not "submit" — and SHALL link to `/create`.

**BREAKING**: `/submit` SHALL NOT exist. It conflated creating a project with
entering one, and the two now have separate homes.

#### Scenario: The creation page offers only creation

- **WHEN** an authenticated user opens `/create`
- **THEN** the page SHALL offer the project creation form
- **AND** SHALL show nothing about competitions

#### Scenario: Creating a project enters no competition

- **GIVEN** a competition with `status = ACCEPTING_APPLICATIONS`
- **WHEN** a user creates a project from `/create`
- **THEN** the project SHALL be a draft
- **AND** SHALL hold no `CompetitionEntry`

#### Scenario: A tipoff can still be created

- **WHEN** a user chooses the tipoff option on `/create` and submits
- **THEN** a community tipoff project SHALL be created

#### Scenario: The old submission route is gone

- **WHEN** any user requests `/submit`
- **THEN** the route SHALL NOT resolve

### Requirement: Competition entries are manageable in the Django admin

The Django admin SHALL let staff see and manage competition entries from both
sides of the relation.

`CompetitionEntry` SHALL have its own changelist listing each entry's
competition, project, `entered_at`, `entered_via` and `entered_by`, filterable
by competition, by the competition's `entry_series` and by `entered_via`, and
searchable by project title and competition name. Adding an entry there SHALL
offer autocomplete for both the competition and the project.

An entry created through the admin SHALL record `entered_via = admin` and
`entered_by` as the acting staff user. `entered_via` and `entered_by` SHALL NOT
be settable by hand, wherever an entry is created in the admin — provenance that
can be typed cannot be trusted.

A competition's change form SHALL continue to allow entries to be added and
removed inline.

A project's change form SHALL show the competitions it is entered in, read only.

#### Scenario: Listing the projects in a competition

- **GIVEN** competitions with entries
- **WHEN** a staff user filters the entry changelist by one competition
- **THEN** the list SHALL show that competition's entries and no others

#### Scenario: Listing the competitions a project is in

- **GIVEN** a project entered in two competitions
- **WHEN** a staff user searches the entry changelist by that project's title
- **THEN** both entries SHALL be listed

#### Scenario: An admin-created entry records who made it

- **WHEN** a staff user adds an entry from the changelist
- **THEN** the entry's `entered_via` SHALL be `admin`
- **AND** its `entered_by` SHALL be that staff user

#### Scenario: Provenance cannot be set by hand

- **WHEN** a staff user adds an entry from the changelist or from a
  competition's inline
- **THEN** the form SHALL NOT offer `entered_via` or `entered_by` as editable
  fields

#### Scenario: Removing a project from a competition

- **GIVEN** a competition with an entry
- **WHEN** a staff user deletes that entry
- **THEN** the project SHALL no longer be in that competition

#### Scenario: A project's change form lists its competitions

- **GIVEN** a project entered in a competition
- **WHEN** a staff user opens that project in the admin
- **THEN** the form SHALL show that competition
- **AND** SHALL NOT offer to add or remove entries there

