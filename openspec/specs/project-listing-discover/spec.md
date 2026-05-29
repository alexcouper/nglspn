# Project Listing Discover

## Purpose

Defines the Discover view of the project listing page: the default curated landing experience composed of independently loading sections (Featured, New Arrivals, Competition Winners, Most Discussed, Category Rows), their supporting API endpoints, card types, and visual design tokens.

## Requirements

### Requirement: Discover view as default project listing view

The project listing page at `/preview/projects/` SHALL default to a Discover view showing curated sections. The Discover view is active when no category search param is set. Each section SHALL only render when it has data — an empty API response for a section means that section is not rendered at all.

#### Scenario: User visits project listing with no params
- **WHEN** a user visits `/preview/projects/`
- **THEN** the Discover view is shown with all non-empty sections

#### Scenario: All sections empty except New Arrivals
- **WHEN** no projects are featured, no competitions have winners, no categories are assigned, and no projects have discussions
- **THEN** only the New Arrivals section is rendered — no empty placeholders or headings for other sections

### Requirement: Featured section

The Discover view SHALL include a Featured section showing projects where `is_featured=True`. The section SHALL only render when at least one featured project exists. The layout SHALL be a 2-column arrangement: left column contains 1 large hero card (16:9 hero banner image on top, dark navy `#0f172a` text box below with indigo category label, white title, slate tagline); right column contains 2 small stacked hero cards (16:9 hero banner with overlay text using a scrim at `rgba(15,23,42,0.35)` and bottom gradient to `rgba(15,23,42,0.8)`). The large card uses a separate text box rather than an overlay because overlays don't read well at that size on a light page.

#### Scenario: 3 featured projects exist
- **WHEN** 3 projects have `is_featured=True`
- **THEN** the Featured section renders with 1 large hero card (left) and 2 small hero cards (right)

#### Scenario: 1 featured project exists
- **WHEN** 1 project has `is_featured=True`
- **THEN** the Featured section renders with just the 1 large hero card

#### Scenario: No featured projects
- **WHEN** no projects have `is_featured=True`
- **THEN** the Featured section is not rendered at all

### Requirement: Featured API endpoint

The system SHALL expose `GET /api/projects/featured` returning approved projects with `is_featured=True`, ordered by `updated_at` descending. The response SHALL include resolved image URLs per the image fallback chain.

#### Scenario: Fetch featured projects
- **WHEN** a client requests `GET /api/projects/featured`
- **THEN** the system returns all approved featured projects with their resolved image URLs

#### Scenario: No featured projects
- **WHEN** no approved projects have `is_featured=True`
- **THEN** the system returns an empty list

### Requirement: New Arrivals section

The Discover view SHALL include a New Arrivals section showing recently approved projects as a horizontal scrollable row. Projects approved within the last 30 days are shown. If fewer than 5 qualify, the system SHALL fall back to the 5 most recently approved projects. Each card SHALL be 240px wide with a 4:3 aspect ratio image (in-use screenshot or AI-generated scene), subtle bottom fade (`rgba(0,0,0,0.15)`), and below the image: indigo uppercase category label, title, and 2-line tagline on a white card surface.

#### Scenario: Enough recent projects
- **WHEN** 8 projects were approved in the last 30 days
- **THEN** the New Arrivals section shows those 8 projects as horizontally scrollable cards ordered by approved_at descending

#### Scenario: Fewer than 5 recent projects
- **WHEN** only 2 projects were approved in the last 30 days
- **THEN** the New Arrivals section shows the 5 most recently approved projects regardless of date

#### Scenario: Zero approved projects
- **WHEN** no approved projects exist at all
- **THEN** the New Arrivals section is not rendered

### Requirement: New Arrivals API endpoint

The system SHALL expose `GET /api/projects/new-arrivals` returning recently approved projects. It SHALL apply the 30-day window with fallback to 5 most recent. Response SHALL include resolved image URLs.

#### Scenario: Fetch new arrivals
- **WHEN** a client requests `GET /api/projects/new-arrivals`
- **THEN** the system returns projects approved in the last 30 days, or the 5 most recent if fewer than 5 qualify

### Requirement: Competition Winners section

The Discover view SHALL include a Competition Winners section as a horizontal scrollable row. The section SHALL only render when at least one competition has a winner assigned. Each card SHALL be 280px wide with a 16:9 winner composite image, gold border (`#fde68a`), gold hover glow, an amber "Winner" badge pill (top-right), and below the image: title, tagline, and competition name in amber.

#### Scenario: Winners exist
- **WHEN** 2 competitions have winners assigned
- **THEN** the Competition Winners section renders with 2 winner cards showing competition details

#### Scenario: No winners
- **WHEN** no competition has a winner assigned
- **THEN** the Competition Winners section is not rendered

