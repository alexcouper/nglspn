## Why

An article hero renders four different shapes today. The editor crops it to
`w-full max-h-80` — a fixed 320px ceiling against a fluid width, so the framing
changes as the browser resizes and never matches the article page. The article
page, the lead card and the grid card all use a fixed 16:9 centre crop, which is
the same shape everywhere but is nobody's choice: the author uploads an image and
the middle band of it is taken.

So an author cannot tell what their hero will look like while writing it, and
cannot decide what part of the image matters.

## What Changes

- After uploading a hero image, the author is shown a crop dialog: a
  full-column-width frame whose height they set with drag handles, over an image
  they pan and zoom. The chosen rectangle **and its aspect ratio** are stored
  with the article.
- The article hero renders at that stored ratio at every viewport — full column
  width, height following the ratio. The editor and the article page use the same
  component, so what the author framed is what a reader sees.
- Listing cards keep a fixed 16:9, so a grid stays uniform. Their crop defaults to
  one derived from the hero selection (same centre, fitted to 16:9, clamped to the
  image), and can be overridden independently from the existing card preview
  dialog.
- Crops are stored as normalised rectangles and applied with CSS over the existing
  image variants. No new derivative files, no reprocessing, and re-cropping is
  instant.
- Articles with no stored crop keep rendering exactly as they do now — 16:9,
  centred. Not breaking, and no backfill.

## Capabilities

### New Capabilities

- `article-hero-cropping`: how an author selects the framing of an article hero
  image, how that selection is stored, and how it resolves into the hero and
  listing-card renderings.

### Modified Capabilities

None. The `articles` capability is still unarchived in
`openspec/changes/add-article-authoring/`, and hero framing is a distinct enough
concern to stand as its own spec rather than amend a spec that has not landed.

## Impact

Backend (`src/django-backend/`):

- `apps/articles/models.py` — `Article` gains `hero_crop` and `card_crop`.
- Migration required.
- `api/schemas/article.py` — `ArticleOut`, `ArticleUpdate` and `ArticleListItem`
  change shape; `ArticleListItem.card_crop` is resolved server-side.
- `services/articles/` — crop validation and the hero → card derivation rule.

Frontend (`src/web-ui/`):

- New `CroppedImage` primitive and `ImageCropDialog`.
- `ArticleHeroImage`, `ArticleCard`, `HeroImageUploader`, `ArticleCardPreview`,
  `ArticleRenderContent` and `useArticleDraft` all touched.

Mechanical: `make extract-openapi` then `npm run generate-types`.
