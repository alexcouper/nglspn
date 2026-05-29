## ADDED Requirements

### Requirement: API returns ordered list of highlight competitions

The competition highlights endpoint SHALL return a list of competitions: all active competitions (status `accepting_applications` or `voting`) sorted by `start_date` descending, followed by the 1 most recently closed competition sorted by `voting_end_date` descending (falling back to `submission_deadline`).

#### Scenario: Multiple active competitions and one closed
- **WHEN** there are 2 active competitions (one accepting opened Mar 2026, one voting opened Jan 2026) and 3 closed competitions
- **THEN** the endpoint returns a list of 3: [accepting Mar, voting Jan, most recently closed]

#### Scenario: No active competitions
- **WHEN** there are no active competitions and 2 closed competitions
- **THEN** the endpoint returns a list of 1: [most recently closed]

#### Scenario: No competitions at all
- **WHEN** there are no competitions
- **THEN** the endpoint returns an empty list

#### Scenario: Active competitions only
- **WHEN** there are 2 active competitions and no closed competitions
- **THEN** the endpoint returns a list of 2: [newest active, older active]

### Requirement: Homepage renders competition highlights using HorizontalScroll

The homepage competition highlight section SHALL render competition cards inside the shared `HorizontalScroll` component (reused from the discover page). Gradient fades indicate scrollable content. With a single competition, the component naturally renders as a single card with no scroll indicators.

#### Scenario: Multiple competitions
- **WHEN** the highlights endpoint returns 3 competitions
- **THEN** the homepage displays fixed-width competition cards in a horizontally scrollable container with gradient fade indicators

#### Scenario: Single competition
- **WHEN** the highlights endpoint returns 1 competition
- **THEN** the homepage displays a single competition card with no gradient fades

#### Scenario: No competitions
- **WHEN** the highlights endpoint returns an empty list
- **THEN** the homepage displays "More competitions coming soon"

### Requirement: Carousel ordering matches API response

The carousel SHALL display competitions in the order returned by the API: active competitions first (newest to oldest), followed by the most recently closed competition.

#### Scenario: Visual ordering
- **WHEN** the API returns [Open Mar 2026, Voting Jan 2026, Closed Dec 2025]
- **THEN** the carousel displays them left-to-right in that order
