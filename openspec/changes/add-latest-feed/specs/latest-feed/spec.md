## ADDED Requirements

### Requirement: Latest tab and route

The system SHALL provide a Latest view at `/latest`, reachable as the first tab
in the sticky tab bar shared with `/projects`. Discover SHALL remain the default
landing view: `/` continues to redirect to `/projects`, not to `/latest`.

#### Scenario: Visitor opens the Latest tab
- **WHEN** a visitor clicks the "Latest" tab from `/projects`
- **THEN** the browser navigates to `/latest`
- **AND** the same sticky tab bar is shown with "Latest" active

#### Scenario: Site root is unchanged
- **WHEN** a visitor loads `/`
- **THEN** they are redirected to `/projects` showing the Discover view

#### Scenario: Anonymous visitor
- **GIVEN** a visitor who is not signed in
- **WHEN** they load `/latest`
- **THEN** the feed renders in full — no entry is hidden or personalised by
  sign-in state

### Requirement: Feed entry states

Each feed entry SHALL render as one of three states, sharing a single row
component: a bare event (flag, title, date), an event with a write-up (event
flag, article headline, listing image, standfirst), or a standalone article
(channel name as flag, then as above).

A bare event SHALL link to the project or competition it concerns. An entry
carrying an article SHALL link to that article.

#### Scenario: Bare event with no write-up
- **GIVEN** a competition whose winner has been announced and no article about it
- **WHEN** the feed renders that entry
- **THEN** it shows the flag "Competition winner", the competition or project
  title, and the event date
- **AND** following the entry opens that project or competition

#### Scenario: Event carrying a write-up
- **GIVEN** a winner-announced event superseded by an article titled "How
  Broadside won Chili"
- **WHEN** the feed renders that entry
- **THEN** the flag still reads "Competition winner"
- **AND** the headline is the article's title, shown with its listing image and
  summary
- **AND** following the entry opens the article

#### Scenario: Standalone article
- **GIVEN** a published article on a project, about no platform event
- **WHEN** the feed renders that entry
- **THEN** the flag is the article's channel name
- **AND** the entry is otherwise identical in shape to a write-up entry

#### Scenario: Article without a listing image
- **GIVEN** a published article with no listing image
- **WHEN** the feed renders its entry
- **THEN** the entry renders without an image rather than with a placeholder,
  matching `ArticleCard` behaviour

### Requirement: Automatic event sources

The system SHALL append a feed event when any of the following occurs: an
article is published, a project is published, a project is recorded as a
community tipoff, or a competition opens, closes, or has its winners announced.

Appending SHALL be the only way rows enter the stream; no source writes
retroactively except the launch backfill.

#### Scenario: Article publish appends an event
- **WHEN** a contributor publishes an article
- **THEN** a feed event is appended with `occurred_at` equal to the article's
  `published_at`

#### Scenario: Project publish appends an event
- **WHEN** a project transitions to published
- **THEN** a feed event is appended and the entry renders with the flag "New
  project" and the project's category

#### Scenario: Competition milestones append events
- **WHEN** a competition opens, closes, or announces winners
- **THEN** one feed event is appended per milestone

#### Scenario: Discussion activity appends nothing
- **WHEN** a discussion thread is created or replied to
- **THEN** no feed event is appended

### Requirement: Promoted discussions

An administrator SHALL be able to promote a discussion thread into the feed as a
deliberate act. Promotion SHALL never happen automatically.

#### Scenario: Admin promotes a thread
- **WHEN** an administrator promotes a discussion thread
- **THEN** a feed event is appended referencing that thread
- **AND** the entry renders with the flag "Discussion" and links to the thread

#### Scenario: Promotion is reversible
- **GIVEN** a promoted discussion entry in the feed
- **WHEN** an administrator retires it
- **THEN** it no longer renders in the feed

### Requirement: Superseding

An article about a platform event SHALL supersede that event's entry rather than
adding a second entry. A superseded event SHALL be retired — excluded from
rendering but retained in the stream.

Superseding SHALL be one-shot: once an event has been superseded, a further
article referencing the same event SHALL appear as its own entry.

#### Scenario: Write-up supersedes its event
- **GIVEN** a winner-announced event in the feed
- **WHEN** an article linked to that event is published
- **THEN** the feed shows one entry, at the article's publish time, carrying the
  event's flag and the article's headline
- **AND** the original bare event no longer renders

#### Scenario: Superseded event is retained
- **GIVEN** a superseded winner-announced event
- **WHEN** an administrator inspects the stream
- **THEN** the original event row is still present and marked as superseded

