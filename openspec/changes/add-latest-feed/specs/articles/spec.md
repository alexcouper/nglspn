## ADDED Requirements

### Requirement: Article links to the feed event it is about

An Article SHALL be able to reference the platform event it is written about.
The reference SHALL be settable by an administrator only, and SHALL NOT be
settable through the publish API. The reference is optional.

Setting the reference hides another party's entry from a site-wide feed, which
makes it an editorial act rather than something an author performs on their own
article. An author offered the choice at publish time can — by accident or
otherwise — retire an entry that is nothing to do with them, and the API would
have to police an event id it has no way to attribute. A missed link costs one
duplicate pair in the feed, which is visible and correctable; a wrong link is
neither.

An Article with no reference is valid; it appears in the feed as a standalone
entry. Superseding behaviour is defined by the `latest-feed` capability.

#### Scenario: The publish API does not accept a reference
- **GIVEN** a draft article and a live feed event
- **WHEN** the author publishes the article
- **THEN** the article publishes with no event reference, whatever the request
  carries
- **AND** the article appears in the feed as a standalone entry

#### Scenario: Publishing without a reference
- **GIVEN** a draft article about no platform event
- **WHEN** the author publishes it
- **THEN** the article publishes with no event reference and the publish is not
  blocked

#### Scenario: Administrator corrects a missed link
- **GIVEN** a published article about a winner-announced event, published with no
  reference
- **WHEN** an administrator sets the reference
- **THEN** the article's entry carries the event's flag
- **AND** the bare event entry is retired

### Requirement: Article publish appends a feed event

Publishing an Article SHALL append a feed event at the article's `published_at`.
A backdated publish SHALL append its event at the backdated timestamp.

Editing or deleting an Article after publish SHALL NOT append a further event.

#### Scenario: Publish appends
- **WHEN** a contributor publishes an article
- **THEN** exactly one feed event is appended, at the article's `published_at`

#### Scenario: Backdated publish
- **GIVEN** an author publishes an article with `published_at` set in the past
- **WHEN** the publish completes
- **THEN** the feed event is appended at that past timestamp, taking its position
  in the stream accordingly

#### Scenario: Edit appends nothing
- **GIVEN** a published article with an entry in the feed
- **WHEN** the author edits its title and body
- **THEN** no further feed event is appended

#### Scenario: Delete removes the entry
- **GIVEN** a published article with an entry in the feed
- **WHEN** the article is deleted
- **THEN** its entry no longer renders
- **AND** any event it superseded returns to rendering as a bare event
