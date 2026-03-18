## ADDED Requirements

### Requirement: complete-profile onboarding step registered in step registry
The onboarding step registry SHALL include a `complete-profile` step. The step's check function SHALL return `True` (complete) when the user has either a non-empty `first_name` or a non-empty `last_name` (after stripping whitespace). The step's priority SHALL be higher than `verify-email` (i.e., a higher number so it appears after email verification).

#### Scenario: User with no names sees the step
- **WHEN** a user has `first_name = ""` and `last_name = ""`
- **THEN** the `complete-profile` step SHALL appear in their pending onboarding steps

#### Scenario: User with first name only is complete
- **WHEN** a user has `first_name = "Jane"` and `last_name = ""`
- **THEN** the `complete-profile` step SHALL NOT appear in their pending onboarding steps

#### Scenario: User with last name only is complete
- **WHEN** a user has `first_name = ""` and `last_name = "Doe"`
- **THEN** the `complete-profile` step SHALL NOT appear in their pending onboarding steps

#### Scenario: User with both names is complete
- **WHEN** a user has `first_name = "Jane"` and `last_name = "Doe"`
- **THEN** the `complete-profile` step SHALL NOT appear in their pending onboarding steps

#### Scenario: Whitespace-only names are treated as empty
- **WHEN** a user has `first_name = "  "` and `last_name = ""`
- **THEN** the `complete-profile` step SHALL appear in their pending onboarding steps

#### Scenario: Step ordered after email verification
- **WHEN** a user has both `verify-email` and `complete-profile` as pending steps
- **THEN** `verify-email` SHALL appear before `complete-profile` in the pending steps list

### Requirement: CompleteProfileStep frontend component
The frontend step component registry SHALL include a `complete-profile` mapping to a `CompleteProfileStep` component. The component SHALL render first name and last name input fields. Both fields SHALL be presented but at least one must be non-empty to submit. The form SHALL submit to `PUT /api/auth/me`. On success, the component SHALL call `onComplete` to advance through the onboarding flow.

#### Scenario: Successful profile completion
- **WHEN** a user fills in at least one name field and submits
- **THEN** the component SHALL save via `PUT /api/auth/me` and call `onComplete`

#### Scenario: Both fields empty rejected
- **WHEN** a user submits the form with both fields empty or whitespace-only
- **THEN** the form SHALL display a validation error and NOT submit

#### Scenario: Component renders in onboarding page
- **WHEN** the onboarding page receives `complete-profile` as the current step
- **THEN** it SHALL render the `CompleteProfileStep` component

### Requirement: Profile save endpoint validates at least one name
The `PUT /api/auth/me` endpoint SHALL validate that after saving, the user has at least one non-empty name (first_name or last_name, after stripping whitespace). If the update would result in both names being empty, the endpoint SHALL return a 400 error.

#### Scenario: Saving with at least one name succeeds
- **WHEN** a user calls `PUT /api/auth/me` with `first_name = "Jane"` and `last_name = ""`
- **THEN** the endpoint SHALL save successfully

#### Scenario: Clearing all names rejected
- **WHEN** a user who has `first_name = "Jane"` calls `PUT /api/auth/me` with `first_name = ""` and `last_name = ""`
- **THEN** the endpoint SHALL return 400

#### Scenario: Partial updates without names unaffected
- **WHEN** a user who has `first_name = "Jane"` calls `PUT /api/auth/me` with only `notification_frequency` changed
- **THEN** the endpoint SHALL save successfully (existing names are preserved)

### Requirement: Profile edit page enforces mandatory names
The existing profile edit page SHALL make first_name and last_name fields visible and SHALL prevent saving if both would be empty. The form SHALL show a validation error when a save would leave the user with no name.

#### Scenario: Clearing both names shows validation error
- **WHEN** a user clears both first name and last name on the profile edit page and attempts to save
- **THEN** the form SHALL display a validation error

#### Scenario: Keeping at least one name allows save
- **WHEN** a user has `first_name = "Jane"` and clears `last_name`
- **THEN** the form SHALL allow saving
