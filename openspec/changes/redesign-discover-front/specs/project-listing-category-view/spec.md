## MODIFIED Requirements

### Requirement: Category tabs bar

The page SHALL have a tab bar using the existing underline tab pattern, sticky below the navigation bar, showing "Discover" as the first tab, followed by one tab per category that has at least one approved project. Categories with zero projects SHALL not appear as tabs.

#### Scenario: Categories with projects
- **WHEN** "Dev Tools" has projects and "Consumer Products" has projects but "Community Boosters" has none
- **THEN** tabs shown are: Discover, Dev Tools, Consumer Products (no Community Boosters tab)

#### Scenario: No categories exist
- **WHEN** no categories have been created
- **THEN** only the "Discover" tab is shown

#### Scenario: Bar is identical across views
- **WHEN** a visitor moves between `/projects` and a category view
- **THEN** the same tab bar is shown in each, with the active tab reflecting the current view

#### Scenario: Retired Latest route
- **WHEN** a visitor requests `/latest`
- **THEN** they are permanently redirected to `/projects`
