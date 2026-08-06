## Why

Every article currently needs a hero image, that image renders above the body,
and the author frames it twice — once free-shape for the article page and once
at 16:9 for listing cards. Using it showed three problems.

The mandatory hero is a tax. An article that has no photograph worth showing
still has to have one, so authors reach for something decorative.

The hero above the body is the wrong mechanism. An author who wants an image at
the top of their article can put one there — the editor already inserts images
into the body. A second, separate uploader above the content is a duplicate way
to do the same thing, with a different framing model and its own rules.

And the card framing lives behind a dialog opened from the editor toolbar,
which is about to become a dialog inside a dialog once picking an image needs
its own dialog. It also shows the lead card and the grid card stacked on top of
each other, so the author sees the same article twice in one small window.

What is actually needed is one image, used only for listing cards, chosen and
framed in a panel that belongs to the article rather than floating over it.

## What Changes

- **BREAKING** The hero image is gone. The article page renders body content
  only; the editor loses its hero uploader. `hero_image`, `hero_crop` and
  `card_crop` on `Article` become `listing_image`, `listing_crop` and
  `listing_image_mode`. Only test data exists, so no backfill.
- **BREAKING** An article can be published with no image. `_can_publish` drops
  its `hero_image` check, and the rule forbidding a published article from
  clearing its image goes with it.
- The listing image has three modes. `auto` (the default) takes the first image
  uploaded to the article, `chosen` uses what the author picked and framed,
  `none` is an explicit text-only card. `auto` re-resolves on every save off the
  new FK — nothing parses the article body. The mode field exists because a null
  image id otherwise cannot tell "not chosen yet" from "deliberately removed".
- Listing cards with no image give the space to the headline instead of drawing
  a placeholder.
- The card preview dialog becomes a **Listing settings** tab on the article
  editor, alongside **Content**. Title and channel stay above the tab strip.
  Inside the tab: the summary field, the image control, and a nested
  *As lead story* / *In the grid* tab pair so the same article is not shown
  twice at once. Switching to the tab saves the draft — the listing summary is
  derived server-side and a preview of unsaved text would be a lie.
- Choosing the image is a two-step wizard: pick from the images already linked
  to this article (or upload a new one), then frame it at 16:9. The list comes
  off the new FK, so no endpoint and no markdown parsing are needed for it.
- **BREAKING** Only one crop survives, and it is always 16:9. The free-shape
  mode of `ImageCropper` — edge handles, the 4:1–1:1 clamp, the derived
  hero → card rule — is deleted along with its only caller.
- **BREAKING** `ProjectImage.source` is replaced by a nullable
  `ProjectImage.article` FK. "Is this an article image" becomes
  `article_id IS NOT NULL`, so the flag and the link cannot disagree. The
  presign API still takes `source`, plus a new `source_id`.
- Opening `/projects/<slug>/articles/new` creates an empty draft immediately and
  swaps the URL to `/edit/<id>`, because an upload cannot be linked to an
  article that does not exist yet.

## Capabilities

### New Capabilities

- `article-listing-image`: which image represents an article in a listing, how
  the author chooses and frames it, and what a card does without one.

### Removed Capabilities

- `article-hero-cropping`, superseded wholesale. It is complete but unarchived,
  so it never reached `openspec/specs/` and there is nothing to write a delta
  against; its directory is deleted in task 0.1, in its own commit. Its
  capability name no longer describes anything — there is no hero.

### Modified Capabilities

None as delta files. `openspec/changes/add-article-authoring/specs/articles/spec.md`
asserts hero-is-required and hero-renders-above-body at lines 55, 94, 101,
107–108, 204, 206, 225 and 257. That change is still in progress (83/94), so
those lines are corrected in place rather than by a delta against a spec that
has not landed — task 11.1, not follow-up work.

## Impact

Backend (`src/django-backend/`):

- `apps/articles/models.py` — field renames, `hero_crop` dropped,
  `listing_image_mode` added, `listing_image` moves from `PROTECT` to
  `SET_NULL`.
- `apps/projects/models.py` — `ProjectImage.article` added, `source` and
  `ImageSource` removed.
- Two migrations, generated (not hand-edited) so a local database can migrate
  forwards without being rebuilt.
- `services/articles/crop.py` — free-shape validation and the hero → card
  derivation deleted.
- `services/articles/django_impl/handler.py` — `auto` resolution on save,
  publish rule.
- `api/schemas/article.py`, `api/schemas/project.py`,
  `api/routers/my_projects.py`, `services/project/django_impl/query.py` — the
  `source` → `article_id` swap and the renamed fields.

Frontend (`src/web-ui/`):

- New `ListingSettingsPanel` and `ListingImageDialog`; `HeroImageUploader` and
  `ArticleCardPreviewDialog` deleted.
- `ArticleAuthoringPage` gains tabs and eager draft creation.
- `ArticleHeroImage` → `ArticleListingImage`, and `ArticleCard` grows an
  imageless layout.
- `ImageCropper` loses its free-shape mode.
- `ArticleRenderContent` loses the hero.

Mechanical: migrations → `make extract-openapi` → `npm run generate-types`.
