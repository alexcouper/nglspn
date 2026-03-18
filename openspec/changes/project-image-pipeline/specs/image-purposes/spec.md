## ADDED Requirements

### Requirement: Project images have a purpose

Each `ProjectImage` SHALL have a `purpose` field with one of: `icon`, `screenshot`, `main_image`, `winner_composite`. The default purpose SHALL be `screenshot`. A project MAY have multiple images of the same purpose (e.g. multiple screenshots), except `icon` and `main_image` which SHALL have at most one `active` image per project.

#### Scenario: New image defaults to screenshot purpose
- **WHEN** a user uploads a new image to their project
- **THEN** the image is created with `purpose=screenshot`

#### Scenario: Only one active icon per project
- **WHEN** a new icon image is accepted for a project that already has an active icon
- **THEN** the previous icon's `approval_status` is set to `proposed` and the new icon becomes `active`

#### Scenario: Only one active main image per project
- **WHEN** a new main image is accepted for a project that already has an active main image
- **THEN** the previous main image's `approval_status` is set to `proposed` and the new one becomes `active`

### Requirement: Project images have an approval status

Each `ProjectImage` SHALL have an `approval_status` field with one of: `active`, `proposed`. The default SHALL be `active`. User-uploaded images are immediately `active`. AI-generated images start as `proposed` until the user accepts them.

#### Scenario: User-uploaded image is immediately active
- **WHEN** a user uploads an image to their project
- **THEN** the image is created with `approval_status=active`

#### Scenario: AI-generated image starts as proposed
- **WHEN** the Leonardo AI service creates an image for a project
- **THEN** the image is created with `approval_status=proposed`

#### Scenario: User accepts a proposed image
- **WHEN** a user accepts a proposed image
- **THEN** the image's `approval_status` is set to `active`

#### Scenario: User rejects a proposed image
- **WHEN** a user rejects a proposed image
- **THEN** the image and its variants are deleted from S3 and the database

### Requirement: Icon is required for listing visibility

A project SHALL only appear on the projects listing page if it has at least one `ProjectImage` with `purpose=icon` and `approval_status=active`. Projects without an active icon remain accessible via direct URL.

#### Scenario: Project with icon appears on listing
- **WHEN** the projects listing API is queried
- **THEN** only projects with an active icon image are returned

#### Scenario: Project without icon excluded from listing
- **WHEN** the projects listing API is queried and a project has no active icon
- **THEN** that project is not included in the results

#### Scenario: Project without icon accessible by direct URL
- **WHEN** a user navigates to `/projects/{id}` for a project without an icon
- **THEN** the project detail page renders normally

### Requirement: Existing images migrated to screenshot purpose

All existing `ProjectImage` rows SHALL be migrated to `purpose=screenshot` and `approval_status=active`. The `is_main` field SHALL be preserved unchanged as a fallback mechanism.

#### Scenario: Data migration sets purpose and status
- **WHEN** the migration runs
- **THEN** all existing `ProjectImage` rows have `purpose=screenshot` and `approval_status=active`

#### Scenario: is_main field preserved
- **WHEN** the migration runs
- **THEN** the `is_main` field on all existing images is unchanged

### Requirement: Images queryable by purpose

The API SHALL support querying project images grouped by purpose. The response SHALL include separate collections for each purpose type, making it easy for the frontend to display the right image in the right slot.

#### Scenario: Get images grouped by purpose
- **WHEN** `GET /api/projects/{id}/images` is called
- **THEN** the response contains images grouped as `icon`, `screenshots`, `main_image`, `winner_composite`, each with their active and proposed images

### Requirement: Previous proposals replaced on new generation

When a new image generation completes for a given project and purpose, any existing `proposed` images for that same project and purpose SHALL be deleted (S3 files and DB records) before the new proposed images are saved.

#### Scenario: New generation replaces old proposals
- **WHEN** a new icon generation completes and the project already has 3 proposed icon images from a previous generation
- **THEN** the 3 old proposed icons are deleted and the new generated images are saved as proposed
