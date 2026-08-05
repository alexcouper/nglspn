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

### Requirement: The ballot is laid out for comparison, not for browsing

A reviewer ranks by comparing projects against one another, so the ballot SHALL favour showing as much of it at once as the screen allows. On wide screens each entry SHALL be laid out horizontally — image beside text — so that a ballot of a dozen projects can be scanned without the reviewer losing their place. On narrow screens, where a horizontal entry cannot show the title and tagline without clipping them, each entry SHALL stack vertically instead.

Whichever layout applies, the requirement that the title and tagline are shown in full still holds. Compactness SHALL NOT be bought by clipping text.

#### Scenario: Reviewer opens a ballot on a wide screen
- **WHEN** a reviewer views a ballot of several projects on a wide screen
- **THEN** each entry is laid out horizontally
- **AND** more entries are visible at once than if each entry were stacked

#### Scenario: Reviewer opens the same ballot on a narrow screen
- **WHEN** the same reviewer views that ballot on a narrow screen
- **THEN** each entry stacks vertically so the title and tagline keep the full width of the card

#### Scenario: The entry's height is set by its content
- **WHEN** a ballot entry is laid out horizontally
- **THEN** the height of the entry is determined by the project card, not by the ranking controls beside it

### Requirement: A ranked entry is numbered on its leading edge

The rank number SHALL be positioned before the project card in reading order, so that a reviewer scanning the ranked list reads the sequence down its leading edge rather than past each entry's content.

#### Scenario: Reviewer scans their ranked list
- **WHEN** a reviewer views a ballot with several ranked projects
- **THEN** each entry's rank number appears before that entry's card
- **AND** the numbers read in order down the leading edge of the list

### Requirement: Ranking controls are placed by purpose, never inside the card's link

The controls that act on a ballot entry SHALL be placed according to what each one does: the rank number before the card, the reorder controls after it, and the remove action in the card's own top corner. The pool card's add action SHALL occupy the position the reorder controls take.

No control SHALL be a descendant of the card's link, whatever its visual position. A control drawn over the card SHALL still sit outside that link in the document, so that the card remains a single link to the project's page and keyboard users are not trapped on it.

#### Scenario: Reviewer opens a project from their ballot
- **WHEN** a reviewer activates the card area of a ranked or pool entry
- **THEN** they are taken to that project's page

#### Scenario: Reviewer reorders without navigating
- **WHEN** a reviewer activates the up, down, drag, remove, or add control
- **THEN** the ballot changes accordingly and the reviewer is not navigated away from the ballot

#### Scenario: Rank number is visible alongside the card
- **WHEN** a reviewer views a ranked entry
- **THEN** its current rank number is shown beside the card

#### Scenario: A control drawn over the card
- **WHEN** a control is positioned over the project card, such as the remove action in its corner
- **THEN** that control is still not a descendant of the card's link
- **AND** activating it acts on the ballot without navigating to the project

### Requirement: A closed ballot is visibly inert

When a reviewer's ballot is submitted or the review period has ended, its cards SHALL be rendered in a dimmed, non-interactive treatment that distinguishes them from an editable ballot, while still showing the same category, title and tagline in full.

#### Scenario: Reviewer views a submitted ballot
- **WHEN** a reviewer views a ballot they have already submitted
- **THEN** the cards are dimmed, no reorder or remove controls are offered, and the title and tagline are still shown in full

#### Scenario: Reviewer views a ballot after voting ended
- **WHEN** a reviewer views their ballot after the review period has ended
- **THEN** the cards are dimmed and no reorder or remove controls are offered
