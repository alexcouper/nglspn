## ADDED Requirements

### Requirement: MODERATOR group exists
The system SHALL have a Django auth group named `MODERATOR`. The group SHALL be created via a data migration so it exists in all environments.

#### Scenario: Group available after migration
- **WHEN** the data migration has run
- **THEN** a Django auth group with name `MODERATOR` exists

### Requirement: Moderator authorization check
The system SHALL provide a reusable authorization check that verifies the authenticated user belongs to the `MODERATOR` group. Superusers SHALL pass the check regardless of group membership.

#### Scenario: Moderator group member is authorized
- **WHEN** an authenticated user who belongs to the `MODERATOR` group accesses a moderation endpoint
- **THEN** the request is allowed

#### Scenario: Superuser is authorized
- **WHEN** an authenticated superuser who does not belong to the `MODERATOR` group accesses a moderation endpoint
- **THEN** the request is allowed

#### Scenario: Regular user is denied
- **WHEN** an authenticated user who is not a superuser and does not belong to the `MODERATOR` group accesses a moderation endpoint
- **THEN** the system returns 403 Forbidden

#### Scenario: Unauthenticated request is denied
- **WHEN** an unauthenticated request accesses a moderation endpoint
- **THEN** the system returns 401 Unauthorized

### Requirement: List pending projects endpoint
The system SHALL provide `GET /api/moderation/projects` that returns all projects with status `pending`. The endpoint SHALL require moderator authorization. Results SHALL be ordered by `created_at` ascending (oldest first).

#### Scenario: Moderator lists pending projects
- **WHEN** a moderator requests `GET /api/moderation/projects`
- **THEN** the system returns all projects with status `pending`, ordered oldest first

#### Scenario: No pending projects
- **WHEN** a moderator requests `GET /api/moderation/projects` and no projects are pending
- **THEN** the system returns an empty list

### Requirement: Change project status endpoint
The system SHALL provide `POST /api/moderation/projects/{project_id}/status` that accepts a target status and optional rejection reason. The endpoint SHALL require moderator authorization.

#### Scenario: Approve a pending project
- **WHEN** a moderator sends `POST /api/moderation/projects/{id}/status` with status `approved`
- **THEN** the project status changes to `approved`, `approved_by` is set to the moderator, `approved_at` is set to the current time, an approval email is enqueued for the project owner, and web UI cache revalidation is enqueued

#### Scenario: Reject a pending project with reason
- **WHEN** a moderator sends `POST /api/moderation/projects/{id}/status` with status `rejected` and a `rejection_reason`
- **THEN** the project status changes to `rejected`, `rejection_reason` is stored, and web UI cache revalidation is enqueued

#### Scenario: Ice-box a project
- **WHEN** a moderator sends `POST /api/moderation/projects/{id}/status` with status `ice_box`
- **THEN** the project status changes to `ice_box` and web UI cache revalidation is enqueued

#### Scenario: Project not found
- **WHEN** a moderator sends a status change for a non-existent project ID
- **THEN** the system returns 404 Not Found

### Requirement: User groups exposed in current user response
The `GET /api/auth/me` endpoint SHALL include the user's group names in the response as `groups: list[str]`.

#### Scenario: Moderator user sees group membership
- **WHEN** a user belonging to the `MODERATOR` group requests `GET /api/auth/me`
- **THEN** the response includes `"groups": ["MODERATOR"]`

#### Scenario: User with no groups
- **WHEN** a user with no group memberships requests `GET /api/auth/me`
- **THEN** the response includes `"groups": []`
