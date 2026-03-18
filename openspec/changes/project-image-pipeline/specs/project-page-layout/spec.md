## ADDED Requirements

### Requirement: Project owner image management section

The project edit page (My Projects) SHALL include an image management section that displays purpose-specific image slots: icon, screenshots, and main image. Each slot SHALL show the current active image and any proposed images.

#### Scenario: Owner sees image slots on edit page
- **WHEN** a project owner visits their project edit page
- **THEN** they see distinct sections for: icon (single slot), screenshots (multi-upload), and main image (single slot)

#### Scenario: Owner sees proposed images
- **WHEN** a project has proposed images from AI generation
- **THEN** the proposed images are displayed in their respective slots with accept and reject actions

### Requirement: Owner can generate images

The project edit page SHALL allow project owners to generate images using the generation dialog for icon and main image purposes.

#### Scenario: Owner generates an icon
- **WHEN** a project owner clicks "Generate" on the icon slot
- **THEN** the generation dialog opens with a pre-filled icon prompt based on the project metadata

#### Scenario: Owner generates a main image from screenshot
- **WHEN** a project owner clicks "Generate" on the main image slot and has screenshots uploaded
- **THEN** the generation dialog opens showing screenshot selection and device frame options

#### Scenario: Owner generates an abstract main image
- **WHEN** a project owner clicks "Generate" on the main image slot and has no screenshots
- **THEN** the generation dialog opens with an abstract concept prompt

### Requirement: Owner can accept or reject proposed images

Project owners SHALL be able to accept proposed images (making them active) or reject them (deleting them). Accepting an image for a slot that already has an active image SHALL replace the previous active image.

#### Scenario: Owner accepts a proposed icon
- **WHEN** a project owner clicks accept on a proposed icon image
- **THEN** the proposed image becomes active, and any previously active icon is displaced

#### Scenario: Owner rejects a proposed image
- **WHEN** a project owner clicks reject on a proposed image
- **THEN** the proposed image and its variants are deleted

### Requirement: Icon missing banner

When a project is missing an active icon, the project edit page SHALL display a prominent banner explaining that an icon is required for the project to appear on the listing page, with a call-to-action to upload or generate one.

#### Scenario: Banner shown when icon missing
- **WHEN** a project owner visits their project edit page and the project has no active icon
- **THEN** a banner is displayed stating the project needs an icon to appear on the projects listing, with upload and generate buttons

#### Scenario: Banner hidden when icon exists
- **WHEN** a project owner visits their project edit page and the project has an active icon
- **THEN** no icon-missing banner is shown

### Requirement: Screenshots UI renamed

The existing image upload UI on the project edit page SHALL be relabelled from generic "images" terminology to "Screenshots". The "Set as main image" action SHALL be renamed to "Set as primary screenshot".

#### Scenario: Upload area labelled as screenshots
- **WHEN** a project owner views the image upload section
- **THEN** the section is labelled "Screenshots" and the upload prompt refers to screenshots

#### Scenario: Set primary screenshot action
- **WHEN** a project owner clicks the action to designate a screenshot
- **THEN** the action is labelled "Set as primary screenshot" (setting `is_main=True`)
