## ADDED Requirements

### Requirement: Variant generation on upload completion

When a project image upload is completed, the system SHALL asynchronously generate WebP size variants (thumb 384w, medium 768w, large 1536w) and store each as an `ImageVariant` record in the database with its S3 storage key, dimensions, and file size. The original image SHALL NOT be modified. Variants SHALL only be generated for sizes smaller than the original width (no upscaling).

#### Scenario: Successful variant generation for a large image
- **WHEN** a user completes uploading a 4000×2250 JPEG image
- **THEN** the system enqueues an async task that generates three WebP variants (384w, 768w, 1536w), uploads each to S3, and creates an `ImageVariant` row for each with the correct dimensions, storage key, and file size

#### Scenario: Original image smaller than a variant size
- **WHEN** a user completes uploading a 500×300 image
- **THEN** the system generates only the thumb (384w) variant and skips medium (768w) and large (1536w) since they would require upscaling

#### Scenario: Original image smaller than all variant sizes
- **WHEN** a user completes uploading a 200×150 image
- **THEN** the system generates no variants and creates no `ImageVariant` rows

#### Scenario: Variant generation partially fails
- **WHEN** the async task successfully generates and uploads the thumb variant but fails on the medium variant
- **THEN** the thumb `ImageVariant` row SHALL be preserved in the database and the system SHALL log the error

### Requirement: Variant storage in S3

Variant files SHALL be stored in the same S3 bucket as originals, using the key pattern `{original_key_without_extension}/{size}.webp`. Variants SHALL be uploaded with `public-read` ACL and `image/webp` content type, served through the existing CDN at `cdn.naglasupan.is`.

#### Scenario: Variant storage key derivation
- **WHEN** the original image has storage key `projects/abc/def123/photo.jpg`
- **THEN** the thumb variant SHALL be stored at `projects/abc/def123/photo/thumb.webp`, medium at `projects/abc/def123/photo/medium.webp`, and large at `projects/abc/def123/photo/large.webp`

#### Scenario: Variant served via CDN
- **WHEN** a variant is stored in S3
- **THEN** it SHALL be accessible at `https://cdn.naglasupan.is/{storage_key}` with no additional configuration

### Requirement: Variant data in API responses

The project image API response SHALL include a `variants` array for each image. Each variant entry SHALL contain `size`, `url`, `width`, and `height`. The `variants` array SHALL be empty when no variants have been generated.

#### Scenario: Image with all variants generated
- **WHEN** the API returns a project image that has all three variants
- **THEN** the response SHALL include a `variants` array with three entries, each containing `size` (one of "thumb", "medium", "large"), `url` (the CDN URL), `width`, and `height`

#### Scenario: Image with no variants yet
- **WHEN** the API returns a project image whose async variant generation has not completed
- **THEN** the response SHALL include an empty `variants` array and the `url` field SHALL still contain the original image URL

#### Scenario: Image with partial variants
- **WHEN** the API returns a project image where only thumb and medium variants exist
- **THEN** the response SHALL include a `variants` array with two entries (thumb and medium only)

### Requirement: Frontend variant selection with fallback

The frontend SHALL select the best available variant for each rendering context. When the preferred size is unavailable, it SHALL fall up to the next larger available variant, then fall back to the original image URL via `next/image`.

#### Scenario: Project grid card with thumb available
- **WHEN** rendering a project card in the grid and the image has a thumb variant
- **THEN** the frontend SHALL render the thumb variant URL directly (no Next.js image optimization)

#### Scenario: Project grid card with thumb missing but medium available
- **WHEN** rendering a project card in the grid and the image has no thumb variant but has a medium variant
- **THEN** the frontend SHALL render the medium variant URL directly

#### Scenario: Project grid card with no variants available
- **WHEN** rendering a project card in the grid and the image has no variants
- **THEN** the frontend SHALL render the original image URL via `next/image` (same as current behaviour)

#### Scenario: Lightbox with large available
- **WHEN** rendering the lightbox view and the image has a large variant
- **THEN** the frontend SHALL render the large variant URL directly

#### Scenario: Lightbox with no large variant
- **WHEN** rendering the lightbox view and the image has no large variant
- **THEN** the frontend SHALL fall back to the original image URL

### Requirement: Variant deletion with image

When a project image is deleted, the system SHALL delete all associated variant files from S3 and remove the `ImageVariant` rows from the database. Failure to delete a variant file from S3 SHALL be logged but SHALL NOT prevent the image deletion from completing.

#### Scenario: Delete image with variants
- **WHEN** a user deletes a project image that has three variants
- **THEN** the system SHALL delete the original file and all three variant files from S3, and remove the `ProjectImage` row and all associated `ImageVariant` rows from the database

#### Scenario: Variant file deletion fails in S3
- **WHEN** a user deletes a project image and one variant file fails to delete from S3
- **THEN** the original image and all DB records SHALL still be deleted, and the S3 failure SHALL be logged

### Requirement: Backfill management command

A Django management command SHALL generate variants for all existing `ProjectImage` records that are missing expected variants. The command SHALL be idempotent — it SHALL skip any size that already has an `ImageVariant` row.

#### Scenario: Backfill images with no variants
- **WHEN** the backfill command runs and there are 50 uploaded images with no variants
- **THEN** the command SHALL generate variants for all 50 images, creating up to 3 `ImageVariant` rows per image depending on original dimensions

#### Scenario: Backfill after partial previous run
- **WHEN** the backfill command runs and an image already has a thumb variant but is missing medium and large
- **THEN** the command SHALL generate only the medium and large variants for that image

#### Scenario: Backfill skips pending/failed images
- **WHEN** the backfill command runs
- **THEN** it SHALL only process images with `upload_status=UPLOADED` and skip images in PENDING or FAILED status
