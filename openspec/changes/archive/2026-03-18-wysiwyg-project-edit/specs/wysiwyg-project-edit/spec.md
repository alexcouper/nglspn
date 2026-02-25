## ADDED Requirements

### Requirement: Shared project page layout

The edit page (`/my-projects/[id]`) and public page (`/projects/[id]`) SHALL use a shared `ProjectPageLayout` component that defines the page structure: a banner zone, a two-column body with a 280px left sidebar and a flexible main content area with tabs. Each zone SHALL accept content via render slots so that the public page passes read-only elements and the edit page passes form fields or editable components.

#### Scenario: Public page uses shared layout
- **WHEN** a visitor loads `/projects/[id]`
- **THEN** the page SHALL render using `ProjectPageLayout` with `ProjectTitleBanner` in the banner slot, images/tags in the sidebar slot, and description/discussions tabs in the main content slot
- **AND** the rendered output SHALL be visually identical to the current public page

#### Scenario: Edit page preview mode uses shared layout
- **WHEN** an author toggles to preview mode on `/my-projects/[id]`
- **THEN** the page SHALL render using `ProjectPageLayout` with the same public page components, populated with the current form data assembled into a Project object

### Requirement: Editable banner with inline fields

In edit mode, the banner zone SHALL display inline text inputs for title, tagline, and website URL in the same positions where the public page displays those fields as text. The author name SHALL be displayed as read-only text (not editable). The inputs SHALL use ghost styling (matching font sizes, weights, and colors of the public banner) with subtle focus indicators.

#### Scenario: Title field in banner
- **WHEN** the edit page loads in edit mode
- **THEN** the banner SHALL display a text input for the project title, styled with the same `text-2xl sm:text-3xl font-semibold` as the public page title
- **AND** the input SHALL have a placeholder of "Project Title"

#### Scenario: Tagline field in banner
- **WHEN** the edit page loads in edit mode
- **THEN** the banner SHALL display a text input for the tagline below the title, styled to match the public page tagline text
- **AND** the input SHALL have a maxLength of 200

#### Scenario: Website URL field in banner
- **WHEN** the edit page loads in edit mode
- **THEN** the banner SHALL display a URL input in the meta row where the website link appears on the public page

#### Scenario: Author displayed but not editable
- **WHEN** the edit page loads in edit mode
- **THEN** the author name SHALL be displayed as plain text in the meta row (not as an input)

### Requirement: Image management in sidebar

In edit mode, the left sidebar SHALL display the image gallery in editable mode (with set-main and delete controls) followed by an image drop zone for uploads, in the same position where images appear on the public page. Upload progress SHALL be displayed below the drop zone.

#### Scenario: Editable image gallery in sidebar
- **WHEN** the edit page loads in edit mode
- **THEN** the sidebar SHALL display `ImageGallery` with the `editable` prop enabled, showing star (set main) and trash (delete) controls on hover

#### Scenario: Image upload drop zone in sidebar
- **WHEN** the edit page loads in edit mode
- **THEN** an `ImageDropZone` SHALL appear below the image gallery in the sidebar
- **AND** it SHALL be disabled when 10 images are already uploaded or an upload is in progress

#### Scenario: Upload progress in sidebar
- **WHEN** the author drops files onto the drop zone
- **THEN** upload progress indicators SHALL appear below the drop zone in the sidebar

### Requirement: Tag editing in sidebar

In edit mode, the left sidebar SHALL display the tag selector below the images, in the same position where tags are shown on the public page. The tag selector SHALL allow the author to add and remove tags.

#### Scenario: Tag selector position
- **WHEN** the edit page loads in edit mode
- **THEN** a `TagSidebarSelector` SHALL appear in the sidebar below the image section, in the position where `TagGroup` elements display on the public page

#### Scenario: Tag changes update form data
- **WHEN** the author adds or removes a tag via the sidebar selector
- **THEN** the form data `tag_ids` array SHALL be updated
- **AND** the preview mode SHALL reflect the updated tags

### Requirement: Description editing in main content tab

In edit mode, the "Description" tab SHALL display a large markdown textarea instead of rendered markdown. The textarea SHALL fill the main content area.

#### Scenario: Description textarea in description tab
- **WHEN** the edit page is in edit mode and the "Description" tab is active
- **THEN** the main content area SHALL display a textarea for the description with a markdown indicator badge
- **AND** the textarea SHALL have a minimum height that fills the content area

#### Scenario: Description changes reflected in preview
- **WHEN** the author edits the description textarea and switches to preview mode
- **THEN** the description tab SHALL render the updated markdown content using `ReactMarkdown`

### Requirement: Settings tab in edit mode

In edit mode, a "Settings" tab SHALL replace the "Discussions" tab. The settings tab SHALL display the project status and submission date.

#### Scenario: Settings tab content
- **WHEN** the edit page is in edit mode and the "Settings" tab is active
- **THEN** the tab SHALL display the project status (pending/approved/rejected) and submission date

#### Scenario: Settings tab not shown in preview
- **WHEN** the author switches to preview mode
- **THEN** the tabs SHALL show "Description" and "Discussions" (the normal public page tabs), not "Settings"

### Requirement: Sticky edit toolbar

The edit page SHALL display a sticky toolbar between the navigation bar and the banner containing: edit/preview mode toggle (pencil and eye icons), save button, and delete button. The toolbar SHALL remain visible when scrolling.

#### Scenario: Toolbar position and stickiness
- **WHEN** the edit page loads
- **THEN** a toolbar SHALL appear below the navigation bar, above the banner
- **AND** it SHALL remain visible (sticky) when the user scrolls down

#### Scenario: Save button in toolbar
- **WHEN** the author clicks the save button in the toolbar
- **THEN** the project SHALL be saved with the current form data (title, tagline, website_url, description, tag_ids)
- **AND** a success message SHALL be displayed

#### Scenario: Delete button in toolbar
- **WHEN** the author clicks the delete button in the toolbar
- **THEN** a confirmation dialog SHALL appear before the project is deleted

#### Scenario: Edit/preview toggle in toolbar
- **WHEN** the author clicks the preview (eye) icon
- **THEN** the page SHALL switch to preview mode, rendering the public page layout with current form data
- **AND** when the author clicks the edit (pencil) icon, the page SHALL switch back to edit mode with form fields

### Requirement: Edit and preview mode switching preserves data

Switching between edit and preview mode SHALL preserve all form data. No data SHALL be lost when toggling modes.

#### Scenario: Round-trip data preservation
- **WHEN** the author edits the title, description, and tags, switches to preview, then switches back to edit
- **THEN** all edited values SHALL be preserved in the form fields exactly as entered
