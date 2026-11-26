## ADDED Requirements

### Requirement: Front-page articles

An article SHALL be eligible for the front page when it is globally visible, its `published_at` has passed, it is author-owned or on an approved project, and its `recent_until` is null or still ahead. Eligible articles SHALL be ordered newest first by `approved_at`, falling back to `published_at` where `approved_at` is null.

#### Scenario: Ordered by when the article became visible
- **GIVEN** article A published on 1 Nov and approved by an admin on 10 Nov, and article B published and auto-approved on 5 Nov
- **WHEN** front-page articles are listed
- **THEN** A comes before B

#### Scenario: Editing the publish date does not move an article up
- **GIVEN** a visible article approved on 1 Nov
- **WHEN** its author edits `published_at` to today
- **THEN** its position in the front-page order is unchanged

#### Scenario: No age limit
- **GIVEN** the newest front-page article was published 20 days ago
- **WHEN** front-page articles are listed
- **THEN** it is still returned first; the card's date tells the reader its age

#### Scenario: Ineligible articles are excluded
- **WHEN** an article is pending review, demoted, on a project that is not approved, scheduled for a future `published_at`, or past its `recent_until`
- **THEN** it is not a front-page article

### Requirement: Recent articles endpoint

The system SHALL expose a public `GET /api/articles/recent?limit=N` returning front-page articles in front-page order. `limit` SHALL default to 2 and be capped. Each item SHALL carry what a card needs: id, slug, title, summary, `published_at`, its channel name, its project's slug and title or null, its author's id, name and avatar, a listing image URL sized for a card, and the listing crop.

#### Scenario: Two newest
- **GIVEN** five front-page articles
- **WHEN** a client requests `GET /api/articles/recent`
- **THEN** the two newest are returned, newest first

#### Scenario: Author-owned article
- **WHEN** a returned article is author-owned
- **THEN** its project fields are null and its author fields are set

### Requirement: Spotlight endpoint

The system SHALL expose a public `GET /api/articles/spotlight?limit=N` returning articles with `is_spotlight` set, in the same item shape and order as the recent endpoint and with the same eligibility, except that `recent_until` SHALL NOT exclude an article. `limit` SHALL default to 5.

#### Scenario: Expired notice still spotlighted
- **GIVEN** a spotlighted article whose `recent_until` has passed
- **WHEN** a client requests `GET /api/articles/spotlight`
- **THEN** the article is returned

#### Scenario: Unflagged articles are excluded
- **WHEN** an article does not have `is_spotlight` set
- **THEN** it is not returned by the spotlight endpoint

### Requirement: Recent section

The Discover view SHALL open with a Recent section. The newest front-page article is a large card on the left. The second is a card at the top right. The competition slot is below it. With one article the right column holds only the competition slot. Without a competition slot, the second article fills the right column. With no articles, the section SHALL NOT render.

#### Scenario: Full section
- **GIVEN** two front-page articles and a competition in voting
- **WHEN** a visitor loads `/projects`
- **THEN** the newest article is the large card, the second sits top right, and the competition slot sits below it

#### Scenario: No competition to show
- **GIVEN** two front-page articles and no competition for the slot
- **WHEN** the Discover view renders
- **THEN** the second article fills the right column

#### Scenario: No articles
- **WHEN** there are no front-page articles
- **THEN** the Recent section is not rendered

### Requirement: Recent section on mobile

At narrow widths the Recent section SHALL stack in the order: lead article, competition slot, second article.

#### Scenario: Stacked order
- **WHEN** the Discover view renders at a mobile width
- **THEN** the competition slot appears between the lead and the second article

### Requirement: Front-page article cards

A front-page card SHALL show the article's flag (its project's title, or its author's name for an author-owned article), date, headline, and summary where its size allows. It SHALL link to the article at its project or author URL with `?from=discover`. An article without a listing image SHALL render as a text-led card with no placeholder image.

#### Scenario: Author-owned card
- **GIVEN** an author-owned article by U in Recent
- **THEN** its flag is U's name and it links to `/users/{U.id}/articles/{slug}?from=discover`

#### Scenario: No cover image
- **GIVEN** a front-page article with no listing image
- **THEN** its card shows headline and summary with no image and no gradient placeholder

### Requirement: Competition slot

The slot SHALL show the first that applies: a competition in `voting` whose voting end date (falling back to `submission_deadline`) is today or later; one in `accepting_applications`; the most recently closed competition with a winner. Otherwise there is no slot. The whole slot SHALL link to `/competitions/{slug}`.

#### Scenario: Voting beats an open round
- **GIVEN** Grasker in `voting` until 2 Dec and Maís in `accepting_applications`, on 26 Nov
- **WHEN** the slot is chosen
- **THEN** it shows Grasker

#### Scenario: Voting left open past its end date
- **GIVEN** a competition still in `voting` whose voting end date has passed, and one in `accepting_applications`
- **WHEN** the slot is chosen
- **THEN** it shows the one accepting applications

#### Scenario: Closed without a winner
- **GIVEN** no active competition and the most recently closed one has no winner
- **WHEN** the slot is chosen
- **THEN** there is no slot

### Requirement: Competition slot states

Each state SHALL carry its own label and verb. Voting: "Voting open", days left, entries, and *Rank the entries*. Accepting: "Open for entries", days left, entries so far, prize, and *Enter your project*. Closed: "Won by" the winning project, with that project's image.

#### Scenario: Open round
- **GIVEN** the slot shows a competition accepting applications with 11 days left, 2 entries and a 50.000 ISK prize
- **THEN** it reads "Open for entries", "11 days left", "2 entered so far", shows the prize and the *Enter your project* verb

#### Scenario: Closed round
- **GIVEN** the slot shows a closed competition won by Alkóhól Listinn
- **THEN** it shows "Won by Alkóhól Listinn" with the winner's image

### Requirement: Spotlight section

Below Recent, the Discover view SHALL show an "In the spotlight" section: spotlighted articles not already shown in Recent, compared by article id, newest first, up to three. It SHALL have a heading only, with no note and no "see all" link. When none are left after removing duplicates, the section SHALL NOT render.

#### Scenario: Removing a duplicate
- **GIVEN** the newest front-page article is spotlighted, and four spotlighted articles exist in total
- **WHEN** the Discover view renders
- **THEN** that article leads Recent and the spotlight shows the other three

#### Scenario: Nothing left
- **GIVEN** the only spotlighted articles are the two in Recent
- **THEN** the spotlight section is not rendered

### Requirement: Front-page sections fail independently

If the recent, spotlight or competition-highlights request fails, the Discover view SHALL render without the part that depends on it, rather than showing the page error.

#### Scenario: Spotlight request fails
- **WHEN** `GET /api/articles/spotlight` fails while the other requests succeed
- **THEN** the page renders with Recent and the existing sections, and without the spotlight

## REMOVED Requirements

### Requirement: Featured section
**Reason**: Replaced by the Recent section and the spotlight (#102).
**Migration**: None for visitors. Admins flag articles with `is_spotlight` instead of projects with `is_featured`.

### Requirement: Featured API endpoint
**Reason**: Nothing reads it once the Featured section is gone.
**Migration**: Use `GET /api/articles/spotlight` and `GET /api/articles/recent`.
