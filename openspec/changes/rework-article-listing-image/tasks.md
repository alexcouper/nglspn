## 0. Retire the superseded change

- [x] 0.1 Delete `openspec/changes/article-hero-cropping/` — complete but unarchived, its capability name no longer describes anything, and every requirement in it is superseded by `article-listing-image`. Its own jj commit, before any code changes, so the removal is legible on its own

## 1. Backend model and migrations

- [x] 1.1 In `apps/articles/models.py`: rename `hero_image` → `listing_image` and change it to `on_delete=SET_NULL`, rename `card_crop` → `listing_crop`, delete `hero_crop`, add `ListingImageMode` choices (`auto` / `chosen` / `none`) and a `listing_image_mode` field defaulting to `auto`
- [x] 1.2 In `apps/projects/models.py`: add `article = FK("articles.Article", null=True, blank=True, on_delete=CASCADE, related_name="images")`, delete the `source` field and move `ImageSource` out of the model module
- [x] 1.3 `uv run python manage.py makemigrations articles` — answer the rename prompts *yes* so the columns are renamed rather than dropped and re-added
- [x] 1.4 `uv run python manage.py makemigrations projects`, and check the generated migration depends on the articles one
- [x] 1.5 `uv run python manage.py migrate` against the local database and confirm it moves forwards without a rebuild
- [x] 1.6 Update `apps/articles/admin.py` and `apps/articles/tests/test_models.py` for the renamed fields
- [x] 1.7 Test that deleting an article deletes its linked images, and that deleting an image that is a listing image nulls the reference instead of raising `ProtectedError`

## 2. Auto mode and publish rules

- [x] 2.1 In `services/articles/django_impl/handler.py`, resolve `auto` mode on create and on update: `listing_image` becomes `article.images.order_by("created_at").first()` (or null) and `listing_crop` becomes null. Order by `created_at` explicitly — `ProjectImage.Meta.ordering` leads with `display_order`, which is identical across an article's uploads
- [x] 2.2 Make any wizard action set `mode = chosen`, and removal set `mode = none`; ensure a `chosen` or `none` article is never re-resolved on save
- [x] 2.3 Drop the `hero_image` requirement from `_can_publish` (`handler.py:166`) and the rule refusing to clear the image on a published article (`handler.py:129`)
- [x] 2.4 Update `services/articles/handler_interface.py` for the renamed and added fields
- [x] 2.5 Extend `services/articles/django_impl/test_handler.py`: auto adopts the earliest upload, a later upload does not displace it, deleting the first promotes the next, `chosen` and `none` are never re-resolved, and publishing with no image succeeds

## 3. Image–article link and derived source

- [x] 3.1 Move `ImageSource` into `api/schemas/project.py` and add `source_id: UUID | None` to `PresignedUploadRequest`
- [x] 3.2 In `api/routers/my_projects.py`, populate `article_id` from `source` + `source_id`, rejecting an id that does not name an article in the same project
- [x] 3.3 Swap the four remaining `source` checks to the FK: `my_projects.py:251` (image cap), `:324` (never promote to main), `:410` (main-image promotion), `services/project/django_impl/query.py:48` (gallery queryset)
- [x] 3.4 Swap `api/schemas/project.py:113` (`resolve_images`) to `img.article_id is None`
- [x] 3.5 Test that article-linked images stay out of the gallery, out of the cap and out of main-image promotion, and that a presign naming a foreign article is rejected

## 4. Backend API surface

- [x] 4.1 In `api/schemas/article.py`: rename to `listing_image_id` / `listing_image_url` / `listing_image` / `listing_crop`, add `listing_image_mode`, delete `hero_crop`, `card_crop` and `card_crop_display`
- [x] 4.2 Update `ArticleCreate`, `ArticleUpdate` and `ArticleListItem` to match, keeping the `UNSET` sentinel handling for `listing_image_id` and `listing_crop`
- [x] 4.3 Add `images: list[ProjectImageResponse]` to `ArticleOut` off the `article.images` reverse relation, prefetched with variants — this is the wizard's selection list, and no new endpoint or body parse is needed for it
- [x] 4.4 Trim `services/articles/crop.py`: delete `derive_card_crop`, `resolve_card_crop`, `MIN_RATIO`, `MAX_RATIO` and the `expected_ratio is None` branch of `validate_crop`; every crop validates against `CARD_RATIO`
- [x] 4.5 Update `services/articles/test_crop.py` for the removals
- [x] 4.6 Extend `api/routers/test_articles.py`: mode round-trips, an image id plus crop round-trips, an explicit null clears, a non-16:9 crop is 422, publishing with no image succeeds, `ArticleOut.images` carries the article's linked uploads and nothing else
- [x] 4.7 `make lint` and `make test` from `src/django-backend/`

## 5. Type regeneration

- [x] 5.1 `make extract-openapi` from `src/django-backend/`
- [x] 5.2 `npm run generate-types` from `src/web-ui/`
- [ ] 5.3 Confirm `backend-openapi.json` and the generated types are committed

## 6. Rendering: cards without an image

