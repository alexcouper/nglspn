## ADDED Requirements

### Requirement: An article needs no image

The system SHALL allow an article to be created, saved and published with no
image. The publish check SHALL require a non-empty `title` and `body` only.

The article render page SHALL NOT display an image above the body. An author who
wants an image at the top of their article inserts one into the body.

#### Scenario: Publishing without an image

- **WHEN** an author publishes an article with a title and a body but no listing
  image
- **THEN** the article publishes and the API does not respond 422

#### Scenario: Clearing the image on a published article

- **WHEN** an author removes the listing image from an already-published article
- **THEN** the change is accepted and the article's cards render without an image

#### Scenario: Article page shows only the body

- **WHEN** a reader opens an article that has a listing image
- **THEN** the page renders the title, byline and body, and no image band above
  the body

### Requirement: The listing image has three modes

The system SHALL store a `listing_image_mode` of `auto`, `chosen` or `none` on
every article, defaulting to `auto`. A nullable image id alone SHALL NOT be used
to express this, because it cannot distinguish "not chosen yet" from
"deliberately removed".

- `auto` — the listing image is the first image uploaded to the article, framed
  16:9 centred.
- `chosen` — the listing image and its crop are exactly what the author picked.
- `none` — the article has no listing image regardless of what the body contains.

#### Scenario: A new article defaults to auto

- **WHEN** an article is created
- **THEN** its mode is `auto`

#### Scenario: Removal is remembered

- **GIVEN** an article in `auto` mode that has uploaded images
- **WHEN** the author removes the listing image and saves again
- **THEN** the mode is `none` and no image is re-adopted on that save or any
  later one

#### Scenario: Framing an image commits the choice

- **GIVEN** an article in `auto` mode
- **WHEN** the author adjusts the crop without changing which image is used
- **THEN** the mode becomes `chosen` and the stored image stops being re-derived

### Requirement: Auto mode resolves on save

The system SHALL resolve `auto` mode when an article is created or updated, by
setting the listing image to the earliest-uploaded image linked to the article
and the listing crop to null. Resolution SHALL use the image–article link
ordered by upload time, and SHALL NOT inspect the article body. Resolution SHALL
NOT happen at read time.

Where the article has no linked images, the listing image SHALL be null and the
article renders as a text-only card while remaining in `auto` mode.

#### Scenario: First upload becomes the listing image

- **WHEN** an author uploads two images to an article and saves
- **THEN** the listing image is the earlier of the two and the listing crop is
  null

#### Scenario: A later upload does not displace it

- **GIVEN** an article in `auto` mode already showing its first upload
- **WHEN** the author uploads another image and saves
- **THEN** the listing image is unchanged

#### Scenario: The first upload is deleted

- **GIVEN** an article in `auto` mode whose listing image is its first upload
- **WHEN** that image is deleted and the article is saved
- **THEN** the listing image becomes the next-earliest linked image, or null if
  there is none

#### Scenario: Resolution is not a read-time concern

- **WHEN** a listing of articles is requested
- **THEN** each card's image comes from the stored listing image, with nothing
  derived per request

### Requirement: One image, one framing, both card variants

The system SHALL store exactly one crop rectangle per article, always at 16:9,
and SHALL render the lead card and the grid card from that same rectangle. The
system SHALL NOT offer per-variant framing.

The system SHALL reject a listing crop whose ratio is not 16:9.

#### Scenario: Lead and grid agree

- **WHEN** the same article appears as the lead card and as a grid card
- **THEN** both show the same region of the image, differing only in rendered
  width

#### Scenario: A crop at the wrong ratio

- **WHEN** a listing crop is submitted at 4:3
- **THEN** the API responds 422 and the article is unchanged

### Requirement: Cards without an image give the space to the headline

A listing card for an article with no listing image SHALL render no image
element and no placeholder graphic. The headline and summary SHALL take the
space the image would have occupied.

An imageless lead card SHALL be visually distinguishable from a card whose image
failed to load.

