## Context

Images are uploaded directly to Scaleway S3 via presigned URLs, with no server-side processing. The Next.js `<Image>` component handles resizing on-the-fly, but its cache lives on the container's ephemeral filesystem. Every restart means re-fetching and re-transcoding every original (up to 10MB each) on a 256 CPU / 512MB container.

The storage key format is `projects/{project_id}/{uuid12}/{filename}`. Images are served via `cdn.naglasupan.is` (Scaleway Edge Services, 1-year cache TTL). The `ProjectImage` model tracks `storage_key`, dimensions, and an `upload_status` enum (PENDING → UPLOADED). The `complete_upload` endpoint is called after the browser finishes the S3 PUT — this is where we'll hook in variant generation.

## Goals / Non-Goals

**Goals:**
- Eliminate Next.js image optimization as the bottleneck for project images
- Serve pre-generated WebP variants directly from CDN with zero server-side processing
- Keep the upload UX unchanged — variant generation is transparent to the user
- Backfill variants for all existing images

**Non-Goals:**
- AVIF support (slower to encode, WebP is sufficient for now)
- Smart cropping or art direction (maintain aspect ratio only)
- Replacing `next/image` globally — only project images are affected
- Changing the CDN or storage provider

## Decisions

### 1. Generate variants asynchronously via `django_tasks`

Variant generation is kicked off as an async task when the frontend calls `complete_upload`. The endpoint returns immediately with the image record (no variants yet). Variants appear in the DB as they're generated, and the frontend picks the best available variant at render time.

**Architecture follows existing patterns:**
- **Service:** `services/image/handler_interface.py` defines the interface (`generate_variants(image_id)`). `services/image/django_impl/handler.py` implements it using Pillow + `StorageService`.
- **Task:** `api/tasks/images.py` defines a `@task()` that calls `HANDLERS.image.generate_variants(image_id)`.
- **Trigger:** `complete_upload` endpoint enqueues the task after marking the image as UPLOADED.

This matches how `email` and `web_ui` services/tasks are structured. The image service handles the processing logic; the task is a thin wrapper that delegates to `HANDLERS.image`.

**Why async?** A 10MB image takes several seconds to download, decode, resize 3 times, encode to WebP, and upload 3 files back to S3. Doing this synchronously would block the `complete_upload` response and degrade the upload UX. Async lets the UI show the original image immediately while variants generate in the background.

### 2. Three variant sizes: thumb (384w), medium (768w), large (1536w)

These map to actual usage:
- **thumb (384w):** Project grid cards. `sizes="(max-width: 768px) 50vw, 33vw"` means the browser needs ~190-256px on a 1x display, ~384-512px on 2x retina. 384w covers the common case.
- **medium (768w):** Detail page main image, and retina coverage for the grid.
- **large (1536w):** Lightbox and hero contexts where high resolution matters.

Images smaller than a variant width are skipped (no upscaling).

**Alternative considered:** Generating only 2 sizes (thumb + large). Rejected because the jump from 384 to 1536 is too large — medium fills the gap for detail pages without being wasteful.

### 3. Store variant records in the database via `ImageVariant` model

Each generated variant gets its own row in an `ImageVariant` model:

```
VariantSize(models.TextChoices):
  THUMB  = "thumb",  "Thumb (384w)"
  MEDIUM = "medium", "Medium (768w)"
  LARGE  = "large",  "Large (1536w)"

ImageVariant:
  id          UUID (pk)
  image       FK → ProjectImage (related_name="variants", cascade delete)
  size        CharField (max_length=20, choices=VariantSize.choices)
  storage_key CharField (full S3 key)
  width       PositiveIntegerField
  height      PositiveIntegerField
  file_size   PositiveIntegerField
  created_at  DateTimeField

  Meta:
    unique_together = (image, size)
    db_table = "project_image_variants"
```

The `VariantSize` TextChoices enum centralises the allowed sizes and their target widths. The variant generation service iterates `VariantSize` to decide which sizes to produce, so adding or removing a size is a single-place change.

