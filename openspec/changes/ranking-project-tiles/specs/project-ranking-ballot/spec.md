## ADDED Requirements

### Requirement: Ballot cards present a project as fully as the listing does

A project on the reviewer's ballot SHALL be presented with the same card rendering used on the project listing page: the image above, and below it the category label, the title, and the tagline. The title SHALL wrap to at most 2 lines and the tagline to at most 2 lines; neither SHALL be truncated to a single line. This applies identically to cards in the ranked list and cards in the unranked pool.

A reviewer is being asked to judge these projects against one another, so the ballot SHALL NOT show less about a project than a visitor browsing the listing page sees.

#### Scenario: Project title fits on one line
- **WHEN** a reviewer views a project on their ballot whose title fits the card width
- **THEN** the full title is shown on one line

#### Scenario: Project title needs two lines
- **WHEN** a reviewer views a project on their ballot whose title does not fit the card width
- **THEN** the title wraps onto a second line rather than being cut off with an ellipsis

#### Scenario: Tagline shown on a narrow screen
- **WHEN** a reviewer views their ballot on a narrow screen
- **THEN** the tagline is given the full width of the card, wrapping to up to 2 lines

#### Scenario: Project has a category
- **WHEN** a project on the ballot belongs to a category
- **THEN** the card shows that category's name above the title, as the listing card does

#### Scenario: Project has no category
- **WHEN** a project on the ballot belongs to no category
- **THEN** no category label is rendered and the title takes its place

#### Scenario: Project has no image
- **WHEN** a project on the ballot has no image resolvable for the card
- **THEN** a gradient placeholder is rendered in the image area

### Requirement: Ranking controls sit beside the project card

The rank number and the controls that act on a ranked entry — reorder up, reorder down, drag to reorder, and remove — SHALL be presented in a column beside the project card rather than inside it. The pool card's add action SHALL occupy the same position. The card itself SHALL remain a single link to the project's page, so that no control is nested inside that link.

#### Scenario: Reviewer opens a project from their ballot
- **WHEN** a reviewer activates the card area of a ranked or pool entry
- **THEN** they are taken to that project's page

#### Scenario: Reviewer reorders without navigating
- **WHEN** a reviewer activates the up, down, drag, remove, or add control
- **THEN** the ballot changes accordingly and the reviewer is not navigated away from the ballot

#### Scenario: Rank number is visible alongside the card
- **WHEN** a reviewer views a ranked entry
- **THEN** its current rank number is shown in the control column beside the card

### Requirement: A closed ballot is visibly inert

When a reviewer's ballot is submitted or the review period has ended, its cards SHALL be rendered in a dimmed, non-interactive treatment that distinguishes them from an editable ballot, while still showing the same category, title and tagline in full.

#### Scenario: Reviewer views a submitted ballot
- **WHEN** a reviewer views a ballot they have already submitted
- **THEN** the cards are dimmed, no reorder or remove controls are offered, and the title and tagline are still shown in full

#### Scenario: Reviewer views a ballot after voting ended
- **WHEN** a reviewer views their ballot after the review period has ended
- **THEN** the cards are dimmed and no reorder or remove controls are offered