#### Scenario: Imageless grid card

- **WHEN** an article with no listing image renders as a grid card
- **THEN** no image element is present and the headline is allowed more lines
  than on a card with an image

#### Scenario: Mixed grid stays aligned

- **WHEN** a grid contains both imageless and imaged cards
- **THEN** the cards in a row are of equal height

#### Scenario: Imageless lead card

- **WHEN** an article with no listing image renders as the lead card
- **THEN** it reads as a deliberate text-led card rather than as a card missing
  its image

### Requirement: Listing settings are a tab on the article editor

The system SHALL present the article editor as two tabs, **Content** and
**Listing settings**. The article title and channel SHALL sit above the tab
strip, so both are editable from either tab and the title stays visible beside
the card preview.

The **Listing settings** tab SHALL contain the summary field, the listing image
control, and a preview of the article's card.

The system SHALL NOT present the card preview as a dialog.

#### Scenario: Reaching listing settings

- **WHEN** an author opens the article editor and selects **Listing settings**
- **THEN** the summary field, image control and card preview are shown in the
  page, with the title and channel still visible above them

#### Scenario: Editing the title from the listing tab

- **WHEN** an author changes the title while on the **Listing settings** tab
- **THEN** the card preview reflects the new title

### Requirement: Switching to the listing tab saves the draft

The system SHALL save the article draft before showing the **Listing settings**
tab, because the previewed summary is derived server-side from the saved body.
The save SHALL use the editor's existing confirmation so it is not silent.

#### Scenario: Unsaved body text

- **GIVEN** an author has typed into the body without saving
- **WHEN** they switch to **Listing settings**
- **THEN** the draft is saved first and the preview shows a summary derived from
  the text they just typed

#### Scenario: Save fails on tab switch

- **WHEN** the save triggered by the tab switch fails
- **THEN** the error is shown and the author is not left looking at a preview of
  stale content

### Requirement: The card preview shows one variant at a time

The **Listing settings** tab SHALL offer *As lead story* and *In the grid* as a
nested tab pair, showing one at a time. The system SHALL NOT show both card
variants simultaneously.

#### Scenario: Switching preview variant

- **WHEN** an author selects *In the grid*
- **THEN** the grid card is shown and the lead card is not

### Requirement: Choosing a listing image is a two-step wizard

The system SHALL open a wizard when the author changes the listing image. Step
one selects an image; step two frames it at 16:9 using the existing crop control
hosted as a step rather than as a nested dialog. The author SHALL be able to go
back from step two to step one.

Confirming step two SHALL set the article's mode to `chosen`.

#### Scenario: Picking an existing image

- **WHEN** the author selects an image already in the article and continues
- **THEN** the framing step opens on that image

#### Scenario: Going back

- **WHEN** the author is on the framing step and chooses back
- **THEN** the selection step reopens with their current selection intact

#### Scenario: Cancelling the wizard

- **WHEN** the author cancels at either step
- **THEN** the article's listing image, crop and mode are unchanged

### Requirement: The wizard offers the article's own images

Step one of the wizard SHALL list the images linked to the article, marking the
current selection. It SHALL also offer uploading a new image, which on
completion continues to the framing step.

The list SHALL come from the image–article link, not from parsing the article
body, so an image the author uploaded through the wizard is offered on the same
footing as one they inserted into the body.

Images with no recorded dimensions SHALL NOT be selectable, because there is
nothing to frame.

An upload that is cancelled before the article adopts it SHALL be deleted,
best-effort.

#### Scenario: The article's uploads are offered

- **GIVEN** an author has inserted three images into the article body
- **WHEN** they open the wizard
- **THEN** all three are offered for selection

#### Scenario: A wizard upload is offered on reopening

- **GIVEN** the author chose an image by uploading it in the wizard, so it is not
  in the body
- **WHEN** they reopen the wizard
- **THEN** that image is offered and marked as the current selection

#### Scenario: An image removed from the body is still offered

