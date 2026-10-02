# latest-feed Specification

## Purpose
The append-only stream of platform events rendered at `/latest`. Covers the
`FeedEvent` model and its automatic appenders (article published, project
approved, tipoff), admin promotion of a discussion, cursor paging, and the
freshness-gated lead story.

## Requirements
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

Each feed entry SHALL render as one of two states, sharing a single row
component: a bare event (flag, title, date), or an article (the article's
project as flag, article headline, listing image, standfirst).

A bare event SHALL link to the project it concerns. An entry carrying an article
SHALL link to that article. An article about something the feed also carries as
a bare event is a second entry; nothing merges the two.

#### Scenario: Bare event
- **GIVEN** an approved project
- **WHEN** the feed renders its entry
- **THEN** it shows the flag "New project", the project's title, and the event
  date
- **AND** following the entry opens that project

#### Scenario: Article
- **GIVEN** a published article on a project
- **WHEN** the feed renders that entry
- **THEN** the flag is the project's title
- **AND** the headline is the article's title, shown with its listing image and
  summary
- **AND** following the entry opens the article

#### Scenario: Article without a listing image
- **GIVEN** a published article with no listing image
- **WHEN** the feed renders its entry
- **THEN** the entry renders without an image rather than with a placeholder,
  matching `ArticleCard` behaviour

### Requirement: Automatic event sources

The system SHALL append a feed event when any of the following occurs: an
article is published, a project is published, or a project is recorded as a
community tipoff.

Competitions SHALL NOT append feed events. A competition opening, its entries
closing and its winner being announced are shown on the competition's own pages,
not in the feed.

Appending SHALL be the only way rows enter the stream; no source writes
retroactively except the launch backfill.

An entry whose `occurred_at` is still ahead — an article published with a future
`published_at` — SHALL NOT render until that time has arrived.

#### Scenario: Article publish appends an event
- **WHEN** a contributor publishes an article
- **THEN** a feed event is appended with `occurred_at` equal to the article's
  `published_at`

#### Scenario: Project publish appends an event
- **WHEN** a project transitions to published
- **THEN** a feed event is appended and the entry renders with the flag "New
  project" and the project's category

#### Scenario: Competition activity appends nothing
- **WHEN** a competition is created, passes its submission deadline, or has a
  winner assigned
- **THEN** no feed event is appended

#### Scenario: A future-dated article waits for its day
- **GIVEN** an article published with a `published_at` a fortnight away
- **WHEN** the feed is read before that time
- **THEN** the feed does not serve its entry
- **AND** `next_cursor` does not report a further page on its account

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

### Requirement: Append-only ordering and pagination

The feed SHALL be ordered strictly by descending `occurred_at`. An entry's
position SHALL NOT change once appended, including when the article it
references is edited.

Reads SHALL be cursor-paginated, so that paging through the feed serves each
entry exactly once. The cursor SHALL identify a position in the stream rather
than a point in time: a bulk approval stamps every project with one
`approved_at`, so entries can share an `occurred_at` to the microsecond, and a
cursor of `occurred_at` alone drops every entry tied with the page boundary. The
cursor SHALL be opaque to callers, who pass back what the previous response gave
them.

#### Scenario: Editing an article does not move its entry
- **GIVEN** a published article whose entry sits in last week's group
- **WHEN** the author edits the article's title and body
- **THEN** the entry renders the updated title
- **AND** the entry remains in the same position

#### Scenario: Paging serves each entry once
- **GIVEN** a feed with more entries than one page
- **WHEN** a reader loads the first page and then the next
- **THEN** no entry appears on both pages and none is skipped

#### Scenario: Entries sharing an event time survive the page boundary
- **GIVEN** three entries with the identical `occurred_at`, spanning a page
  boundary
- **WHEN** a reader pages through the feed
- **THEN** all three are served, each exactly once

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

#### Scenario: The lead is not also served as a row
- **GIVEN** an administrator has pinned an entry that sits deep in the stream
- **WHEN** a reader pages all the way past that entry's position
- **THEN** it renders once, as the lead, and not again as a row

### Requirement: Entries do not outlive their subject's visibility

An entry SHALL render only while the project it concerns is still shown on the
site. A project that leaves the approved state — rejected, iced — takes its
entry, and the entries of its articles and promoted discussions, out of the feed
with it.

Approval appends the entry and nothing withdraws it later, so the read path
checks rather than trusting the append. Without this the feed keeps publishing a
withdrawn project's title, tagline and icon, and links to a page that 404s for
everyone but its owner.

#### Scenario: Withdrawn project leaves the feed
- **GIVEN** an approved project with an entry in the feed
- **WHEN** an administrator moves it to the ice box or rejects it
- **THEN** its entry no longer renders

#### Scenario: A withdrawn project takes its articles with it
- **GIVEN** a published article whose entry leads the feed
- **WHEN** its project stops being approved
- **THEN** neither the lead nor the article's row renders

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

The launch backfill SHALL seed the stream from existing projects and tipoffs
using each record's original timestamp, covering their full history with no
cut-off date. Articles are out of its scope: article entries enter the stream
only through the publish path.

The backfill SHALL be idempotent — running it more than once SHALL NOT produce
duplicate entries, and a second run SHALL append only events its earlier runs
did not cover.

The backfill SHALL NOT fire any notification, in-app or email.

#### Scenario: Backfill run
- **GIVEN** existing published projects and tipoffs predating this change
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

