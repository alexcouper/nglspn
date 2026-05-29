## ADDED Requirements

### Requirement: Image purpose field

The `ProjectImage` model SHALL have a `purpose` CharField with choices: `general`, `icon`, `hero_banner`, `in_use`, `winner_composite`. The default SHALL be `general`. All existing images SHALL remain `general` (via migration default).

#### Scenario: New image defaults to general purpose
- **WHEN** a project image is uploaded without specifying a purpose
- **THEN** the image's purpose is set to `general`

#### Scenario: Image with specific purpose
- **WHEN** an admin or upload flow sets an image's purpose to `icon`
- **THEN** the image's purpose field stores `icon`

#### Scenario: Existing images after migration
- **WHEN** the migration runs on a database with existing images
- **THEN** all existing images have purpose set to `general`

### Requirement: Backend image URL resolution with fallback

The project API responses for listing endpoints SHALL include resolved image URLs for each purpose: `icon_url`, `hero_banner_url`, `in_use_image_url`. The backend SHALL resolve each using the fallback chain: purpose-specific image → main project image → null. The frontend SHALL render a gradient placeholder when a URL is null.

#### Scenario: Project has a purpose-specific icon
- **WHEN** a project has an image with purpose `icon`
- **THEN** the API returns that image's URL as `icon_url`

#### Scenario: Project has no icon but has a main image
- **WHEN** a project has no image with purpose `icon` but has a main image (is_main=True)
- **THEN** the API returns the main image's URL as `icon_url`

#### Scenario: Project has no images at all
- **WHEN** a project has no uploaded images
- **THEN** the API returns null for `icon_url`, `hero_banner_url`, and `in_use_image_url`

#### Scenario: Frontend renders gradient placeholder for null URL
- **WHEN** the frontend receives null for an image URL
- **THEN** a gradient placeholder is rendered in place of the image

### Requirement: Image artifact dimensions per purpose

Each image purpose has target dimensions:

| Purpose | Min Dimensions | Aspect Ratio | Used In |
|---------|---------------|-------------|---------|
| icon | 256x256px | 1:1 square | Icon cards, list items, category view, winner composites |
| hero_banner | 1536px wide | 16:9 | Featured section, fallback for arrivals |
| in_use | 1024px wide | 4:3 | New Arrivals cards |
| winner_composite | 1536px wide | 16:9 | Competition Winners section |
| general | Any | Any | Existing images, general gallery |

#### Scenario: Icon used at various sizes
- **WHEN** an icon-purpose image is rendered
- **THEN** it is displayed at 40px, 44px, or 48px square depending on the card type, cropped from the 1:1 source

### Requirement: Purpose-specific image queries

The system SHALL provide a method to query a project's images by purpose, returning the best image for a given purpose using the fallback chain. This SHALL be used by the listing API endpoints to resolve image URLs server-side.

#### Scenario: Query icon image with fallback
- **WHEN** the system resolves `icon` for a project with no icon-purpose image but a main image
- **THEN** the main image is returned

#### Scenario: Query icon image with purpose-specific match
- **WHEN** the system resolves `icon` for a project with an icon-purpose image
- **THEN** the icon-purpose image is returned (not the main image)

### Requirement: Gradient placeholder for missing images

When no image is available for a project (all URL fields are null), the frontend SHALL render a gradient placeholder based on the project title hash, using the existing `getPlaceholderColor` utility.

#### Scenario: Project with no images renders gradient
- **WHEN** a project card renders with null image URLs
- **THEN** a gradient placeholder based on the project title hash is shown