The DB is the source of truth for what variants exist. The API returns only the variants that are actually recorded — if generation fails partway through, the client sees exactly what's available and falls back to `next/image` for the rest.

Storage keys follow the pattern `{original_key_without_ext}/{size_name}.webp`. For example, `projects/abc/def123/photo.jpg` → `projects/abc/def123/photo/thumb.webp`.

**Why a separate model instead of columns on ProjectImage?** A separate model cleanly handles partial generation (2 of 3 variants succeed), makes it easy to add/remove sizes later without schema changes, and lets us query "images missing variants" efficiently for backfill.

**Alternative considered:** Convention-based URL derivation (no DB records). Rejected because the DB should be the authority on what exists — inferring from convention means assuming files are present in S3 without proof.

### 5. WebP format only

WebP has universal browser support (>97% globally) and produces files ~30% smaller than JPEG at equivalent quality. AVIF would be marginally better but Pillow's AVIF encoding is significantly slower and requires additional system dependencies (`libavif`). WebP is the pragmatic choice.

Quality setting: 80 (good balance of quality and file size for web).

### 6. Frontend selects the best available variant for each context

The API returns the image's `variants` array (each with `size`, `url`, `width`, `height`). The frontend picks the best match for the rendering context, falling up through available sizes:

- **Project grid card** — wants `thumb`. If missing, use `medium`, then `large`, then original URL via `next/image`.
- **Detail page main image** — wants `medium`. Falls up to `large`, then original.
- **Lightbox** — wants `large`. Falls back to original.

A small helper function (e.g. `pickVariant(variants, preferred)`) handles the selection logic. This makes the system resilient to partial variant generation (async task hasn't finished, or a size was skipped because the original was smaller).

When a variant is available, render with a plain `<img>` tag — the CDN serves WebP directly with no Next.js processing. When falling back to the original, use `next/image` so the browser still gets optimization (just with the cold-cache cost).

### 7. Delete variants when deleting an image

The existing `delete_image` endpoint calls `storage_service.delete_object(image.storage_key)`. The cascade delete on `ImageVariant` handles the DB side. We also need to delete the variant files from S3 — iterate the image's variants and delete each `storage_key`. Deletion failures for variant files are logged but don't block the response.

## Risks / Trade-offs

**[Variant generation latency]** → A 10MB image at 4000px wide will take several seconds to process. Since generation is async, this doesn't block the upload flow. The image appears immediately with the original; variants become available as the task completes.

**[Variant generation fails mid-way]** → Each variant is recorded in the DB individually as it's uploaded. If generation fails after 2 of 3 variants, those 2 are still usable. The frontend falls back to `next/image` for sizes that don't have a variant. The backfill command can fill in the gaps later. No data loss — the original is always preserved.

**[Storage cost increase]** → 3 WebP variants per image, each much smaller than the original. For 100 projects × 5 images = 500 originals → 1500 variants. At ~50KB average per variant, that's ~75MB total. Negligible on Scaleway S3.

**[Stale variants if we change sizes later]** → Variant sizes are baked in. If we change sizes, we need a re-generation batch job. Acceptable given the small scale.

## Migration Plan

Single deployment — everything ships together. Most existing images will have no variants immediately after deploy; the frontend's fallback-to-original behaviour handles this gracefully.

1. **Run DB migration** — creates the `project_image_variants` table
2. **Deploy backend + web-ui** — both go live at once. New uploads get variants via the async task. Existing images have empty `variants` arrays, so the frontend falls back to the original URL via `next/image` (same as today).
3. **Run backfill command** — management command processes all `ProjectImage` records missing expected variants. Idempotent — skips sizes that already have a variant row. As each image is backfilled, subsequent page loads pick up the variants.

**Rollback:** Frontend falls back to `next/image` when no variants are present in the API response. The original image URL remains unchanged throughout. Deleting `ImageVariant` rows (or the table) reverts to the old behaviour entirely — the S3 variant files become orphaned but harmless.

## Open Questions

None — the approach is straightforward and well-bounded.
