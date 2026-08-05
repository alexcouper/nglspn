## ADDED Requirements

### Requirement: Author selects the hero framing on upload

After a hero image finishes uploading, the system SHALL present a crop dialog
before the image is accepted as the article's hero. The dialog SHALL show a
selection frame fixed to the full width of the dialog content, standing in for the
article column, with the source image pannable and zoomable beneath it. The author
SHALL be able to change the height of the selection frame, and the resulting
aspect ratio SHALL be displayed while they do so.

#### Scenario: Crop dialog opens after upload

- **WHEN** an author uploads a hero image and the upload succeeds
- **THEN** the crop dialog opens with the largest selection the source allows at
  16:9, centred

#### Scenario: Author confirms a selection

- **WHEN** the author pans, zooms or resizes the frame and confirms
- **THEN** the selection rectangle and its aspect ratio are saved with the article
  and the dialog closes

#### Scenario: Author cancels the dialog

- **WHEN** the author cancels the crop dialog after a first upload
- **THEN** no hero is set on the article and the uploaded image is discarded

#### Scenario: Author cancels after re-framing an existing hero

- **WHEN** the author opens the crop dialog on an existing hero and cancels
- **THEN** the previously stored selection is left unchanged

### Requirement: Hero aspect ratio is bounded

The system SHALL constrain the hero aspect ratio to between 4:1 and 1:1
inclusive. The frame height handles SHALL NOT permit a selection outside that
range.

#### Scenario: Author drags past the wide bound

- **WHEN** the author drags the frame shorter than a 4:1 selection
- **THEN** the frame stops at 4:1

#### Scenario: Author drags past the tall bound

- **WHEN** the author drags the frame taller than a 1:1 selection
- **THEN** the frame stops at 1:1

### Requirement: Low-resolution selections are warned about

The system SHALL warn, without blocking, when the confirmed selection is under
768 pixels wide in the source image, because that is below the `medium` variant
width and will render soft.

#### Scenario: Author zooms into a small region

- **WHEN** the selection covers a region less than 768px wide in the original
- **THEN** the dialog shows a resolution warning and still allows confirmation

### Requirement: Hero renders at the stored ratio everywhere

The system SHALL render the article hero at the stored aspect ratio, at the full
width of its container, on every viewport and on both the editor and the article
page. The editor preview and the article page SHALL use the same rendering
component so their framing cannot diverge.

#### Scenario: Narrow viewport

- **WHEN** an article whose hero was framed at 34:12 is viewed on a 375px-wide
  screen
- **THEN** the hero is 375px wide and its height is 375 × 12 / 34, showing the
  same region of the image as on a desktop

#### Scenario: Editor matches the article page

- **WHEN** an author views their hero in the editor and then on the published
  article
- **THEN** both show the same region of the image at the same aspect ratio

### Requirement: Listing cards use a fixed 16:9 crop

The system SHALL render every article listing card — lead and grid — at 16:9, so
that a grid of cards is uniform. Card framing SHALL come from a stored card crop
when one exists.

#### Scenario: Lead and grid agree

- **WHEN** the same article appears as the lead card and as a grid card
- **THEN** both show the same region of the image at 16:9, differing only in
  rendered width

### Requirement: Card crop is derived from the hero selection by default

The system SHALL derive the card crop from the hero crop whenever an article has
a hero selection but no explicit card selection: the same centre point, grown or
shrunk vertically to reach 16:9, clamped to the bounds of the source image. The
derivation SHALL be performed server-side and delivered already resolved, so the
frontend has no second implementation to drift from.

#### Scenario: Derived card follows a re-framed hero

- **WHEN** the author changes the hero selection and has never set a card crop
- **THEN** the card crop re-derives from the new hero selection

#### Scenario: Hero selection near an image edge

- **WHEN** the hero selection sits against the top edge of the image and growing
  it vertically would exceed the image
- **THEN** the derived 16:9 rectangle is clamped inside the image bounds rather
  than overflowing

### Requirement: Author can override the card crop

The system SHALL allow the author to set a card crop independently of the hero,
from the article card preview dialog, using the same crop control with the frame
locked to 16:9. Once set, the card crop SHALL stop tracking the hero selection.
The system SHALL provide a way to discard the override and return to the derived
crop.

#### Scenario: Override stops tracking the hero

- **WHEN** the author sets a card crop and then re-frames the hero
- **THEN** the card crop is unchanged

#### Scenario: Reset returns to derived

- **WHEN** the author resets the card crop
- **THEN** the stored override is cleared and the card shows the crop derived
  from the current hero selection

### Requirement: Crops are stored as rectangles, not as new image files

The system SHALL store crops as normalised coordinates against the source image
and apply them at render time over the existing image variants. The system SHALL
NOT generate additional cropped derivative files.

#### Scenario: Re-cropping is immediate

- **WHEN** the author changes a crop and saves
- **THEN** the new framing is visible without any image processing step or
  processing state

### Requirement: Articles without a stored crop keep today's rendering

The system SHALL render an article that has no stored hero crop at 16:9, centred
— the behaviour before this change. No data migration of existing articles SHALL
be required.

#### Scenario: Pre-existing article

- **WHEN** an article created before this change is rendered
- **THEN** its hero and cards appear at 16:9 centred, as they did before

### Requirement: Crop values are validated on write

The system SHALL reject a crop whose rectangle falls outside the normalised 0–1
range, whose width or height is zero or negative, or whose aspect ratio is
outside the permitted bounds. A card crop SHALL be rejected if its ratio is not
16:9.

#### Scenario: Rectangle outside the image

- **WHEN** a crop is submitted with `x + w` greater than 1
- **THEN** the API responds 422 and the article is unchanged

#### Scenario: Card crop at the wrong ratio

- **WHEN** a card crop is submitted at 4:3
- **THEN** the API responds 422 and the article is unchanged
