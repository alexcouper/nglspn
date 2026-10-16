## ADDED Requirements

### Requirement: A public profile exists for every ordinary account

`GET /api/users/{id}` SHALL return the public profile of an active, non-system user: `id`, `first_name`, `last_name`, `info`, `is_system_user`, `avatar_url` (null when no avatar is set) and `created_at`. It SHALL return 404 for an unknown id, for a user with `is_active = False`, and for a user with `is_system_user = True`. Private fields (email, kennitala, notification settings, opt-ins, groups) SHALL NOT appear in the response.

#### Scenario: Active user has a profile
- **WHEN** an unauthenticated client requests `/api/users/{id}` for an active, non-system user
- **THEN** the response is 200 with the public fields above and none of the private ones

#### Scenario: Inactive account has no profile
- **WHEN** a client requests `/api/users/{id}` for a user whose `is_active` is false
- **THEN** the response is 404

#### Scenario: System user has no profile
- **WHEN** a client requests `/api/users/{id}` for the community seed user or any other `is_system_user`
- **THEN** the response is 404

### Requirement: A user's public projects are listed with their role

`GET /api/users/{id}/projects` SHALL return, for a user who has a public profile, every project on which the user has a `ProjectContributor` row and whose status is `approved`. Each item SHALL carry `id`, `slug`, `title`, `tagline`, `category_name`, `main_image_thumb_url` (null when the project has no uploaded image) and `role`, one of `owner` or `tipster`. Items SHALL be ordered with `owner` rows first, then by the project's `published_at` descending. Projects in any other status SHALL NOT appear, regardless of who is asking. The endpoint SHALL return 404 under the same conditions as the profile itself.

#### Scenario: Owned and tipped-off projects appear with the right role
- **WHEN** a user is an `owner` contributor on an approved project A and a `tipster` on an approved project B
- **THEN** the list contains A with `role = "owner"` before B with `role = "tipster"`

#### Scenario: Unapproved projects are absent
- **WHEN** a user is a contributor on projects in `draft`, `pending`, `rejected` and `ice_box`
- **THEN** none of them appears, even when the requester is that user

#### Scenario: Thumbnail follows the project's main image
- **WHEN** a listed project has an uploaded main image with a thumb variant
- **THEN** `main_image_thumb_url` is that variant's URL; a project with no uploaded image has `null`

#### Scenario: No profile, no list
- **WHEN** the id belongs to a system user, an inactive user, or nobody
- **THEN** the response is 404

### Requirement: A user's published articles are listed with their project

`GET /api/users/{id}/articles` SHALL return, for a user who has a public profile, every article whose `author` is the user, which is globally visible (`published` with `global_visibility` in the visible states), and whose project is `approved`. Each item SHALL carry the public `ArticleListItem` fields (`id`, `title`, `summary`, `slug`, `published_at`, `channel`, `listing_image_url`, `listing_crop`) plus `project` with `slug` and `title`. Items SHALL be ordered by `published_at` descending. Drafts, articles pending review, demoted articles and articles on unapproved projects SHALL NOT appear, regardless of who is asking.

#### Scenario: Visible articles are listed newest first
- **WHEN** a user has authored two globally visible articles on approved projects
- **THEN** both appear, the more recently published one first, each naming its project

#### Scenario: Hidden articles are absent
- **WHEN** a user has authored a draft, an article with `global_visibility = pending`, and an article with `global_visibility = demoted`
- **THEN** none of them appears, even when the requester is the author

#### Scenario: Articles on unapproved projects are absent
- **WHEN** a user has a globally visible article on a project whose status is `ice_box`
- **THEN** it does not appear

### Requirement: The public profile page shows who the person is and what they have done

The page at `/users/{id}` SHALL render, from the three endpoints above: the avatar (or initials), the person's display name, a line reading "Joined <month year>" with the project and article counts, the About markdown, a Projects section rendered as project tiles each carrying the role label ("Owner" or "Tipped off") and the category, and an Articles section rendered as article cards each naming the project and channel and linking to the article. Each section SHALL show its own loading state until its request returns, and an empty section SHALL say so in one line rather than disappear. A 404 from the profile request SHALL render a "User not found" page and SHALL NOT request the lists.

