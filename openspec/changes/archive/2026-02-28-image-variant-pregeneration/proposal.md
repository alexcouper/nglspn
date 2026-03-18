## Why

Images on naglasupan.is/projects load slowly, especially after the web-ui container restarts. The Next.js `<Image>` component fetches full-size originals (up to 10MB) from CDN and resizes them on-the-fly on a 256 CPU / 512MB container. The optimized results are cached in ephemeral container storage (`.next/cache/images/`), so every pod restart or deployment forces re-processing of every image. This saturates CPU and network, causing multi-second load times on the project grid.

## What Changes

- Generate WebP size variants (384w thumb, 768w medium, 1536w large) when an image upload completes on the Django backend
- Store variants in S3 alongside the original, served through the existing CDN (`cdn.naglasupan.is`)
- Expose variant URLs in the project API response
- Frontend uses pre-generated variants directly instead of relying on Next.js image optimization for project images
- Management command to backfill variants for all existing images
- Original images are preserved as-is for admin/download use

## Capabilities

### New Capabilities
- `image-variants`: Server-side generation of WebP size variants at upload time, storage in S3, and serving via CDN

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **Backend**: `complete_upload` endpoint gains variant generation (Pillow, already a dependency). New S3 download/upload methods in StorageService. API responses include variant URLs.
- **Frontend**: Project listing, detail, and gallery components switch from `next/image` optimization to direct CDN variant URLs. Reduces Next.js server CPU load to near-zero for image serving.
- **Storage**: ~3-5x increase in S3 storage per image (3 small WebP variants per original). Negligible cost at current scale.
- **CDN**: No configuration changes — variants use the same S3 bucket and Edge Services pipeline with 1-year cache TTL.
- **Migration**: One-time batch job to generate variants for existing uploaded images.
