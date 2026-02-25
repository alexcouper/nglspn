## ADDED Requirements

### Requirement: Pending Projects link in user menu
The user dropdown menu SHALL display a "Pending Projects" link for users whose `groups` include `MODERATOR`. The link SHALL NOT appear for users without the `MODERATOR` group.

#### Scenario: Moderator sees menu link
- **WHEN** a user with the `MODERATOR` group opens the user dropdown menu
- **THEN** a "Pending Projects" link is visible, pointing to `/moderation`

#### Scenario: Regular user does not see menu link
- **WHEN** a user without the `MODERATOR` group opens the user dropdown menu
- **THEN** no "Pending Projects" link is visible

### Requirement: Pending projects page
The system SHALL provide a `/moderation` page that displays all pending projects. The page SHALL require authentication and moderator group membership.

#### Scenario: Moderator views pending projects
- **WHEN** a moderator navigates to `/moderation`
- **THEN** the page displays a list of pending projects showing each project's title, owner, submission date, and main image

#### Scenario: No pending projects
- **WHEN** a moderator navigates to `/moderation` and there are no pending projects
- **THEN** the page displays an empty state message

#### Scenario: Non-moderator access
- **WHEN** a non-moderator user navigates to `/moderation`
- **THEN** the user is redirected away or shown an access denied message

### Requirement: Project status actions
Each project on the pending projects page SHALL have action controls to approve, reject, or ice-box the project. Rejection SHALL require a reason before submission.

#### Scenario: Approve a project
- **WHEN** a moderator clicks the approve action on a pending project
- **THEN** the project is approved via the API and removed from the pending list

#### Scenario: Reject a project with reason
- **WHEN** a moderator clicks the reject action and enters a rejection reason
- **THEN** the project is rejected via the API with the given reason and removed from the pending list

#### Scenario: Reject requires a reason
- **WHEN** a moderator clicks the reject action without entering a reason
- **THEN** the form requires a reason before allowing submission

#### Scenario: Ice-box a project
- **WHEN** a moderator clicks the ice-box action on a pending project
- **THEN** the project is ice-boxed via the API and removed from the pending list
