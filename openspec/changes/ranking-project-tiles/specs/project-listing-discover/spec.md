## MODIFIED Requirements

### Requirement: New Arrivals section

The Discover view SHALL include a New Arrivals section showing recently approved projects as a horizontal scrollable row. Projects approved within the last 30 days are shown. If fewer than 5 qualify, the system SHALL fall back to the 5 most recently approved projects. Each card SHALL be 240px wide with a 4:3 aspect ratio image (in-use screenshot or AI-generated scene), subtle bottom fade (`rgba(0,0,0,0.15)`), and below the image: indigo uppercase category label, title, and 2-line tagline on a white card surface. The title SHALL wrap to at most 2 lines rather than truncating to 1, so that a title too long for a single line stays readable. Cards in the row SHALL remain equal height regardless of how many lines any one title occupies.

#### Scenario: Enough recent projects
- **WHEN** 8 projects were approved in the last 30 days
- **THEN** the New Arrivals section shows those 8 projects as horizontally scrollable cards ordered by approved_at descending

#### Scenario: Fewer than 5 recent projects
- **WHEN** only 2 projects were approved in the last 30 days
- **THEN** the New Arrivals section shows the 5 most recently approved projects regardless of date

#### Scenario: Zero approved projects
- **WHEN** no approved projects exist at all
- **THEN** the New Arrivals section is not rendered

#### Scenario: Title too long for one line
- **WHEN** a project's title does not fit on a single line at the card's 240px width
- **THEN** the title wraps onto a second line instead of being cut off with an ellipsis

#### Scenario: One card's title wraps and its neighbours' do not
- **WHEN** one card in the row has a two-line title and the others have one-line titles
- **THEN** every card in the row is still rendered at the same height
