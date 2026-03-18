# Image Performance at Naglasupan - Analysis & Recommendations

## Problem

Images on naglasupan.is/projects load slowly, especially after the web-ui container restarts. The page shows a grid of project cards, each with a thumbnail image. After a fresh deployment or pod restart, every image must be fetched from origin and re-optimised on the fly, causing multi-second load times that degrade with the number of projects.

---

## How Images Work at Naglasupan Today

### Upload Path
1. User drops an image (max 10MB, JPEG/PNG/WebP/GIF) into the browser
2. Frontend requests a **presigned S3 PUT URL** from the Django API
3. Browser uploads the **original, unmodified file** directly to Scaleway Object Storage (`s3.fr-par.scw.cloud`)
4. Frontend calls `complete` endpoint; Django records dimensions + metadata, but does **no image processing**

**Key files:** `src/django-backend/api/routers/my_projects.py:169-332`, `src/django-backend/services/storage.py`

### Storage
- Scaleway S3 bucket: `sideproject-prod-project-images`
- Objects stored under `projects/{project_id}/{uuid12}/{filename}` with `public-read` ACL
- No size variants are created — only the raw original

### CDN Layer (Scaleway Edge Services)
- `cdn.naglasupan.is` → Scaleway Edge Services pipeline → S3 bucket origin
- **Cache TTL: 1 year** (files have unique path segments so this is safe)
- Pipeline: DNS stage → TLS (Let's Encrypt) → Cache → Backend (S3)
- This caches the **original full-size image** at the edge — no transformation

**Key file:** `infra/prod/app/edge_services.tf`

### Next.js Image Optimization (the bottleneck)
- The `<Image>` component (next/image) fetches images through Next.js's built-in `/_next/image` endpoint
- This endpoint: fetches the original from `cdn.naglasupan.is` → decodes → resizes to requested width → encodes to AVIF or WebP → serves to browser
- The `sizes` prop `"(max-width: 768px) 50vw, 33vw"` tells the browser to request ~200-400px wide variants
- Config: `minimumCacheTTL: 2592000` (30 days), formats: AVIF + WebP
- **Cache location: `.next/cache/images/` on the container filesystem**

**Key files:** `src/web-ui/next.config.ts`, `src/web-ui/src/app/projects/ProjectsListing.tsx:273-280`

### Container Setup
- Scaleway Serverless Container: **256 CPU / 512MB memory**, min_scale=1, max_scale=1
- No persistent volume — **container filesystem is ephemeral**
- Standalone Next.js build (output: "standalone")

**Key files:** `infra/prod/app/container.tf:102-138`, `src/web-ui/Dockerfile`

### The Full Request Chain (after restart)
```
Browser → /_next/image?url=cdn.naglasupan.is/...&w=384&q=75
       → Next.js server (no cache, cold)
       → fetches https://cdn.naglasupan.is/projects/xxx/original.jpg (e.g. 4000px, 3MB)
       → decodes, resizes to 384px, encodes to AVIF
       → caches in .next/cache/images/ (ephemeral!)
       → serves ~30KB AVIF to browser
```

For a grid of 15+ projects, this means the tiny container (256 CPU / 512MB) must simultaneously fetch and transcode 6+ large images (those with `priority={true}`), with the rest queued. This saturates both network and CPU.

---

## Industry Approaches

### 1. Server-side pre-generation of size variants (at upload time)

**How it works:** When an image is uploaded, the server immediately creates multiple resized versions (e.g. 320w, 640w, 1024w, 1920w) and stores them all in object storage alongside the original. The frontend references specific sizes in `<img srcset>` or via direct URL.

**Who decides which size?** The HTML `srcset` attribute and `sizes` hint tell the browser which variant to download. The browser picks the closest match based on viewport width and device pixel ratio.

**Example:**
```html
<img srcset="/img/photo-320w.webp 320w,
             /img/photo-640w.webp 640w,
             /img/photo-1024w.webp 1024w"
     sizes="(max-width: 768px) 50vw, 33vw" />
```

**Pros:**
- Zero runtime processing cost — images served directly from S3/CDN
- Predictable performance, no cold-start penalty
- Full control over quality and output format (WebP, AVIF)
- Simple to understand and debug

**Cons:**
- Increases storage usage (~3-5x depending on variant count)
- Requires background processing at upload time (Pillow, sharp, etc.)
- Adding new sizes requires a migration/batch job
- Must decide on sizes upfront

**At Naglasupan:** Process images in the Django backend's `complete_upload` endpoint (or an async task). After the image lands in S3, download it, generate variants with Pillow, upload variants back to S3 under `projects/{id}/{uuid}/w_{width}.webp`. Update the API to return variant URLs. On the frontend, switch from `next/image` to standard `<img srcset>` or pass the right variant URL directly.

### 2. On-the-fly image transformation service (image CDN)

**How it works:** An external service sits between your storage and the browser. You request images with transformation parameters in the URL (e.g. `?width=400&format=webp`). The service fetches the original, transforms it, caches the result at the edge, and serves it. Subsequent requests for the same transformation are served from cache.

**Popular services:** Cloudflare Images, Imgix, Cloudinary, Bunny Optimizer, AWS CloudFront + Lambda@Edge.

**Who decides which size?** Same as above — the frontend constructs the URL with the desired width. `next/image` can be configured with a custom `loader` that builds the URL for whatever service you use.

**Example with a generic image CDN:**
```
https://images.naglasupan.is/projects/xxx/photo.jpg?w=400&f=webp&q=80
```

**Pros:**
- No storage multiplication — single original, infinite variants on demand
- Edge-cached globally — fast everywhere after first request
- Zero processing on your servers
- New sizes/formats work immediately with no backend changes
- Usually provides smart cropping, blur placeholders, etc.

**Cons:**
- External service dependency and cost
- Another vendor in the stack
- Cache miss on first request per variant (but only once, not per pod restart)
- Some services charge per transformation or per GB served

**At Naglasupan:** Subscribe to a service (e.g. Cloudflare Images, Imgix, or Bunny Optimizer). Point it at `cdn.naglasupan.is` as origin. Configure a custom `next/image` loader (or use `<img>` directly). No backend changes needed for upload — just change how URLs are constructed in the frontend.

### 3. Scaleway Edge Services Transform (if available) / S3-native transforms

**How it works:** Some cloud providers offer built-in image transformation as part of their CDN or object storage. AWS has CloudFront Functions + S3 Object Lambda. Cloudflare has Image Resizing. Scaleway's Edge Services currently do **not** support image transformation — they only cache.

**At Naglasupan:** Not currently viable. Scaleway Edge Services is a pure caching CDN with no transform capabilities. Would need to switch CDN provider or add a transform layer in front of it.

### 4. Next.js image optimization with persistent cache

**How it works:** Keep the existing `next/image` approach but make the optimization cache persistent across container restarts. This can be done by:
- Mounting a persistent volume for `.next/cache/images/`
- Using a custom cache handler that stores optimized images in S3 or Redis

**Who decides which size?** Same as today — `next/image` handles everything automatically based on `sizes`, `deviceSizes`, and `imageSizes` in next.config.

**Pros:**
- Minimal code changes — keep existing `<Image>` components as-is
- Cache survives restarts
- Still get automatic AVIF/WebP negotiation

**Cons:**
- Scaleway Serverless Containers don't support persistent volumes
- Custom cache handlers add complexity and another moving part
- Still CPU-intensive on cache misses (just happens less often)
- Optimized images still need to be generated at least once per variant
- A new deployment wipes the cache anyway (new container image = new filesystem)

**At Naglasupan:** Scaleway Serverless Containers don't support mounted volumes. You'd need to either (a) switch to a Kubernetes deployment with persistent volumes, or (b) implement a custom Next.js image cache handler that stores results in S3. Option (b) is possible but adds significant complexity for what's essentially recreating approach #1.

### 5. Hybrid: Pre-generate key sizes + next/image for the rest

**How it works:** Generate 2-3 common sizes at upload time (e.g. thumbnail 384w for the project grid, medium 1024w for detail pages). Use these directly via `<img>` for the most common views. Fall back to `next/image` for edge cases like the lightbox where full-res is needed.

**Pros:**
- Handles the critical path (project grid) with zero runtime cost
- Lightbox can still load the full original — users expect that to be slower
- Less storage than full pre-generation
- Simpler than a full image CDN integration

**Cons:**
- Partial solution — some paths still use runtime optimization
- Still need upload-time processing

**At Naglasupan:** Best of both worlds for the current scale.

---

## Recommendation: Pre-generate size variants at upload time (Approach 1/5 hybrid)

For Naglasupan's scale and stack, **pre-generating image variants at upload time** is the right call. Here's why:

1. **Eliminates the core problem.** The slow loads happen because Next.js must download + transcode large originals on a tiny container. Pre-generated variants bypass Next.js image optimization entirely — images serve straight from CDN.

2. **No new services or vendors.** Everything stays within Scaleway (S3 + Edge Services). No monthly bills from Imgix/Cloudinary, no new API keys to manage.

3. **Simple to implement.** Pillow is already a dependency. The upload flow already has a `complete` step where we know the image is in S3. We add variant generation there (or as an async task).

4. **Robust.** Pod restarts, new deployments, scaling events — none of them affect image serving because the variants live in S3 behind the CDN with a 1-year cache TTL.

5. **Storage cost is negligible.** With max 10 images per project and generating 3 variants per image, even 100 projects = ~3000 small WebP files. At Scaleway S3 pricing this is pennies.

### Implementation Outline

**Variant sizes to generate:**
- `thumb` — 384w (project grid cards, the critical path)
- `medium` — 768w (detail page, 2x for grid on retina)
- `large` — 1536w (lightbox, detail hero)
- Keep original as-is for admin/download

**Format:** WebP (universal browser support, ~30% smaller than JPEG). AVIV could be added later but encoding is much slower and WebP is good enough.

**On upload complete:**
1. Download original from S3
2. Generate WebP variants with Pillow at each width (maintaining aspect ratio)
3. Upload variants to S3 under `projects/{id}/{uuid}/thumb.webp`, `medium.webp`, `large.webp`
4. Store variant metadata in the database (or derive URLs by convention)

**API changes:**
- Return variant URLs in the project API response (e.g. `image.thumb_url`, `image.medium_url`)

**Frontend changes:**
- For project grid cards: use `<img>` with the thumb URL directly (no `next/image` needed)
- Or keep `next/image` but with `unoptimized` prop + srcset of known variants
- The `sizes` prop already tells the browser what it needs

**Migration:**
- Batch script to generate variants for existing images

### Files to modify
- `src/django-backend/api/routers/my_projects.py` — variant generation in complete_upload
- `src/django-backend/services/storage.py` — add download + upload methods
- `src/django-backend/apps/projects/models.py` — variant URL properties
- `src/web-ui/src/app/projects/ProjectsListing.tsx` — use variant URLs
- `src/web-ui/src/components/ImageUpload/ImageGallery.tsx` — use variant URLs
- `src/web-ui/src/app/my-projects/ProjectsList.tsx` — use variant URLs
- Management command for backfilling existing images

### Verification
- Upload a test image (large JPEG, ~4000px wide)
- Verify variants appear in S3 at expected paths
- Visit /projects and confirm images load from CDN variant URLs (check network tab)
- Restart the web-ui container and confirm images load just as fast
- Run `make test` and `npm run lint` for both codebases
