## ADDED Requirements

### Requirement: Image generation via Leonardo AI

The system SHALL integrate with the Leonardo AI REST API to generate project images. Generation requests are tracked via `ImageGenerationRequest` records. The service SHALL support generating icons (1:1), main images (4:3), and winner composites (16:9).

#### Scenario: Generate an icon
- **WHEN** a generation request is created with `purpose=icon`
- **THEN** the system calls Leonardo AI with Phoenix 1.0 model, 1024×1024 dimensions, ILLUSTRATION preset, and the provided prompt

#### Scenario: Generate a main image without screenshots
- **WHEN** a generation request is created with `purpose=main_image` and no reference image
- **THEN** the system calls Leonardo AI with Phoenix 1.0 model, 1024×768 dimensions, PHOTOGRAPHY preset, and the provided prompt

#### Scenario: Generate a main image from a screenshot
- **WHEN** a generation request is created with `purpose=main_image`, a reference screenshot, and a device frame selection
- **THEN** the system uploads the reference screenshot to Leonardo, then calls Leonardo AI with the screenshot as reference and a prompt incorporating the device frame context (mobile/laptop/watch)

#### Scenario: Generate a winner composite
- **WHEN** a generation request is created with `purpose=winner_composite` and the project has an active icon
- **THEN** the system uploads the icon to Leonardo, calls FLUX Kontext model at 1248×704 with the icon as contextImage and a fixed trophy composition prompt

### Requirement: Generation request lifecycle

Each `ImageGenerationRequest` SHALL track its status through: `queued` → `generating` → `completed` or `failed`. The system SHALL poll Leonardo's API until the generation completes or fails.

#### Scenario: Successful generation
- **WHEN** a generation request is enqueued and Leonardo returns completed images
- **THEN** the request status progresses from `queued` → `generating` → `completed`, the `leonardo_generation_id` is recorded, and `completed_at` is set

#### Scenario: Generation fails at Leonardo
- **WHEN** Leonardo's API returns a failure status
- **THEN** the request status is set to `failed` with the error message stored in `error_message`

#### Scenario: Generation polling timeout
- **WHEN** polling Leonardo's API exceeds the maximum wait time (~60s)
- **THEN** the request status is set to `failed` with a timeout error message

### Requirement: Generated images stored as ProjectImage

When a Leonardo generation completes, each generated image SHALL be downloaded from Leonardo's CDN, uploaded to the project's S3 storage, and saved as a `ProjectImage` with the appropriate `purpose` and `approval_status=proposed`. Variant generation SHALL be triggered for each saved image.

#### Scenario: Generation results saved to S3
- **WHEN** Leonardo returns 3 completed images for an icon generation
- **THEN** 3 `ProjectImage` rows are created with `purpose=icon`, `approval_status=proposed`, stored in S3 under the project's image path, and variant generation is enqueued for each

#### Scenario: Generated image linked to generation request
- **WHEN** a generated image is saved as a `ProjectImage`
- **THEN** the `ProjectImage` has a `generation_request` FK pointing to the `ImageGenerationRequest` that produced it

### Requirement: Multiple variants per generation

A generation request SHALL support generating 1-4 image variants in a single Leonardo API call via the `num_variants` field. All variants are saved as `proposed` images for the user to choose from.

#### Scenario: Generate 4 icon variants
- **WHEN** a generation request is created with `num_variants=4`
- **THEN** the Leonardo API is called with `num_images=4` and up to 4 proposed images are created

### Requirement: Generation status polling endpoint

The API SHALL provide a polling endpoint for generation status. The response SHALL include the current status and, when completed, the URLs of generated images.

#### Scenario: Poll in-progress generation
- **WHEN** `GET /api/images/generate/{id}` is called for a generating request
- **THEN** the response includes `status=generating` and no images

#### Scenario: Poll completed generation
- **WHEN** `GET /api/images/generate/{id}` is called for a completed request
- **THEN** the response includes `status=completed` and an array of proposed `ProjectImage` data with URLs and variants

#### Scenario: Poll failed generation
- **WHEN** `GET /api/images/generate/{id}` is called for a failed request
- **THEN** the response includes `status=failed` and the `error_message`

### Requirement: Generation dialog pre-fills prompt from project metadata

When opening the generation dialog, the system SHALL pre-fill the prompt based on the project's title, tagline, and description. The prompt template varies by purpose.

#### Scenario: Icon prompt pre-fill
- **WHEN** the generation dialog opens for an icon
- **THEN** the prompt is pre-filled with a template incorporating the project title and tagline, suggesting a clean app icon style

#### Scenario: Main image prompt pre-fill with screenshot
- **WHEN** the generation dialog opens for a main image with a screenshot selected and device frame "laptop"
- **THEN** the prompt is pre-filled describing the app displayed on a laptop screen

#### Scenario: Main image prompt pre-fill without screenshots
- **WHEN** the generation dialog opens for a main image with no screenshots available
- **THEN** the prompt is pre-filled with an abstract conceptual image based on the project description

#### Scenario: Winner composite has no editable prompt
- **WHEN** the generation dialog opens for a winner composite
- **THEN** the prompt is shown but not editable, and describes a trophy composition featuring the project icon

### Requirement: Generation dialog supports screenshot and device frame selection

For `main_image` generation, if the project has screenshots, the dialog SHALL show the available screenshots for the user to select as a reference image. It SHALL also show a device frame selector with options: mobile, laptop, watch.

#### Scenario: Screenshot selection shown for main image
- **WHEN** the generation dialog opens for a main image and the project has 3 screenshots
- **THEN** the dialog shows the 3 screenshots as selectable reference options

#### Scenario: Device frame selector shown
- **WHEN** the generation dialog opens for a main image with screenshots available
- **THEN** the dialog shows device frame options: mobile, laptop, watch

#### Scenario: No screenshot selection when none exist
- **WHEN** the generation dialog opens for a main image and the project has no screenshots
- **THEN** no screenshot selector or device frame selector is shown
