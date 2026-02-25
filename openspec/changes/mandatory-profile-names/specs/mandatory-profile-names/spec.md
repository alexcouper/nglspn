## ADDED Requirements

### Requirement: User model has profile_action_required flag
The User model SHALL have a `profile_action_required` boolean field. New users SHALL be created with `profile_action_required = True`. The field SHALL be included in the `UserResponse` API schema.

#### Scenario: New user registration
- **WHEN** a new user registers
- **THEN** their `profile_action_required` field SHALL be `True`

#### Scenario: Field available in API responses
- **WHEN** the client calls `GET /api/auth/me`
- **THEN** the response SHALL include `profile_action_required` as a boolean field

### Requirement: Login response includes profile_action_required
The login API response SHALL include `profile_action_required` alongside `is_verified` so the frontend can route without an extra API call.

#### Scenario: Login with incomplete profile
- **WHEN** a user with `profile_action_required = True` logs in successfully
- **THEN** the token response SHALL include `profile_action_required: true`

#### Scenario: Login with complete profile
- **WHEN** a user with `profile_action_required = False` logs in successfully
- **THEN** the token response SHALL include `profile_action_required: false`

### Requirement: Frontend redirects users with profile_action_required to complete-profile
The `getPostAuthDestination` function SHALL check `profile_action_required` after the `is_verified` gate. When true, it SHALL redirect to `/complete-profile`, preserving the `next` parameter.

#### Scenario: Redirect after login
- **WHEN** a user with `profile_action_required = True` and `is_verified = True` logs in
- **THEN** the frontend SHALL redirect to `/complete-profile`

#### Scenario: Redirect preserves next parameter
- **WHEN** a user with `profile_action_required = True` logs in with `next=/projects/123`
- **THEN** the frontend SHALL redirect to `/complete-profile?next=%2Fprojects%2F123`

#### Scenario: No redirect when profile is complete
- **WHEN** a user with `profile_action_required = False` and `is_verified = True` logs in
- **THEN** the frontend SHALL redirect to the `next` destination or `/my-projects`

### Requirement: Complete-profile page collects first and last name
The `/complete-profile` page SHALL display a form with first name and last name fields. Both fields SHALL be required. The form SHALL submit to `PUT /api/auth/me`. On success, the page SHALL redirect to the `next` parameter or `/my-projects`.

#### Scenario: Successful profile completion
- **WHEN** a user fills in both first name and last name and submits
- **THEN** the system SHALL save the names via `PUT /api/auth/me` and redirect to the destination

#### Scenario: Empty fields rejected
- **WHEN** a user submits the form with either field empty or whitespace-only
- **THEN** the form SHALL display a validation error and NOT submit

#### Scenario: Page requires authentication
- **WHEN** an unauthenticated user navigates to `/complete-profile`
- **THEN** they SHALL be redirected to the login page

### Requirement: Profile save clears profile_action_required when requirements are met
The `PUT /api/auth/me` endpoint SHALL evaluate after saving whether `profile_action_required` should remain set. If `first_name` and `last_name` are both non-empty (after stripping whitespace), the endpoint SHALL set `profile_action_required = False`.

#### Scenario: Flag cleared on valid name save
- **WHEN** a user with `profile_action_required = True` saves a profile with `first_name = "Jane"` and `last_name = "Doe"`
- **THEN** `profile_action_required` SHALL be set to `False`

#### Scenario: Flag remains when names still empty
- **WHEN** a user with `profile_action_required = True` saves a profile update that only changes email preferences (names remain empty)
- **THEN** `profile_action_required` SHALL remain `True`

#### Scenario: Flag re-evaluated on every save
- **WHEN** a user saves their profile with `first_name = " "` (whitespace only) and `last_name = "Doe"`
- **THEN** `profile_action_required` SHALL remain `True`

### Requirement: Mandatory name validation when profile_action_required is set
When `profile_action_required` is `True`, the `PUT /api/auth/me` endpoint SHALL require both `first_name` and `last_name` to be present and non-empty in the request. The endpoint SHALL return a 400 error if either is missing or blank.

#### Scenario: Missing names rejected
- **WHEN** a user with `profile_action_required = True` calls `PUT /api/auth/me` without `first_name` or `last_name`
- **THEN** the endpoint SHALL return 400 with an error message

#### Scenario: Normal profile updates unaffected
- **WHEN** a user with `profile_action_required = False` calls `PUT /api/auth/me` with only `notification_frequency` changed
- **THEN** the endpoint SHALL save successfully without requiring names

### Requirement: Data migration flags existing users with missing names
A Django data migration SHALL set `profile_action_required = True` for all existing users where `first_name` is empty OR `last_name` is empty. Users who already have both names SHALL get `profile_action_required = False`.

#### Scenario: User with no names gets flagged
- **WHEN** the migration runs and a user has `first_name = ""` and `last_name = ""`
- **THEN** `profile_action_required` SHALL be set to `True`

#### Scenario: User with both names is not flagged
- **WHEN** the migration runs and a user has `first_name = "Jane"` and `last_name = "Doe"`
- **THEN** `profile_action_required` SHALL be set to `False`

#### Scenario: User with partial names gets flagged
- **WHEN** the migration runs and a user has `first_name = "Jane"` and `last_name = ""`
- **THEN** `profile_action_required` SHALL be set to `True`

### Requirement: Profile edit page enforces mandatory names
The existing profile edit page SHALL make first_name and last_name required fields in the form. The save button SHALL be disabled or the form SHALL show validation errors if either field is empty.

#### Scenario: Empty name fields show validation errors
- **WHEN** a user clears their first name on the profile edit page and attempts to save
- **THEN** the form SHALL display a validation error for the first name field

#### Scenario: Existing names cannot be removed
- **WHEN** a user with `first_name = "Jane"` tries to save with `first_name = ""`
- **THEN** the form SHALL prevent submission and show a validation error