### Requirement: Competition Winners API endpoint

The system SHALL expose `GET /api/projects/winners` returning projects that have won competitions, with competition name and date included in the response.

#### Scenario: Fetch winners
- **WHEN** a client requests `GET /api/projects/winners`
- **THEN** the system returns winning projects with their competition details, ordered by competition end_date descending

#### Scenario: No winners
- **WHEN** no competitions have winners
- **THEN** the system returns an empty list

### Requirement: Most Discussed section

The Discover view SHALL include a Most Discussed section as a vertical list of the top 4-5 projects by discussion activity. Each item shows a 40px square icon, title, tagline, and comment count in indigo. Only top-level discussions (parent is null) SHALL be counted — replies are excluded. The section SHALL only render when at least one project has discussions.

#### Scenario: Projects with discussions
- **WHEN** several projects have top-level discussions
- **THEN** the Most Discussed section renders as a vertical list with up to 5 projects ordered by discussion count descending

#### Scenario: No discussions
- **WHEN** no projects have any discussions
- **THEN** the Most Discussed section is not rendered

### Requirement: Most Discussed API endpoint

The system SHALL expose `GET /api/projects/most-discussed` returning approved projects annotated with top-level discussion count, ordered by count descending. Only projects with count > 0 SHALL be returned. The count SHALL exclude replies (only discussions with parent=null).

#### Scenario: Fetch most discussed
- **WHEN** a client requests `GET /api/projects/most-discussed`
- **THEN** the system returns projects with discussion_count > 0, ordered by discussion_count descending

#### Scenario: No discussed projects
- **WHEN** no projects have discussions
- **THEN** the system returns an empty list

### Requirement: Category Rows in Discover view

The Discover view SHALL include a horizontal scroll row for each category that has at least one approved project assigned. Each row shows the category name as a heading, a "See all" link that navigates to that category's filtered view, and icon-led compact cards (44px square icon + title + short tagline, 200px card width). Categories with no projects SHALL not have a row. Each row shows a representative sample of projects, not all projects in the category.

#### Scenario: Categories with projects
- **WHEN** "Dev Tools" has 5 projects and "Consumer Products" has 3 projects
- **THEN** two category rows render with icon-led cards and "See all" links

#### Scenario: Category with no projects
- **WHEN** "Community Boosters" has no approved projects assigned
- **THEN** no row is rendered for "Community Boosters"

#### Scenario: No categories exist
- **WHEN** no categories have been created
- **THEN** no category rows are rendered

#### Scenario: See all link navigates to category view
- **WHEN** a user clicks "See all" on the "Dev Tools" row
- **THEN** the page switches to the Category view with the Dev Tools tab active

### Requirement: Visual design tokens

The Discover view SHALL use the existing Naglasúpan light theme with these design tokens: page background `#f8fafc` (existing `--muted`), card surfaces `#ffffff` with `1px solid #e2e8f0` border, accent colour `#6366f1` indigo (existing `--accent`) for category labels, active tabs, and links, winner accent `#fbbf24` amber. Cards SHALL have 12px border radius and hover effect of `translateY(-2px)` with shadow lift (existing patterns). Font: Inter (existing).

#### Scenario: Cards use consistent styling
- **WHEN** any card renders in the Discover view
- **THEN** it uses the specified border radius, border colour, hover effect, and font

### Requirement: Card types

The Discover view uses distinct card types per section:

| Card Type | Used In | Image | Text Treatment |
|-----------|---------|-------|----------------|
| Large hero | Featured (main) | 16:9 banner | Dark navy box below image |
| Small hero | Featured (side) | 16:9 banner | Overlay with scrim + gradient |
| Arrival card | New Arrivals | 4:3 image | Below on white card |
| Winner card | Competition Winners | 16:9 composite | Below on white, gold accent |
| Icon card | Category rows | 44px square icon | Inline next to icon |
| List item | Most Discussed | 40px square icon | Inline, with comment count |

#### Scenario: Each section uses the correct card type
- **WHEN** the Discover view renders
- **THEN** Featured uses hero cards, New Arrivals uses arrival cards, Winners uses winner cards, Category Rows uses icon cards, and Most Discussed uses list items

### Requirement: Sections load independently

Each Discover section SHALL fetch its data independently using separate API calls. Sections SHALL render as they load, with skeleton placeholders shown during loading. A failed section SHALL not prevent other sections from rendering.

#### Scenario: Progressive loading
- **WHEN** the Discover view loads and the featured endpoint responds before new-arrivals
- **THEN** the Featured section renders while New Arrivals still shows a skeleton

#### Scenario: One section fails
- **WHEN** the most-discussed endpoint returns an error
- **THEN** all other sections still render normally and the Most Discussed section is hidden
