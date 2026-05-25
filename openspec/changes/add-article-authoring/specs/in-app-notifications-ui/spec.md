## MODIFIED Requirements

### Requirement: Notifications popover

Clicking the bell SHALL open a popover anchored to the bell, showing up to 5 of the user's most recent unread notification groups. The popover SHALL include a "See all" link that navigates to `/notifications`.

Each popover item SHALL display: the project image, a headline, an excerpt, and a relative timestamp. Headline format depends on the group's `kind`:

- For `kind = "discussion"`: `"<Author> started a discussion on <Project>"` for new discussions, `"<Author> and N others replied to <thread title> on <Project>"` for coalesced replies. Excerpt is the latest comment body.
- For `kind = "article"`: `"<Project> published <Article title> in <Channel>"`. Excerpt is the article body excerpt returned by the groups endpoint.

Clicking a popover item SHALL navigate to the deep link for that group (see "Notification deep-link click-through").

The popover items SHALL be backed by `GET /api/notifications/groups`.

#### Scenario: Popover shows up to 5 most recent groups
- **GIVEN** an authenticated user has 8 unread notification groups (mix of discussion and article)
- **WHEN** they click the bell
- **THEN** the popover renders the 5 most recent groups, ordered by latest event time descending
- **AND** a "See all" link is visible

#### Scenario: Popover empty state
- **GIVEN** an authenticated user has no unread notifications
- **WHEN** they click the bell
- **THEN** the popover shows an empty state message

#### Scenario: Popover item navigates to deep link (discussion)
- **WHEN** the user clicks a popover item for a discussion group whose latest notification has comment id `c-7` on project slug `foo`
- **THEN** the user navigates to `/projects/foo?comment=c-7`

#### Scenario: Popover item navigates to article page
- **WHEN** the user clicks a popover item for an article group whose Article has slug `spring-update` on project slug `foo`
- **THEN** the user navigates to `/projects/foo/articles/spring-update`

### Requirement: New-notification toaster

When polling reveals new unread notifications since the previous poll, the system SHALL show a toaster for each newly active group. Toaster text SHALL match the same coalesced format used in the feed (discussion or article headline as described in the Notifications popover requirement).

The system SHALL debounce toasters per group:
- For discussion groups, debounce by root discussion id (no further toast within 2 minutes).
- For article groups, debounce by Article id (no further toast within 2 minutes; in practice article notifications coalesce 1:1 per Article so this rarely triggers).

Clicking a toaster SHALL navigate to the same deep link as the corresponding feed item.

#### Scenario: New article activity shows a toaster
- **GIVEN** an authenticated user is viewing the app with no unread notifications
- **WHEN** an article notification arrives for them and the next polling tick fires
- **THEN** a toaster appears with the article headline format and is dismissable

#### Scenario: New discussion activity shows a toaster
- **GIVEN** an authenticated user is viewing the app with no unread notifications
- **WHEN** a discussion notification arrives and the next polling tick fires
- **THEN** a toaster appears with the discussion headline format and is dismissable

#### Scenario: Per-thread debounce
- **GIVEN** a toaster has just been shown for discussion thread T
- **WHEN** another new notification for thread T arrives within 2 minutes
- **THEN** no additional toaster is shown for thread T

#### Scenario: Multiple groups each get a toaster
- **GIVEN** new notifications arrive on the same poll for discussion T, discussion U, and article A
- **WHEN** the poll completes
- **THEN** one toaster is shown for each (3 total)

#### Scenario: Toaster click navigates to deep link (discussion)
- **WHEN** the user clicks a toaster representing the latest notification with comment id `c-3` on project slug `bar`
- **THEN** the user navigates to `/projects/bar?comment=c-3`

#### Scenario: Toaster click navigates to article
- **WHEN** the user clicks a toaster representing an article notification for Article slug `news` on project slug `bar`
- **THEN** the user navigates to `/projects/bar/articles/news`

### Requirement: Notification deep-link click-through

The system SHALL accept a `?comment=<id>` query parameter on project pages. On load, when this parameter is present, the project page SHALL:

1. If a comment with the given id exists in the project's discussions, scroll it into view (UI scroll only — list ordering is unchanged) and apply a brief highlight to it.
2. Focus the appropriate reply input:
   - if the comment is a root discussion, focus that discussion's own reply input
   - if the comment is a reply, focus the reply input of its containing thread
3. Call `POST /api/notifications/mark-thread-read` with the comment's root discussion id.

If the comment id is not present (deleted, unlisted, or otherwise unavailable), the project page SHALL show a toast "This discussion is no longer available" AND SHALL still call `POST /api/notifications/mark-thread-read` with the requested comment id's root if known.

For article notifications, click-through navigates to `/projects/<project-slug>/articles/<article-slug>` directly (the article render page, see `articles` capability). On the article render page the client SHALL call `POST /api/notifications/mark-thread-read` with `{"article_id": <article-id>}` once the page has loaded, so the notification clears from the user's feed.

If the article slug is unknown to the server (deleted between notification fan-out and click-through), the system SHALL respond with 404 AND the client on the parent feed SHALL still call `POST /api/notifications/mark-thread-read` with the known article id, so the stale notification clears.

Browser navigation history SHALL NOT be manipulated specially — the back button returns to the prior page (typically `/notifications`).

#### Scenario: Click-through scrolls and highlights an existing comment
- **GIVEN** comment `c-5` is a reply on project slug `proj` and is currently rendered on the page
- **WHEN** the user navigates to `/projects/proj?comment=c-5`
- **THEN** the page scrolls `c-5` into view
- **AND** `c-5` is briefly highlighted
- **AND** the reply input for `c-5`'s thread receives keyboard focus
- **AND** the system calls `mark-thread-read` for `c-5`'s root discussion id

#### Scenario: Click-through on a root discussion focuses its own reply input
- **GIVEN** comment `c-9` is a root discussion on project slug `proj`
- **WHEN** the user navigates to `/projects/proj?comment=c-9`
- **THEN** the page scrolls `c-9` into view
- **AND** the reply input belonging to `c-9` receives keyboard focus

#### Scenario: Stale comment shows a toast and clears the notification
- **GIVEN** comment `c-99` no longer exists on project slug `proj` (deleted or unlisted)
- **WHEN** the user navigates to `/projects/proj?comment=c-99`
- **THEN** a toast "This discussion is no longer available" is shown
- **AND** the system calls `mark-thread-read` for the relevant root discussion (best effort), so the notification clears from the user's feed

#### Scenario: Clicking through marks the discussion thread read everywhere
- **GIVEN** the user has 3 unread notifications for root discussion R, including the one being clicked
- **WHEN** the user clicks through any feed/popover/toaster item for R
- **THEN** all 3 R-notifications are marked read
- **AND** the badge dot updates on the next poll (or sooner if the client refetches the summary on success)

#### Scenario: Article click-through marks the article notification read
- **GIVEN** the user has 1 unread Notification for Article A with slug `news` on project slug `proj`
- **WHEN** the user clicks through any feed/popover/toaster item for A
- **THEN** the article render page loads at `/projects/proj/articles/news`
- **AND** the client calls `POST /api/notifications/mark-thread-read` with `{"article_id": <A>}`
- **AND** the A-notification is marked read

#### Scenario: Stale article notification still clears
- **GIVEN** Article A was deleted between notification creation and click-through
- **WHEN** the user clicks through an article feed item for A
- **THEN** the article page responds with 404
- **AND** the client still calls `POST /api/notifications/mark-thread-read` with `{"article_id": <A>}`
- **AND** the A-notification is marked read
