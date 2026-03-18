## MODIFIED Requirements

### Requirement: Variant generation on upload completion

When a project image upload is completed, the system SHALL asynchronously generate WebP size variants (thumb 384w, medium 768w, large 1536w) and store each as an `ImageVariant` record in the database with its S3 storage key, dimensions, and file size. The original image SHALL NOT be modified. Variants SHALL only be generated for sizes smaller than the original width (no upscaling). This requirement now also applies to AI-generated images saved from Leonardo AI — variant generation SHALL be triggered for generated images in the same way as uploaded images.

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

#### Scenario: Variant generation triggered for AI-generated images
- **WHEN** a Leonardo AI generation completes and images are saved to S3 as ProjectImage rows
- **THEN** the variant generation task is enqueued for each generated image, producing the same WebP variants as uploaded images
