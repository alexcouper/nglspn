## Context

Project pages serve images through Next.js `<Image>` component pointing at `cdn.naglasupan.is` origins. All images route through `/_next/image` for on-the-fly optimization. HAR analysis of a 10-image project page shows:

- **1180ms** before any image request fires (JS hydration blocks discovery)
- **580-974ms** server TTFB per image even on `x-nextjs-cache: HIT`
- **2209ms** until the last image loads
- Total payload is only 65KB — size isn't the issue, timing is

Current code: no `priority` prop on any above-the-fold image, no AVIF format configured, default 4-hour cache TTL.

## Goals / Non-Goals

**Goals:**
- Reduce time-to-first-image by allowing browser to preload above-the-fold images during JS download
- Reduce image payload with AVIF format
- Reduce server-side re-optimization frequency with longer cache TTL

**Non-Goals:**
- Pre-generating optimized thumbnails at upload time (larger architectural change for later)
- Changing the CDN or image hosting infrastructure
- Adding blur placeholders or skeleton states (already has placeholders)

## Decisions

### Use `priority` prop for above-the-fold images
Next.js `priority` adds `<link rel="preload">` to the HTML `<head>` and sets `loading="eager"`. This lets the browser discover and start fetching images from the HTML alone, without waiting for JS execution and React hydration. The hero image on detail pages and first 6 grid cards on listing pages are consistently above the fold.

Alternative considered: using `loading="eager"` directly — this skips lazy loading but doesn't add the preload hint, so the browser still can't discover the image until React renders.

### Enable AVIF format
AVIF produces 20-30% smaller files than WebP at equivalent quality. Next.js serves AVIF to browsers that support it (all modern browsers) and falls back to WebP. No code changes needed beyond config.

### Set `minimumCacheTTL` to 30 days
The current default (4 hours via upstream `max-age`) means the Next.js optimizer must re-fetch and re-encode images frequently. Project images are immutable once uploaded (new uploads get new paths), so a 30-day TTL is safe.

## Risks / Trade-offs

- **Too many preloaded images on listing page** → Preloading 6 images adds 6 `<link rel="preload">` tags. This is within the recommended limit. We pass `priority` only to the first 6 cards via index check.
- **AVIF encoding is slower than WebP on first request** → Only affects cold cache. Subsequent requests benefit from smaller payloads. The 30-day TTL minimizes cold cache frequency.
- **Cache staleness if images are replaced at same path** → Project images use content-hash paths (`/c2986b0f7af8/6.png`), so this isn't a concern — different content always gets a different URL.