#### Scenario: Full profile
- **WHEN** a visitor opens the profile of a user with an avatar, an About text, two approved projects and one visible article
- **THEN** the header shows the avatar and name, the About card shows the rendered markdown, the Projects section shows two tiles with role labels, and the Articles section shows one card linking to `/projects/{slug}/articles/{articleSlug}`

#### Scenario: Empty sections
- **WHEN** a visitor opens the profile of a user with no projects and no articles
- **THEN** each section renders a single line saying there is nothing yet, and the header counts read 0

#### Scenario: Unknown user
- **WHEN** a visitor opens `/users/{id}` for an id the API answers 404 to
- **THEN** the page shows "User not found" and makes no request for projects or articles

#### Scenario: Phone layout
- **WHEN** the page is rendered at a 390 px viewport
- **THEN** the project tiles lay out in two columns, the article cards stack, and no horizontal scrolling is needed

### Requirement: About markdown renders without images or raw HTML

The About text SHALL be rendered as markdown on the public page with `img` elements disallowed. Raw HTML SHALL NOT be rendered. Paragraphs, emphasis, lists and links SHALL render.

#### Scenario: Image markdown is dropped
- **WHEN** a user's `info` contains `![x](https://example.com/a.png)` and a paragraph
- **THEN** the paragraph renders and no `img` element is present

#### Scenario: Links render
- **WHEN** a user's `info` contains `[site](https://example.is)`
- **THEN** an anchor to `https://example.is` is rendered

### Requirement: The owner can reach the edit page from their own profile

When the authenticated user's id equals the profile's id, the header SHALL show an "Edit profile" control linking to `/profile`. It SHALL NOT be shown to anyone else, including when nobody is logged in.

#### Scenario: Own profile
- **WHEN** a logged-in user opens `/users/{their own id}`
- **THEN** "Edit profile" is present and leads to `/profile`

#### Scenario: Someone else's profile
- **WHEN** a logged-in user opens another user's profile, or a visitor opens any profile
- **THEN** no "Edit profile" control is rendered

### Requirement: `/profile` edits the public fields and nothing else

The page at `/profile` SHALL require authentication and SHALL present: the avatar with upload and remove controls, first name, last name, and the About text with a Write/Preview switch whose Preview renders the same markdown the public page does. Save SHALL send the three text fields in one `PUT /api/auth/me` and, on success, navigate to `/users/{me}`. Cancel SHALL navigate to `/users/{me}` without saving. The page SHALL keep the existing rule that a save leaving both names empty is rejected before the request is made, with a visible error. The page SHALL NOT contain the account settings, and the previous Edit/Preview page toggle SHALL be removed.

#### Scenario: Save returns to the public page
- **WHEN** a user edits their About text and presses Save
- **THEN** `PUT /api/auth/me` is called with `first_name`, `last_name` and `info`, and the browser navigates to `/users/{their id}` where the new text is shown

#### Scenario: Cancel discards
- **WHEN** a user edits a field and presses Cancel
- **THEN** no request is made and the browser navigates to `/users/{their id}`

#### Scenario: Both names cleared
- **WHEN** a user clears both name fields and presses Save
- **THEN** an error is shown and no request is made

#### Scenario: Preview matches the public rendering
- **WHEN** a user switches the About field to Preview
- **THEN** the markdown renders with the same component and options as the public page, images excluded

#### Scenario: Unauthenticated visitor
- **WHEN** a visitor who is not logged in opens `/profile`
- **THEN** they are redirected to the login page, as other authenticated routes do

### Requirement: Account settings live at `/profile/settings`

The promotions opt-in and the discussion and article email cadence controls SHALL be served at `/profile/settings`, behaving as they do today. The edit page SHALL link to it, and the user menu SHALL gain a "Settings" entry pointing at it. `/profile` SHALL no longer render these controls.

#### Scenario: Settings page works standalone
- **WHEN** a logged-in user opens `/profile/settings` and changes the article email cadence
- **THEN** the change is saved via `PUT /api/auth/me` and reflected on reload

#### Scenario: Reachable from the menu and the edit page
- **WHEN** a logged-in user opens the user menu, or the edit page
- **THEN** each offers a link to `/profile/settings`

#### Scenario: Not on the edit page
- **WHEN** a user opens `/profile`
- **THEN** no cadence or opt-in control is rendered
