## ADDED Requirements

### Requirement: Admin project list with image completeness

An admin-only page at `/admin/projects` SHALL display all projects with their image completeness status. The page SHALL be accessible only to users in the ADMIN group.

#### Scenario: Admin sees project image completeness
- **WHEN** an admin visits `/admin/projects`
- **THEN** they see a table of all projects showing: project name, owner, icon status, main image status, and winner composite status (for competition winners)

#### Scenario: Image status indicators
- **WHEN** the project list renders
- **THEN** each image slot shows one of: active (has an accepted image), proposed (has a pending proposal), or missing (no image)

#### Scenario: Non-admin denied access
- **WHEN** a non-admin user attempts to visit `/admin/projects`
- **THEN** they are redirected or shown an unauthorized message

#### Scenario: Unauthenticated user denied access
- **WHEN** an unauthenticated user attempts to visit `/admin/projects`
- **THEN** they are redirected to the login page

### Requirement: Admin project list filtering

The admin project list SHALL support filtering by image completeness status to help admins find projects that need attention.

#### Scenario: Filter to projects missing images
- **WHEN** an admin applies the "missing images" filter
- **THEN** only projects that are missing at least one required image (icon or main image) are shown

#### Scenario: Filter to projects with pending proposals
- **WHEN** an admin applies the "has proposals" filter
- **THEN** only projects that have at least one proposed image pending user acceptance are shown

### Requirement: Admin per-project image management

An admin-only page at `/admin/projects/{id}` SHALL display a project's image slots with the ability to generate, view, and manage images for each purpose.

#### Scenario: Admin views project image slots
- **WHEN** an admin visits `/admin/projects/{id}`
- **THEN** they see image slots for: icon, main image, screenshots, and winner composite (if project is a competition winner), each showing the current active image, any proposed images, and a generate button

#### Scenario: Admin generates an image
- **WHEN** an admin clicks the generate button on an image slot
- **THEN** the generation dialog opens with the pre-filled prompt for that purpose

#### Scenario: Admin accepts a proposal on behalf of user
- **WHEN** an admin clicks accept on a proposed image
- **THEN** the image becomes active, following the same rules as user acceptance (previous active image for that purpose is displaced)

### Requirement: Admin link in profile dropdown

The profile dropdown menu SHALL include an "Admin" link visible only to users in the ADMIN group. This link navigates to `/admin/projects`.

#### Scenario: Admin sees admin link
- **WHEN** an admin user opens the profile dropdown
- **THEN** an "Admin" link is shown that navigates to `/admin/projects`

#### Scenario: Non-admin does not see admin link
- **WHEN** a non-admin user opens the profile dropdown
- **THEN** no admin link is shown

### Requirement: Admin API endpoints

Admin-specific API endpoints SHALL exist for querying projects with image completeness data. These endpoints SHALL only be accessible to users in the ADMIN group.

#### Scenario: Admin project list API
- **WHEN** `GET /api/admin/projects` is called by an admin user
- **THEN** the response includes all projects with image completeness data (icon status, main image status, winner composite status)

#### Scenario: Admin project detail API
- **WHEN** `GET /api/admin/projects/{id}` is called by an admin user
- **THEN** the response includes the full project data with all images grouped by purpose and status

#### Scenario: Non-admin rejected from admin API
- **WHEN** a non-admin user calls `GET /api/admin/projects`
- **THEN** a 403 Forbidden response is returned