- [ ] 6.1 Rename `ArticleHeroImage` → `ArticleListingImage`, drop the `GradientPlaceholder` branch (`GradientPlaceholder` itself stays — nine other surfaces use it)
- [ ] 6.2 Give `ArticleCard` an imageless layout: no image element, headline clamp `2 → 4` (grid) and `3 → 4` (lead), summary clamp `3 → 5` (grid) and `2 → 4` (lead)
- [ ] 6.3 Decide the imageless **lead** treatment against the real rendering so it does not read as a broken card — rule, tint, larger headline or a combination. Screenshot before and after
- [ ] 6.4 Confirm a mixed grid keeps equal row heights
- [ ] 6.5 Remove the hero from `ArticleRenderContent.tsx`
- [ ] 6.6 Update `MyProjectArticles.tsx` and `ArticlesList.tsx` for the renamed fields
- [ ] 6.7 Extend `article-card.test.tsx`: an imageless card renders no image element and the wider clamps; an imaged card is unchanged

## 7. Cropper simplification

- [ ] 7.1 In `ImageCropper.tsx`, delete the edge handles, `minRatio`, `maxRatio`, the free-shape hint and the ratio readout's free-shape path; make `lockRatio` required
- [ ] 7.2 Simplify `ImageCropDialog.tsx` accordingly, and allow the cropper to be hosted as a wizard step rather than only in a dialog
- [ ] 7.3 Prune the free-shape cases from `image-cropper.test.tsx`

## 8. Editor: tabs and draft lifecycle

- [ ] 8.1 Create the draft on mount in the `/new` route and `router.replace` to `/edit/<id>`; guard with a ref so StrictMode's double effect does not create two
- [ ] 8.2 Best-effort delete the draft on unmount when it is still untouched (no title, body, listing image or uploaded images)
- [ ] 8.3 Rework `ArticleAuthoringPage.tsx`: title and channel above a **Content** / **Listing settings** tab strip; delete the hero uploader, the crop-dialog wiring, `needsHeroImage` and the warning it drove
- [ ] 8.4 Save the draft on switching to **Listing settings**, surfacing failure and not showing a stale preview
- [ ] 8.5 Rework `useArticleDraft.ts`: form state becomes `listing_image_id`, `listing_crop`, `listing_image_mode`; replace `handleHeroUpload` / `setHeroCrop` / `clearHero` with the wizard's setters; drop `needsHeroImage`
- [ ] 8.6 Pass `source_id` through `useImageUpload` and `uploadProjectImage`
- [ ] 8.7 Delete `HeroImageUploader.tsx` and `ArticleCardPreviewDialog.tsx`

## 9. Listing settings panel

- [ ] 9.1 Write `ListingSettingsPanel.tsx`: summary field (unchanged behaviour and 300-char cap), the image control with Change / Remove, and the card preview
- [ ] 9.2 Rework `ArticleCardPreview.tsx` into a nested *As lead story* / *In the grid* tab pair showing one at a time
- [ ] 9.3 Show the current mode in words — following the first image in the article, the author's choice, or no image
- [ ] 9.4 Update `article-card-preview.test.tsx` for the tab pair and the mode display

## 10. Listing image wizard

- [ ] 10.1 Write `ListingImageDialog.tsx` — step one selects, step two frames, with back and cancel
- [ ] 10.2 Step one: `article.images` from `ArticleOut`, the current selection marked, then upload; a fresh upload continues straight to step two
- [ ] 10.3 Step two: `ImageCropper` at `lockRatio={16/9}`, opening on the stored crop when the image is unchanged and on a centred default otherwise
- [ ] 10.4 Best-effort delete an upload that is cancelled before adoption
- [ ] 10.5 Confirm sets image, crop and `mode = chosen`; Remove sets `mode = none` and clears both
- [ ] 10.6 Component tests: the article's linked images are offered, an image uploaded through the wizard is offered on reopen, re-picking the current image preserves its crop, picking a different one resets it, cancelling changes nothing

## 11. Spec reconciliation

- [ ] 11.1 Correct `openspec/changes/add-article-authoring/specs/articles/spec.md` — lines 55, 94, 101, 107–108, 204, 206, 225 and 257 assert hero-is-required or hero-renders-above-body. That change is still in progress, so it must not archive those statements into `openspec/specs/`
- [ ] 11.2 Check `docs/` for anything asserting a mandatory hero image

## 12. Verification

- [ ] 12.1 `npm run lint` and the vitest suite from `src/web-ui/`
- [ ] 12.2 Rewrite or delete `e2e/article-hero-removal.spec.ts`; update `e2e/article-images.spec.ts` for the linked-upload flow
- [ ] 12.3 E2E: create an article, insert two body images, save, confirm the card auto-adopts the earlier one; open the wizard, pick the second, frame it, save, reload and confirm it persisted; remove it and confirm it stays removed across a save. Run serially and clean up uploads — login is rate limited to 5/min per IP and projects cap at 10 images
- [ ] 12.4 E2E or manual: publish an article with no image at all and confirm it renders as a text-only card in both variants
- [ ] 12.5 Manually check the wizard on an emulated 375px viewport
- [ ] 12.6 Run the repo's checks: `make lint` + `make test` in `src/django-backend/`, `npm run lint` + vitest in `src/web-ui/` (there is no working root `make ci` target)
