## ADDED Requirements

### Requirement: Notifications bell with unread dot

Authenticated users SHALL see a bell icon in the top bar of the application. The bell SHALL display a small unread dot when the user has any unread notifications. The dot SHALL NOT show a count.

The dot's visibility SHALL be driven by the `has_unread` field of `GET /api/notifications/summary`, polled on tab focus and on a 30-second interval while the tab is active.

#### Scenario: User with unread notifications sees the dot
- **GIVEN** an authenticated user whose `GET /api/notifications/summary` returns `{ has_unread: true, ... }`
- **WHEN** the user is viewing any page with the top bar
- **THEN** the bell icon displays an unread dot

#### Scenario: User with no unread notifications sees a plain bell
- **GIVEN** an authenticated user whose `GET /api/notifications/summary` returns `{ has_unread: false, ... }`
- **WHEN** the user is viewing any page with the top bar
- **THEN** the bell icon displays no dot

#### Scenario: Dot updates on poll
- **GIVEN** an authenticated user is viewing the app with no unread notifications (no dot)
- **WHEN** a new notification is created for them and the next polling tick fires
- **THEN** the dot appears without a page reload

#### Scenario: Unauthenticated visitors do not see the bell
- **WHEN** an unauthenticated visitor views any page
- **THEN** the bell icon is not rendered

### Requirement: Notifications popover

Clicking the bell SHALL open a popover anchored to the bell, showing up to 5 of the user's most recent unread notification groups. The popover SHALL include a "See all" link that navigates to `/notifications`.

Each popover item SHALL display: the project image, a headline (`"<Author> started a discussion on <Project>"` for new discussions, `"<Author> and N others replied to <thread title> on <Project>"` for coalesced replies), a truncated excerpt of the latest comment body, and a relative timestamp.

Clicking a popover item SHALL navigate to the deep link for that group (see "Notification deep-link click-through").

The popover items SHALL be backed by `GET /api/notifications/groups`.

#### Scenario: Popover shows up to 5 most recent groups
- **GIVEN** an authenticated user has 8 unread notification groups
- **WHEN** they click the bell
- **THEN** the popover renders the 5 most recent groups, ordered by latest event time descending
- **AND** a "See all" link is visible

#### Scenario: Popover empty state
- **GIVEN** an authenticated user has no unread notifications
- **WHEN** they click the bell
- **THEN** the popover shows an empty state message

#### Scenario: Popover item navigates to deep link
- **WHEN** the user clicks a popover item for a group whose latest notification has comment id `c-7` on project slug `foo`
- **THEN** the user navigates to `/projects/foo?comment=c-7`

### Requirement: Notifications page (action queue)

The system SHALL provide an authenticated `/notifications` page showing the user's unread notification groups in latest-first order. For v1 this page is action-queue only — read notifications SHALL NOT appear on the page.

Each group SHALL render the same visual layout used in the popover, with the addition of a selection checkbox.

The page SHALL include:
- a "Mark selected as read" button that, when pressed, calls `POST /api/notifications/mark-thread-read` for each selected group's root discussion id
- a "Mark all as read" button that calls `POST /api/notifications/mark-thread-read` for every currently visible unread group
- an empty state when the user has no unread groups

The user dropdown menu SHALL contain a "Notifications" link to this page.

#### Scenario: Page shows unread groups
- **GIVEN** an authenticated user has 3 unread notification groups
- **WHEN** they navigate to `/notifications`
- **THEN** all 3 groups are listed in latest-first order

#### Scenario: Page does not show read groups
- **GIVEN** an authenticated user has 1 unread group and 4 read groups
- **WHEN** they navigate to `/notifications`
- **THEN** only the 1 unread group is listed

#### Scenario: Mark selected as read
- **GIVEN** the page lists 3 unread groups and the user has selected 2 of them
- **WHEN** they press "Mark selected as read"
- **THEN** the system calls `mark-thread-read` for each selected group's root discussion id
- **AND** the marked groups disappear from the list

#### Scenario: Mark all as read
- **GIVEN** the page lists 5 unread groups
- **WHEN** the user presses "Mark all as read"
- **THEN** the system calls `mark-thread-read` for every listed group
- **AND** the list shows the empty state

#### Scenario: Empty state
- **GIVEN** an authenticated user has no unread notification groups
- **WHEN** they navigate to `/notifications`
- **THEN** an empty state message is displayed and no action buttons are shown

### Requirement: New-notification toaster

When polling reveals new unread notifications since the previous poll, the system SHALL show a toaster for each newly active thread. Toaster text SHALL match the same coalesced format used in the feed.

The system SHALL debounce toasters per thread: once a toast for a given root discussion is shown, no further toast for the same thread SHALL appear within a 2-minute window.

Clicking a toaster SHALL navigate to the same deep link as the corresponding feed item.

#### Scenario: New activity shows a toaster
- **GIVEN** an authenticated user is viewing the app with no unread notifications
- **WHEN** a new notification arrives and the next polling tick fires
- **THEN** a toaster appears with the coalesced text and is dismissable

#### Scenario: Per-thread debounce
- **GIVEN** a toaster has just been shown for thread T
- **WHEN** another new notification for thread T arrives within 2 minutes
- **THEN** no additional toaster is shown for thread T

#### Scenario: Multiple threads each get a toaster
- **GIVEN** new notifications arrive for two separate threads T and U on the same poll
- **WHEN** the poll completes
- **THEN** one toaster is shown for T and one for U

#### Scenario: Toaster click navigates to deep link
- **WHEN** the user clicks a toaster representing the latest notification with comment id `c-3` on project slug `bar`
- **THEN** the user navigates to `/projects/bar?comment=c-3`

### Requirement: Notification deep-link click-through

The system SHALL accept a `?comment=<id>` query parameter on project pages. On load, when this parameter is present, the project page SHALL:

1. If a comment with the given id exists in the project's discussions, scroll it into view (UI scroll only — list ordering is unchanged) and apply a brief highlight to it.
2. Focus the appropriate reply input:
   - if the comment is a root discussion, focus that discussion's own reply input
   - if the comment is a reply, focus the reply input of its containing thread
3. Call `POST /api/notifications/mark-thread-read` with the comment's root discussion id.

If the comment id is not present (deleted, unlisted, or otherwise unavailable), the project page SHALL show a toast "This discussion is no longer available" AND SHALL still call `POST /api/notifications/mark-thread-read` with the requested comment id's root if known.

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

#### Scenario: Clicking through marks the thread read everywhere
- **GIVEN** the user has 3 unread notifications for root discussion R, including the one being clicked
- **WHEN** the user clicks through any feed/popover/toaster item for R
- **THEN** all 3 R-notifications are marked read
- **AND** the badge dot updates on the next poll (or sooner if the client refetches the summary on success)
