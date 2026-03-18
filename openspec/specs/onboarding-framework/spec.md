### Requirement: Registration service step registry
The `registration` service SHALL maintain an ordered registry of onboarding steps. Each step SHALL have a unique string identifier, a priority (determining presentation order), and a check function that accepts a User and returns whether the step is complete. Steps SHALL be evaluated dynamically against the current user state — there is no persistent record of "completed steps", only whether the user currently satisfies each check.

#### Scenario: Step registered with check function
- **WHEN** a step is registered with id `verify-email` and a check function that returns `True` when `user.is_verified` is `True`
- **THEN** the registration service includes `verify-email` in its registry and can evaluate it against any user

#### Scenario: New step added after users have onboarded
- **WHEN** a new step `accept-terms` is added to the registry with a check function
- **AND** an existing user has not satisfied that check
- **THEN** the service SHALL return `accept-terms` as a pending step for that user without affecting steps they have already satisfied

### Requirement: Registration service pending steps query
The registration service SHALL expose a method to get all pending (incomplete) onboarding steps for a given user, returned in priority order. If all steps are complete, the method SHALL return an empty list.

#### Scenario: User with all steps complete
- **WHEN** the service evaluates pending steps for a user who satisfies all registered check functions
- **THEN** it SHALL return an empty list

#### Scenario: User with some steps incomplete
- **WHEN** the service evaluates pending steps for a user who has not verified their email but has completed all other steps
- **THEN** it SHALL return only the `verify-email` step

#### Scenario: Steps returned in priority order
- **WHEN** the service evaluates pending steps for a user with multiple incomplete steps
- **THEN** the steps SHALL be returned sorted by their registered priority (lowest number first)

### Requirement: Me endpoint includes onboarding state
`GET /api/auth/me` SHALL include a `pending_onboarding_steps` field in the response. This field SHALL be a list of step identifiers (strings) representing the onboarding steps the user has not yet completed, in priority order. If the user has completed all steps, the list SHALL be empty.

#### Scenario: Verified user with no pending steps
- **WHEN** a verified user with a complete profile calls `GET /api/auth/me`
- **THEN** the response SHALL include `"pending_onboarding_steps": []`

#### Scenario: Unverified user
- **WHEN** an unverified user calls `GET /api/auth/me`
- **THEN** the response SHALL include `"pending_onboarding_steps": ["verify-email"]`

#### Scenario: Multiple pending steps
- **WHEN** a user has two incomplete onboarding steps
- **THEN** the response SHALL include both step identifiers in priority order

### Requirement: Frontend onboarding gate
After authentication (login or registration), the frontend SHALL check the user's `pending_onboarding_steps`. If the list is non-empty, the user SHALL be redirected to `/onboarding` instead of their destination. The intended destination SHALL be preserved and used after onboarding completes. This replaces the current `getPostAuthDestination` logic that only checks `is_verified`.

#### Scenario: Login with pending steps
- **WHEN** a user logs in and `pending_onboarding_steps` contains `["verify-email"]`
- **THEN** the frontend SHALL redirect to `/onboarding` with the intended destination preserved

#### Scenario: Login with no pending steps
- **WHEN** a user logs in and `pending_onboarding_steps` is empty
- **THEN** the frontend SHALL redirect to the intended destination (or `/my-projects` by default)

#### Scenario: Returning user with new pending step
- **WHEN** an existing user logs in and a new onboarding step has been added since their last login
- **AND** they do not satisfy the new step's check function
- **THEN** the frontend SHALL redirect to `/onboarding` showing only the unsatisfied step

### Requirement: Onboarding page step rendering
The `/onboarding` page SHALL render one onboarding step at a time, in the order provided by `pending_onboarding_steps`. Each step identifier SHALL map to a frontend component responsible for rendering that step's UI and handling its completion. The page SHALL NOT require modification when new steps are added — only a new component mapping is needed.

#### Scenario: Single pending step
- **WHEN** a user arrives at `/onboarding` with one pending step `verify-email`
- **THEN** the page SHALL render the verify-email component

#### Scenario: Multiple pending steps shown sequentially
- **WHEN** a user has pending steps `["verify-email", "accept-terms"]`
- **THEN** the page SHALL render `verify-email` first
- **AND** after the user completes it, the page SHALL render `accept-terms`

#### Scenario: All steps completed
- **WHEN** the user completes the final pending step on the onboarding page
- **THEN** the page SHALL redirect the user to their preserved destination (or `/my-projects`)

### Requirement: Onboarding page requires authentication
The `/onboarding` page SHALL only be accessible to authenticated users. Unauthenticated users SHALL be redirected to `/login`.

#### Scenario: Unauthenticated access
- **WHEN** an unauthenticated user navigates to `/onboarding`
- **THEN** they SHALL be redirected to `/login`

### Requirement: Email verification as onboarding step
The existing email verification flow SHALL be migrated to an onboarding step. The `verify-email` step SHALL use the existing backend verification endpoints (`POST /api/auth/verify-email`, `POST /api/auth/resend-verification`). The standalone `/verify-email` page redirect in `getPostAuthDestination` SHALL be removed in favour of the onboarding gate.

#### Scenario: Unverified user login flow
- **WHEN** an unverified user logs in
- **THEN** they SHALL be routed to `/onboarding` which renders the email verification component
- **AND** the component SHALL use the existing verify-email and resend-verification API endpoints

#### Scenario: Already verified user
- **WHEN** a verified user logs in
- **THEN** the `verify-email` step check returns complete and the step is not shown
