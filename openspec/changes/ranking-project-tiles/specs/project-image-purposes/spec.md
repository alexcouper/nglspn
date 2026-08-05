## MODIFIED Requirements

### Requirement: Backend image URL resolution with fallback

The project API responses for listing endpoints and for the reviewer ballot endpoint SHALL include resolved image URLs for each purpose: `icon_url`, `hero_banner_url`, `in_use_image_url`. The backend SHALL resolve each using the fallback chain: purpose-specific image → main project image → null. Resolution SHALL consider only images whose `upload_status` is `uploaded`; an image that is still uploading SHALL never be returned by any of these URLs. The frontend SHALL render a gradient placeholder when a URL is null.

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

#### Scenario: Reviewer ballot response resolves purposes
- **WHEN** a reviewer fetches the projects on their ballot for a competition
- **THEN** each project in the response carries `in_use_image_url` and `hero_banner_url` resolved by the same fallback chain used by the listing endpoints

#### Scenario: Only a non-uploaded image matches the purpose
- **WHEN** a project's only image with purpose `in_use` has an `upload_status` other than `uploaded`
- **THEN** that image is skipped and resolution falls through to the main image, or to null if there is no uploaded main image
