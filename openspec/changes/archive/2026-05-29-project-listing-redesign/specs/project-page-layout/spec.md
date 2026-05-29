## ADDED Requirements

### Requirement: Project listing page with Discover and Category views

The project listing page SHALL support two views: a Discover view (default, showing curated sections) and a Category view (filtered grid per category). The active view is determined by the presence of a `category` search param. The page lives at `/preview/projects/` during staging.

#### Scenario: No category param shows Discover view
- **WHEN** a user visits `/preview/projects/`
- **THEN** the Discover view is rendered

#### Scenario: Category param shows Category view
- **WHEN** a user visits `/preview/projects?category=dev-tools`
- **THEN** the Category view is rendered for that category

### Requirement: is_featured boolean on Project

The `Project` model SHALL have an `is_featured` BooleanField with default False. This field is admin-toggled to select editor's picks for the Featured section. This field was previously removed in migration `0023` — it SHALL be re-added via a new migration (not by reversing the old one).

#### Scenario: Admin flags a project as featured
- **WHEN** an admin sets `is_featured=True` on a project
- **THEN** the project appears in the Featured section of the Discover view

#### Scenario: Default is not featured
- **WHEN** a new project is created
- **THEN** `is_featured` defaults to False

### Requirement: Competition view toggle removed

The competition view toggle on the project listing page SHALL be removed. Competition winners are surfaced as a section within the Discover view instead.

#### Scenario: No competition toggle
- **WHEN** a user visits the project listing page
- **THEN** there is no toggle to switch between "list" and "competition" view modes

## REMOVED Requirements

### Requirement: Project listing flat grid with tag filtering
**Reason**: Replaced by Discover view (curated sections) and Category view (filtered grid). The flat grid layout and tag-based filtering on the listing page are superseded by the new two-view system.
**Migration**: Existing `/projects` page is preserved during staging. New page is at `/preview/projects/`. Cutover replaces the old page entirely.
