## MODIFIED Requirements

### Requirement: Project page title banner

The project page SHALL have a title banner section containing the project name, the project's displayed owner line (described below), and the project URL or tagline as previously rendered. This replaces the current boxed layout header.

The displayed owner line SHALL be derived from the project's contributor list rather than from a single owner field. Displayed owners are contributors satisfying `role = "OWNER"` AND `full_edit = true` AND `user.is_system_user = false`.

- If one or more displayed owners exist, the line reads "by {names}" with each name linked to the owner's profile (comma-separated when multiple).
- If no displayed owners exist (i.e. the only OWNER contributors are system users), the line is omitted entirely. Other banner elements (title, tagline, URL, starred image, navigation) are unaffected.

#### Scenario: Title banner displays project info for a self-owned project

- **GIVEN** a project whose only OWNER contributor is a non-system user
- **WHEN** a user visits `/projects/{id}`
- **THEN** a title banner is shown with the project name, the owner line "by {owner name}" linked to the owner's profile, and the existing tagline / URL elements

#### Scenario: Title banner omits the owner line for a community-owned project

- **GIVEN** a project whose only OWNER contributor is the Community/Unowned system user
- **WHEN** a user visits `/projects/{id}`
- **THEN** the title banner renders the project name and the existing tagline / URL elements
- **AND** no "by ..." owner line is rendered
- **AND** the layout above the line separating title and content remains visually balanced (the absence of the owner line does not cause the banner to collapse)
