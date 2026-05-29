# Project Page Layout Specification

## Purpose

Defines the project detail page layout: the title banner (project name, contributor-derived owner line, starred image), Info/Discussions navigation and routes, the Info and Discussions views, the notification frequency setting, and the project listing page's Discover/Category views.

## Requirements

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

### Requirement: Starred image on title banner

The project's main (starred) image SHALL be rendered on the title banner, positioned with a CSS rotation to appear as a screen, extending slightly above the line separating the title section from the content area.

#### Scenario: Main image is displayed with rotation treatment
- **WHEN** a project has a main image
- **THEN** the image is rendered on the banner with a CSS rotation transform, visually overlapping the title/content boundary

#### Scenario: Project with no main image
- **WHEN** a project has no images
- **THEN** the title banner renders without an image, with no broken layout

### Requirement: Info and Discussions navigation

The project page SHALL have navigation between two views: Info and Discussions. Info is at `/projects/{id}` and Discussions is at `/projects/{id}/discussions`. Navigation links SHALL be visible on both pages.

#### Scenario: Navigation links on project info page
- **WHEN** a user visits `/projects/{id}`
- **THEN** navigation is shown with "Info" as active and a link to "Discussions"

#### Scenario: Navigation links on discussions page
- **WHEN** an authenticated user visits `/projects/{id}/discussions`
- **THEN** navigation is shown with "Discussions" as active and a link back to "Info"

### Requirement: Info view content

The Info view at `/projects/{id}` SHALL display the project description, additional images (non-main), and tags. This replaces the current boxed content layout.

#### Scenario: Info view shows description and images
- **WHEN** a user visits `/projects/{id}`
- **THEN** the project description, additional images, and tags are displayed below the title banner

### Requirement: Discussions view as separate route

Discussions SHALL live at `/projects/{id}/discussions` as a separate Next.js page. This page is dynamically rendered (not statically generated) since its content is auth-gated and dynamic.

#### Scenario: Discussions route exists
- **WHEN** an authenticated user navigates to `/projects/{id}/discussions`
- **THEN** a discussions page is rendered with the shared title banner and discussion content

#### Scenario: Discussions page shares title banner
- **WHEN** a user views the discussions page
- **THEN** the same title banner layout (project name, author, starred image) is shown as on the info page

### Requirement: Discussions view for authenticated users

When an authenticated user visits the discussions page, they SHALL see existing discussions and a form to create new ones.

#### Scenario: Authenticated user sees discussions
- **WHEN** an authenticated user visits `/projects/{id}/discussions`
- **THEN** they see a list of existing discussions with replies, and a form to post a new discussion

#### Scenario: Authenticated user creates a discussion
- **WHEN** an authenticated user submits the new discussion form with a body
- **THEN** a new discussion is created via the API and appears in the list

#### Scenario: Authenticated user replies to a discussion
- **WHEN** an authenticated user clicks reply on an existing discussion and submits a body
- **THEN** a reply is created via the API and appears under the parent discussion

### Requirement: Discussions view for unauthenticated users

When an unauthenticated user visits the discussions page, they SHALL see a prompt to sign up or log in to join the conversation. No discussion content is shown.

#### Scenario: Unauthenticated user sees sign-up prompt
- **WHEN** an unauthenticated user visits `/projects/{id}/discussions`
- **THEN** they see a message prompting them to sign up or log in, with no discussion content visible

### Requirement: Notification frequency setting in user settings UI

The user settings page SHALL include a sliding scale control for notification frequency with options: Every Time, At most every hour, At most every day, Never. The control SHALL be sticky (visible as user scrolls through settings).

#### Scenario: Notification frequency slider displays current value
- **WHEN** a user visits their settings page and their `notification_frequency` is HOURLY
- **THEN** the slider is positioned at "At most every hour"

#### Scenario: User changes notification frequency
- **WHEN** a user moves the slider to "At most every day"
- **THEN** the API is called to update `notification_frequency` to DAILY and the slider reflects the new position

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
