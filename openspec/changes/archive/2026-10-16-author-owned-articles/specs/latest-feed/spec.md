# Spec Delta

## MODIFIED Requirements

### Requirement: Feed entry states

Each feed entry SHALL render as one of two states, sharing a single row
component: a bare event (flag, title, date), or an article (a flag, article
headline, listing image, standfirst). The flag of an article on a project is
the project's title; the flag of an author-owned article is the author's name.

A bare event SHALL link to the project it concerns. An entry carrying an article
SHALL link to that article, at its project URL or its author URL. An article
about something the feed also carries as a bare event is a second entry;
nothing merges the two.

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

#### Scenario: Author-owned article
- **GIVEN** a published author-owned article by U
- **WHEN** the feed renders that entry
- **THEN** the flag is U's name
- **AND** following the entry opens `/users/{U.id}/articles/{slug}`

#### Scenario: Article without a listing image
- **GIVEN** a published article with no listing image
- **WHEN** the feed renders its entry
- **THEN** the entry renders without an image rather than with a placeholder,
  matching `ArticleCard` behaviour

### Requirement: Entries do not outlive their subject's visibility

An entry SHALL render only while the project it concerns is still shown on the
site. A project that leaves the approved state — rejected, iced — takes its
entry, and the entries of its articles and promoted discussions, out of the feed
with it. An author-owned article has no project to be withdrawn; its entry
renders while the article itself is globally visible.

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

#### Scenario: An author-owned article renders on its own visibility
- **GIVEN** a globally visible author-owned article with an entry in the feed
- **WHEN** the feed is read
- **THEN** its entry renders
- **AND** when an administrator demotes the article, the entry no longer renders