#### Scenario: Second article about the same event
- **GIVEN** a winner-announced event already superseded by an article
- **WHEN** a second article linked to the same event is published
- **THEN** the second article appears as its own entry
- **AND** the first entry is unaffected

#### Scenario: Article published without an event link
- **GIVEN** a winner-announced event in the feed
- **WHEN** an article about it is published with no event link set
- **THEN** both entries render — the duplicate is visible rather than silent
- **AND** an administrator can link them afterwards, retiring the bare event

### Requirement: Append-only ordering and pagination

The feed SHALL be ordered strictly by descending `occurred_at`. An entry's
position SHALL NOT change once appended, including when the article it
references is edited.

Reads SHALL be cursor-paginated on `occurred_at`, so that paging through the
feed serves each entry exactly once.

#### Scenario: Editing an article does not move its entry
- **GIVEN** a published article whose entry sits in last week's group
- **WHEN** the author edits the article's title and body
- **THEN** the entry renders the updated title
- **AND** the entry remains in the same position

#### Scenario: Paging serves each entry once
- **GIVEN** a feed with more entries than one page
- **WHEN** a reader loads the first page and then the next
- **THEN** no entry appears on both pages and none is skipped

#### Scenario: Entries are grouped by week
- **WHEN** the feed renders
- **THEN** entries are grouped under week headers, which are the only grouping
  applied

### Requirement: Freshness-gated lead

The newest entry SHALL render as a full-width lead — listing image, headline and
summary — only when it carries an article published within the freshness window.
Otherwise the feed SHALL start flat, with no lead.

The freshness window SHALL be a single configurable value, defaulting to 7 days.

An administrator SHALL be able to pin a specific entry as the lead, overriding
the freshness rule.

#### Scenario: Recent article leads
- **GIVEN** the newest entry carries an article published 2 days ago
- **WHEN** the feed renders
- **THEN** that entry renders full width above the first week header

#### Scenario: Stale article does not lead
- **GIVEN** the newest entry carries an article published 30 days ago
- **WHEN** the feed renders
- **THEN** no lead is rendered and the feed begins with the first week header

#### Scenario: Newest entry is a bare event
- **GIVEN** the newest entry is a new-project event with no article
- **WHEN** the feed renders
- **THEN** no lead is rendered

#### Scenario: Admin pin overrides freshness
- **GIVEN** an administrator has pinned an entry
- **WHEN** the feed renders
- **THEN** the pinned entry renders as the lead regardless of its age

### Requirement: Responsive layout

The feed SHALL render as a single column on narrow viewports, with the lead card
full width and entry thumbnails kept to the left. No feed content SHALL depend on
a wide viewport to be reachable.

#### Scenario: Narrow viewport
- **WHEN** the feed is rendered at a mobile viewport width
- **THEN** every entry present on desktop is present, in one column, in the same
  order

### Requirement: Empty feed

When the stream contains no renderable entries, the feed SHALL show a short line
of text and a link to Discover.

#### Scenario: Nothing to show
- **GIVEN** a stream with no renderable entries
- **WHEN** a visitor loads `/latest`
- **THEN** a short message and a link to Discover are shown, with no empty
  section headings

### Requirement: Launch backfill

The launch backfill SHALL seed the stream from existing projects, tipoffs and
competitions using each record's original timestamp, covering their full history
with no cut-off date. Articles are out of its scope: article entries enter the
stream only through the publish path.

The backfill SHALL be idempotent — running it more than once SHALL NOT produce
duplicate entries, and a second run SHALL append only events its earlier runs
did not cover.

The backfill SHALL NOT fire any notification, in-app or email.

#### Scenario: Backfill run
- **GIVEN** existing published projects, tipoffs and competitions predating this
  change
- **WHEN** the backfill runs
- **THEN** feed events exist at those records' original timestamps
- **AND** no in-app notification and no email is generated

#### Scenario: Backfill run twice
- **GIVEN** a completed backfill run
- **WHEN** the backfill is run again with no new source records
- **THEN** the stream is unchanged — no entry is duplicated

#### Scenario: Backfill after new records appear
- **GIVEN** a completed backfill run, after which further projects were published
- **WHEN** the backfill is run again
- **THEN** events are appended only for the records not already covered

#### Scenario: Articles are not backfilled
- **GIVEN** an article published before this change shipped
- **WHEN** the backfill runs
- **THEN** no feed event is created for it
