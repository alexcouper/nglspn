## 1. Backend model and crop rules

- [x] 1.1 Add nullable `hero_crop` and `card_crop` JSON fields to `Article` in `apps/articles/models.py`
- [x] 1.2 Generate and review the migration (`uv run python manage.py makemigrations projects`)
- [x] 1.3 Write `services/articles/crop.py` with `CropRect` normalisation helpers, `validate_crop` (bounds, ratio range, 16:9 check for card crops, cross-check against source dimensions where known) and `derive_card_crop`
- [x] 1.4 Write `services/articles/test_crop.py`: derivation preserves the hero centre, clamps at the top and bottom image edges, shrinks width when the source is too tall for 16:9, returns `None` when the image has no recorded dimensions; validation rejects out-of-bounds rects, zero width, ratio outside 4:1–1:1, and a card crop at the wrong ratio

## 2. Backend API surface

- [x] 2.1 Add the `CropRect` schema to `api/schemas/article.py`
- [x] 2.2 Add `hero_crop` and `card_crop` to `ArticleUpdate`
- [x] 2.3 Add `hero_crop`, `card_crop` and resolved `card_crop_display` to `ArticleOut`
- [x] 2.4 Add resolved `card_crop` to `ArticleListItem`
- [x] 2.5 Extend `update_article` in `services/articles/django_impl/handler.py` to accept both crops through the existing `UNSET` sentinel, validate them, and clear both when the hero image is cleared
- [x] 2.6 Pass both fields from `patch_article` via `payload.dict(exclude_unset=True)`, mapping validation failures to 422
- [x] 2.7 Extend `api/routers/test_articles.py`: setting a hero crop round-trips; omitting it leaves it alone; explicit `null` clears it; clearing the hero image clears both crops; a card override survives a hero re-frame; an out-of-bounds crop is 422
- [x] 2.8 Test that `ArticleListItem.card_crop` resolves to the override when set and the derived value when not
- [x] 2.9 Run `make lint` and `make test` from `src/django-backend/`

## 3. Type regeneration

- [x] 3.1 `make extract-openapi` from `src/django-backend/`
- [x] 3.2 `npm run generate-types` from `src/web-ui/`
- [x] 3.3 Confirm `backend-openapi.json` and the generated types are committed

## 4. Rendering primitive

- [x] 4.1 Write `src/web-ui/src/components/CroppedImage.tsx` — `aspect-ratio` box, absolutely positioned image scaled by percentage, `maxWidth: "none"` inline, shared `CROP_BACKGROUND` where the crop overruns the image, `crop == null` falling back to 16:9 + `object-cover`
- [x] 4.2 Rework `ArticleHeroImage` to take a `crop` prop and delegate to `CroppedImage`, keeping the `GradientPlaceholder` path for a missing source
- [x] 4.3 Component tests: a crop produces the expected computed width/left/top and `max-width: none`; a null crop renders the 16:9 centre path; a missing source still renders the placeholder

## 5. Crop dialog

- [x] 5.1 Write `src/web-ui/src/components/ImageCropper.tsx` — article-agnostic, controlled, whole image on a stage with a dashed crop box over it, pointer-event pan, top/bottom edge handles, state in normalised source coordinates
- [x] 5.2 Zoom scales the image while the box holds its on-screen size, on a logarithmic slider; zoom and resize both preserve the crop's centre
- [x] 5.3 Allow the box past the image edges, painting `CROP_BACKGROUND` behind it so the stage matches the result
- [x] 5.4 Render a live `CroppedImage` preview of the working crop
- [x] 5.5 Clamp the ratio at 4:1 and 1:1 at the handles, and show a ratio readout that names small whole-number pairs
- [x] 5.6 Show the non-blocking resolution warning under 768 source pixels wide; support `lockRatio` (removes handles, fixes shape)
- [x] 5.7 Reduce `ImageCropDialog` to a thin `components/Dialog.tsx` wrapper, full-screen under `sm`, with only the stage scrolling
- [x] 5.8 Component tests: zoom narrows the focus and holds the box size, the box may leave the image, centre is preserved, dragging pans, handles stop at both clamps, `lockRatio` hides the handles

## 6. Editor wiring

- [x] 6.1 Track `hero_crop` and `card_crop` in `useArticleDraft.ts` form state and send both on save
- [x] 6.2 Change `handleHeroUpload` to take a crop, and make `clearHero` clear both crops
- [x] 6.3 Open `ImageCropDialog` from `onUploadComplete` in `ArticleAuthoringPage.tsx` instead of setting the hero directly
- [x] 6.4 On cancel of a first upload, do not set the hero and best-effort delete the uploaded image
- [x] 6.5 Replace the preview in `HeroImageUploader.tsx` with `ArticleHeroImage` and add an "Adjust framing" button alongside the existing remove control
- [x] 6.6 Update `image-insert.test.tsx` / `useImageUploadStatus` expectations if the upload-complete contract changed

## 7. Card framing

- [x] 7.1 Pass the resolved card crop through `ArticleCard` to `ArticleHeroImage`
- [x] 7.2 Add an "Adjust framing" control and a "Reset to match hero" control to `ArticleCardPreview.tsx`, opening `ImageCropDialog` with `lockRatio={16/9}`
- [x] 7.3 Update `toListItem` in `ArticleCardPreview.tsx` to carry the card crop so the in-dialog preview matches the live listing
- [x] 7.4 Update `ArticleRenderContent.tsx` to pass the hero crop
- [x] 7.5 Update `MyProjectArticles.tsx` to pass the card crop
- [x] 7.6 Extend `article-card.test.tsx` and `article-card-preview.test.tsx`: a card renders its resolved crop; reset clears the override; setting an override sends it

## 8. Verification

- [x] 8.1 `npm run lint` and the vitest suite from `src/web-ui/`
- [x] 8.2 E2E in `src/web-ui/e2e/`: upload a hero, set a non-default crop, save, reload the editor, assert the crop persisted and the editor preview matches the article page. Run serially and delete uploads — login is rate limited to 5/min per IP and projects cap at 10 images
- [x] 8.3 Manually check the crop dialog on a touch device or an emulated 375px viewport
- [x] 8.4 Confirm a pre-existing article with no stored crop renders exactly as before
- [x] 8.5 Run the repo's checks. There is no root `make ci` target (CLAUDE.md is out of date on this), so this is `make lint` + `make test` in `src/django-backend/` and `npm run lint` + vitest in `src/web-ui/`
