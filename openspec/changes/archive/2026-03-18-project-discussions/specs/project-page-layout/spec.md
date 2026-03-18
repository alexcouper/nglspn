## ADDED Requirements

### Requirement: Project page title banner

The project page SHALL have a title banner section containing the project name, author name, and author email. This replaces the current boxed layout header.

#### Scenario: Title banner displays project info
- **WHEN** a user visits `/projects/{id}`
- **THEN** a title banner is shown with the project name, author name (linked to author profile), and author email

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
