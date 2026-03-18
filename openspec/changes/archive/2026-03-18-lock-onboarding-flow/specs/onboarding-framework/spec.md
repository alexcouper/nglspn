## ADDED Requirements

### Requirement: Authenticated route onboarding enforcement
The `useRequireAuth` hook SHALL check the authenticated user's `pending_onboarding_steps`. If the list is non-empty and the current route is not `/onboarding`, the hook SHALL redirect the user to `/onboarding`. The hook SHALL NOT redirect when the user is already on `/onboarding`.

#### Scenario: User with pending steps navigates to authenticated route
- **WHEN** a user with `pending_onboarding_steps: ["verify-email"]` navigates to `/my-projects`
- **THEN** the hook SHALL redirect the user to `/onboarding`

#### Scenario: User with pending steps is already on onboarding page
- **WHEN** a user with `pending_onboarding_steps: ["verify-email"]` is on `/onboarding`
- **THEN** the hook SHALL NOT redirect (no infinite loop)

#### Scenario: User with no pending steps navigates to authenticated route
- **WHEN** a user with `pending_onboarding_steps: []` navigates to `/my-projects`
- **THEN** the hook SHALL allow normal access without redirecting

### Requirement: Navigation hides authenticated links during onboarding
The `Navigation` component SHALL hide authenticated-only navigation links (My Projects, My Reviews, Profile) when the user has non-empty `pending_onboarding_steps`. The UserMenu (containing logout) SHALL remain visible so the user can exit their session.

#### Scenario: Navigation during onboarding
- **WHEN** an authenticated user has `pending_onboarding_steps: ["verify-email"]`
- **THEN** the Navigation SHALL NOT display links to My Projects, My Reviews, or Profile
- **AND** the Navigation SHALL display the UserMenu with logout

#### Scenario: Navigation after onboarding complete
- **WHEN** an authenticated user has `pending_onboarding_steps: []`
- **THEN** the Navigation SHALL display all authenticated links (My Projects, My Reviews) and the UserMenu

#### Scenario: Public links remain visible during onboarding
- **WHEN** an authenticated user has pending onboarding steps
- **THEN** the Navigation SHALL continue to display public links (About, Projects, Competitions)
