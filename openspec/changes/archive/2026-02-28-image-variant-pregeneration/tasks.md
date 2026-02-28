## 1. ImageVariant model and migration

- [x] 1.1 Add `VariantSize` TextChoices enum (THUMB/MEDIUM/LARGE) and `ImageVariant` model to `apps/projects/models.py` — UUID pk, FK to ProjectImage (cascade, related_name="variants"), `size` CharField with VariantSize choices, `storage_key`, `width`, `height`, `file_size`, `created_at`. unique_together on (image, size), db_table "project_image_variants"
- [x] 1.2 Add `url` property to `ImageVariant` that returns `{S3_PUBLIC_URL_BASE}/{storage_key}`
- [x] 1.3 Generate and run migration

## 2. Image processing service

- [x] 2.1 Create `services/image/handler_interface.py` with `ImageHandlerInterface` defining `generate_variants(image_id: str) -> None`
- [x] 2.2 Create `services/image/django_impl/handler.py` with `DjangoImageHandler` implementing variant generation: download original from S3, resize with Pillow to each target width (384, 768, 1536) that is smaller than the original, encode as WebP quality 80, upload to S3 with public-read ACL, create `ImageVariant` row for each. Skip sizes >= original width. Each variant saved individually so partial success is preserved.
- [x] 2.3 Add `download_object` method to `StorageService` in `services/storage.py` — returns file bytes for a given key
- [x] 2.4 Add `upload_object` method to `StorageService` — uploads bytes with specified key, content type, and ACL
- [x] 2.5 Register `ImageHandlerInterface` and `DjangoImageHandler` in `services/__init__.py` (add `image` field to `HandlerServices`)
- [x] 2.6 Write tests for `DjangoImageHandler.generate_variants` — large image (3 variants), small image (partial variants), tiny image (no variants), partial failure preserves completed variants. Use moto for S3 mocking.

## 3. Async task

- [x] 3.1 Create `api/tasks/images.py` with `generate_image_variants` task that calls `HANDLERS.image.generate_variants(image_id)`
- [x] 3.2 Enqueue `generate_image_variants` task in `complete_upload` endpoint after image is marked UPLOADED
- [x] 3.3 Write test for task enqueuing in complete_upload flow

## 4. API response changes

- [x] 4.1 Add `ImageVariantResponse` schema in `api/schemas/project.py` with fields: `size`, `url`, `width`, `height`
- [x] 4.2 Add `variants: list[ImageVariantResponse]` to `ProjectImageResponse` schema
- [x] 4.3 Add `resolve_variants` to `ProjectImageResponse` that returns the image's `ImageVariant` queryset
- [x] 4.4 Regenerate OpenAPI spec: `cd src/django-backend && make extract-openapi`
- [x] 4.5 Regenerate TypeScript types: `cd src/web-ui && npm run generate-types`

## 5. Variant deletion

- [x] 5.1 Update `delete_image` endpoint to delete variant S3 files before deleting the image (iterate `image.variants.all()`, delete each `storage_key`). Log and continue on S3 deletion failure. DB rows cascade-delete with the image.
- [x] 5.2 Write test for deletion — confirm variant S3 files and DB rows are cleaned up

## 6. Frontend variant selection

- [x] 6.1 Create `pickVariant` helper in `src/web-ui/src/lib/utils.ts` — takes variants array and preferred size name, falls up through sizes (thumb → medium → large), returns variant URL or null
- [x] 6.2 Update `ProjectsListing.tsx` ProjectCard — use `pickVariant(variants, "thumb")`, render `<img>` when variant found, fall back to `next/image` with original URL when null
- [x] 6.3 CompetitionProjectCard skipped — uses `CompetitionProjectResponse` which has `main_image_url` string, no variants array
- [x] 6.4 Update `ImageGallery.tsx` main image — use `pickVariant(variants, "medium")`
- [x] 6.5 Update `ImageGallery.tsx` lightbox — use `pickVariant(variants, "large")`
- [x] 6.6 Update `ProjectsList.tsx` (my-projects) — use `pickVariant(variants, "thumb")`

## 7. Backfill management command

- [x] 7.1 Create management command `generate_image_variants` — queries all ProjectImage with upload_status=UPLOADED that are missing any expected variant sizes, calls the image service to generate missing variants for each. Log progress (N/total processed).
- [x] 7.2 Write test for backfill — confirm idempotency (skips existing variants), only processes UPLOADED images

## 8. Linting and tests

- [x] 8.1 Run `make lint` in `src/django-backend/` and fix any issues
- [x] 8.2 Run `make test` in `src/django-backend/` and fix any failures
- [x] 8.3 Run `npm run lint` in `src/web-ui/` and fix any issues
