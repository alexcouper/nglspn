## MODIFIED Requirements

### Requirement: Category tabs bar

The page SHALL have a tab bar using the existing underline tab pattern, sticky below the navigation bar, showing "Latest" as the first tab, then "Discover", followed by one tab per category that has at least one approved project. Categories with zero projects SHALL not appear as tabs.

The tab bar SHALL be shared chrome rather than being rendered by the projects page alone, so that `/latest` and `/projects` present an identical bar and moving between the two views costs one click.

#### Scenario: Categories with projects
- **WHEN** "Dev Tools" has projects and "Consumer Products" has projects but "Community Boosters" has none
- **THEN** tabs shown are: Latest, Discover, Dev Tools, Consumer Products (no Community Boosters tab)

#### Scenario: No categories exist
- **WHEN** no categories have been created
- **THEN** only the "Latest" and "Discover" tabs are shown

#### Scenario: Bar is identical across views
- **WHEN** a visitor moves between `/latest`, `/projects`, and a category view
- **THEN** the same tab bar is shown in each, with the active tab reflecting the current view
