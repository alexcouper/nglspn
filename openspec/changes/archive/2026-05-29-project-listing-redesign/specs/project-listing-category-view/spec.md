## ADDED Requirements

### Requirement: Category view activated by tab selection

When a user selects a category tab, the page SHALL switch from Discover view to Category view, showing a filtered grid of projects in that category. The URL SHALL update to include the category as a search param (`/preview/projects?category={slug}`).

#### Scenario: User clicks a category tab
- **WHEN** a user clicks the "Dev Tools" tab
- **THEN** the URL updates to `/preview/projects?category=dev-tools` and the Category view renders with projects in that category

#### Scenario: User clicks back to Discover tab
- **WHEN** a user clicks the "Discover" tab while viewing a category
- **THEN** the URL updates to `/preview/projects/` (no category param) and the Discover view renders

#### Scenario: Direct URL with category param
- **WHEN** a user navigates directly to `/preview/projects?category=dev-tools`
- **THEN** the Category view renders with "Dev Tools" tab active

### Requirement: Category tabs bar

The page SHALL have a tab bar using the existing underline tab pattern, sticky below the navigation bar, showing "Discover" as the first tab followed by one tab per category that has at least one approved project. Categories with zero projects SHALL not appear as tabs.

#### Scenario: Categories with projects
- **WHEN** "Dev Tools" has projects and "Consumer Products" has projects but "Community Boosters" has none
- **THEN** tabs shown are: Discover, Dev Tools, Consumer Products (no Community Boosters tab)

#### Scenario: No categories exist
- **WHEN** no categories have been created
- **THEN** only the "Discover" tab is shown

### Requirement: Category view grid layout

The Category view SHALL display projects as an icon-led grid using `repeat(auto-fill, minmax(240px, 1fr))`. Each project card shows a 48px square project icon (or fallback), title, and 2-line tagline. The grid is designed to scale to 100+ projects within a category.

#### Scenario: Category with multiple projects
- **WHEN** a user views the "Dev Tools" category with 12 projects
- **THEN** a responsive grid of icon-led project cards is rendered with auto-fill layout

### Requirement: Category view sort options

The Category view SHALL support sorting by: Newest (approved_at descending), Name A-Z (title ascending), and Most Discussed (discussion_count descending). The default sort SHALL be Newest.

#### Scenario: Sort by name
- **WHEN** a user selects "Name A-Z" from the sort dropdown
- **THEN** the project grid re-orders alphabetically by title

#### Scenario: Sort by most discussed
- **WHEN** a user selects "Most Discussed" from the sort dropdown
- **THEN** the project grid re-orders by top-level discussion count descending

#### Scenario: Default sort is Newest
- **WHEN** a user enters a category view with no sort param
- **THEN** projects are sorted by approved_at descending

### Requirement: Category view project count

The Category view SHALL display the total number of approved projects in the selected category.

#### Scenario: Category with projects
- **WHEN** a user views the "Dev Tools" category with 15 projects
- **THEN** the view displays "15 projects" (or similar count indicator)

### Requirement: Category-filtered API endpoint

The system SHALL expose `GET /api/projects/by-category/{slug}` returning approved projects in a given category, with support for sort parameter. The endpoint SHALL accept `sort` as a query param with values: `newest` (default), `name`, `most-discussed`. When sorted by most-discussed, the response SHALL include discussion_count annotation.

#### Scenario: Fetch projects by category sorted by newest
- **WHEN** a client requests `GET /api/projects/by-category/dev-tools`
- **THEN** the system returns approved projects with category slug "dev-tools", ordered by approved_at descending

#### Scenario: Fetch projects by category sorted by most discussed
- **WHEN** a client requests `GET /api/projects/by-category/dev-tools?sort=most-discussed`
- **THEN** the system returns approved projects in that category annotated with discussion_count, ordered by discussion_count descending

#### Scenario: Category slug not found
- **WHEN** a client requests `GET /api/projects/by-category/nonexistent`
- **THEN** the system returns 404