- **GIVEN** an image uploaded for this article and since deleted from the body
- **WHEN** the author opens the wizard
- **THEN** it is still offered, because it was uploaded for this article

#### Scenario: Reusing the current selection keeps its framing

- **WHEN** the author selects the image that is already chosen and continues
- **THEN** the framing step opens on the stored crop rather than on a default

#### Scenario: Selecting a different image resets the framing

- **WHEN** the author selects an image other than the current one
- **THEN** the framing step opens on a centred default, because a rectangle drawn
  on one image does not transfer to another

### Requirement: The author can remove the listing image

The wizard SHALL offer removing the listing image. Removal SHALL set the mode to
`none`, clear the stored image and crop, and SHALL NOT be undone by a later save.

#### Scenario: Removing an auto-adopted image

- **GIVEN** an article in `auto` mode showing its first uploaded image
- **WHEN** the author removes the listing image
- **THEN** the card renders with no image, and stays that way after further edits
  and saves

### Requirement: Uploaded images are linked to their article

The system SHALL record, on each uploaded image, which article it was uploaded
for. The upload request SHALL carry the owning item's type and id; the system
SHALL reject an id that does not name an article in the same project.

"This image belongs to an article" SHALL be derived from that link rather than
stored as a separate flag, so the two cannot disagree.

Article-linked images SHALL continue to be excluded from the project's gallery,
its cover-image selection and its per-project image cap.

#### Scenario: Body image upload is linked

- **WHEN** an author inserts an image into an article body
- **THEN** the stored image records the article it was uploaded for

#### Scenario: Article images stay out of the project gallery

- **WHEN** a project page is requested
- **THEN** images linked to an article are absent from its gallery, are never
  promoted to the project's main image, and do not count towards the image cap

#### Scenario: Upload naming an article from another project

- **WHEN** an upload request names an article that does not belong to the project
  being uploaded to
- **THEN** the request is rejected

### Requirement: Deleting an article deletes its images

Deleting an article SHALL delete the image records linked to it. They SHALL NOT
be left unlinked, because an unlinked image is indistinguishable from a project
image and would appear in the project's gallery.

Deleting an image that an article uses as its listing image SHALL leave the
article intact with no listing image, rather than being refused.

#### Scenario: Article deletion

- **WHEN** an article with body images is deleted
- **THEN** its image records are deleted and none of them appears in the
  project's gallery

#### Scenario: Deleting an image in use

- **WHEN** an image that is an article's listing image is deleted
- **THEN** the deletion succeeds and the article renders as a text-only card

### Requirement: The new-article page creates a draft immediately

Opening the new-article page SHALL create an empty draft and replace the URL
with the edit URL for it, so that image uploads have an article to be linked to.
The system SHALL create exactly one draft per visit.

A draft that is still untouched — no title, no body, no listing image and no
uploaded images — SHALL be deleted, best-effort, when the author leaves the page.

#### Scenario: Opening the new-article page

- **WHEN** an author opens the new-article page
- **THEN** one draft article exists and the URL addresses it

#### Scenario: Inserting an image before typing anything

- **WHEN** an author inserts an image as their first action on a new article
- **THEN** the image is linked to that article

#### Scenario: Leaving without writing anything

- **WHEN** an author opens the new-article page and navigates away without
  editing
- **THEN** no empty draft remains in their article list

### Requirement: Crops are stored as rectangles, not as new image files

The system SHALL store the listing crop as coordinates normalised against the
source image and apply it at render time over the existing image variants. The
system SHALL NOT generate cropped derivative files.

A crop MAY extend beyond the edges of its source, with the overrun rendered as
the shared crop background colour. The system SHALL reject a crop that does not
overlap its source at all, or that is more than six times its size.

#### Scenario: Re-framing is immediate

- **WHEN** the author changes the framing and saves
- **THEN** the new framing is visible with no image-processing step

#### Scenario: A crop that misses the image entirely

- **WHEN** a crop whose rectangle lies wholly outside the image is submitted
- **THEN** the API responds 422 and the article is unchanged
